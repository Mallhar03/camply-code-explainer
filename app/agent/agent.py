import json
import time
import uuid
from app.agent.models import AgentResult, Citation
from app.agent.llm import LLMClient
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import keyword_search, read_file
from app.agent.validate import validate_schema, verify_citations, confidence_for, status_for
from app.retrieval.retriever import semantic_search
from app.db import connection


def _usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    return getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0)


def _chunk_dict(chunk) -> dict:
    return {
        "chunk_id": chunk.id,
        "path": chunk.path,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "score": chunk.score,
        "content": chunk.content,
    }


def _tool_result(result) -> str:
    if isinstance(result, list):
        return json.dumps([_chunk_dict(item) for item in result])
    return json.dumps(_chunk_dict(result))


def run(question: str) -> AgentResult:
    started = time.monotonic()
    trace_id = str(uuid.uuid4())
    trace = {"trace_id": trace_id, "seed": [], "iterations": [], "invalid_citations": [], "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}

    try:
        seed = semantic_search(question, k=6)
    except Exception as exc:
        return _save_error(trace_id, question, trace, started, f"retrieval failed: {exc}")

    trace["seed"] = [_chunk_dict(chunk) for chunk in seed]
    evidence = list(seed)
    evidence_text = "\n\n".join(
        f"<chunk path=\"{c.path}\" lines=\"{c.start_line}-{c.end_line}\">\n{c.content}\n</chunk>"
        for c in seed
    )
    messages = [
        {"role": "user", "content": f"Question: {question}\n\n<evidence>\n{evidence_text}\n</evidence>"}
    ]
    llm = LLMClient()
    tool_rounds = 0
    submitted = None
    retrieval_error = None

    while True:
        elapsed = time.monotonic() - started
        if elapsed >= 60:
            return _save_error(trace_id, question, trace, started, "wall-clock limit reached before submit_answer")
        if tool_rounds >= 5:
            messages.append({"role": "user", "content": "Tool round limit reached. Call submit_answer now. Do not call another tool."})

        try:
            response = llm.call(messages)
        except Exception as exc:
            return _save_error(trace_id, question, trace, started, str(exc))
        tin, tout = _usage(response)
        trace["tokens_in"] += tin
        trace["tokens_out"] += tout
        iteration = {"tool_calls": [], "tokens_in": tin, "tokens_out": tout}

        tool_uses = [block for block in getattr(response, "content", []) if getattr(block, "type", None) == "tool_use"]
        if not tool_uses:
            return _save_error(trace_id, question, trace, started, "model returned no tool call")

        assistant_content = getattr(response, "content", [])
        messages.append({"role": "assistant", "content": assistant_content})
        tool_results = []
        for block in tool_uses:
            name = block.name
            args = block.input
            if name == "submit_answer":
                submitted = args
                iteration["tool_calls"].append({"name": name, "arguments": args, "result_size": len(json.dumps(args))})
                trace["iterations"].append(iteration)
                break

            if tool_rounds >= 5:
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "error: tool round limit reached"})
                iteration["tool_calls"].append({"name": name, "arguments": args, "result_size": 0, "error": "tool round limit reached"})
                continue

            tool_rounds += 1
            started_tool = time.monotonic()
            try:
                if name == "semantic_search":
                    result = semantic_search(args["query"], min(args.get("k", 6), 8))
                    evidence.extend(result)
                elif name == "keyword_search":
                    result = keyword_search(args["pattern"], args.get("path_glob"), args.get("limit", 10))
                    evidence.extend(result)
                elif name == "read_file":
                    result = read_file(args["path"], args["start_line"], args["end_line"])
                    evidence.append(result)
                else:
                    raise ValueError(f"unknown tool: {name}")
                text = _tool_result(result)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": text})
                iteration["tool_calls"].append({
                    "name": name,
                    "arguments": args,
                    "result_size": len(text),
                    "ms": round((time.monotonic() - started_tool) * 1000),
                })
            except Exception as exc:
                text = f"error: {exc}"
                retrieval_error = text
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": text})
                iteration["tool_calls"].append({"name": name, "arguments": args, "result_size": len(text), "error": text})
        trace["iterations"].append(iteration)

        if submitted is not None:
            break
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    answer, schema_error = validate_schema(submitted)
    if answer is None:
        retry_message = {"role": "user", "content": f"The submitted answer failed Pydantic validation: {schema_error}. Call submit_answer with corrected JSON."}
        messages.append(retry_message)
        try:
            response = llm.call(messages)
        except Exception as exc:
            return _save_error(trace_id, question, trace, started, str(exc))
        tin, tout = _usage(response)
        trace["tokens_in"] += tin
        trace["tokens_out"] += tout
        block = next((b for b in getattr(response, "content", []) if getattr(b, "type", None) == "tool_use"), None)
        if block is None or block.name != "submit_answer":
            return _save_error(trace_id, question, trace, started, "schema retry did not call submit_answer")
        answer, schema_error = validate_schema(block.input)
        if answer is None:
            return _save_error(trace_id, question, trace, started, f"schema validation failed twice: {schema_error}")

    verified, invalid = verify_citations(answer, evidence)
    trace["invalid_citations"] = invalid
    best_seed = max((chunk.score for chunk in seed), default=0.0)
    confidence = confidence_for(verified, best_seed)
    status = status_for(answer, verified)
    latency = round((time.monotonic() - started) * 1000)
    trace["latency_ms"] = latency
    trace["retrieval_error"] = retrieval_error
    trace_json = json.loads(json.dumps(trace, default=str))
    result = AgentResult(
        status=status,
        answer=answer.answer,
        citations=verified,
        confidence=confidence,
        trace=trace_json,
    )
    _save_query(trace_id, question, result, latency)
    return result


def _save_error(trace_id: str, question: str, trace: dict, started: float, message: str) -> AgentResult:
    trace["latency_ms"] = round((time.monotonic() - started) * 1000)
    trace["error"] = message
    result = AgentResult(status="error", answer=message, citations=[], confidence="low", trace=trace)
    _save_query(trace_id, question, result, trace["latency_ms"])
    return result


def _save_query(trace_id: str, question: str, result: AgentResult, latency: int) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO queries (id, question, status, answer_json, trace_json, latency_ms, tokens_in, tokens_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    trace_id,
                    question,
                    result.status,
                    json.loads(result.model_dump_json())["answer"] if False else json.dumps({"answer": result.answer, "citations": [c.model_dump() for c in result.citations], "confidence": result.confidence}),
                    json.dumps(result.trace),
                    latency,
                    result.trace.get("tokens_in", 0),
                    result.trace.get("tokens_out", 0),
                ),
            )
