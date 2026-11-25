from types import SimpleNamespace
from app.agent import agent
from app.agent.models import Chunk


def block_tool(name, input, id="tool-1"):
    return SimpleNamespace(type="tool_use", name=name, input=input, id=id)


def response(*blocks, tin=10, tout=20):
    return SimpleNamespace(content=list(blocks), usage=SimpleNamespace(input_tokens=tin, output_tokens=tout))


def test_loop_stops_on_submit(monkeypatch):
    submitted = {
        "answer": "Camply uses refresh tokens.",
        "citations": [{"path": "src/app.ts", "start_line": 1, "end_line": 10}],
        "insufficient_evidence": False,
    }
    monkeypatch.setattr(agent, "semantic_search", lambda q, k=6: [
        Chunk(id=1, path="src/app.ts", start_line=1, end_line=10, score=.8, content="refresh")
    ])
    monkeypatch.setattr(agent, "_save_query", lambda *args: None)
    monkeypatch.setattr(agent, "LLMClient", lambda: SimpleNamespace(
        call=lambda messages: response(block_tool("submit_answer", submitted))
    ))
    result = agent.run("How are refresh tokens handled?")
    assert result.status == "answered"


def test_loop_stops_at_round_limit(monkeypatch):
    submitted = {"answer": "No answer.", "citations": [], "insufficient_evidence": True}
    chunks = [Chunk(id=1, path="src/app.ts", start_line=1, end_line=10, score=.2, content="code")]
    monkeypatch.setattr(agent, "semantic_search", lambda q, k=6: chunks)
    monkeypatch.setattr(agent, "keyword_search", lambda *args: chunks)
    monkeypatch.setattr(agent, "_save_query", lambda *args: None)
    calls = {"n": 0}
    def fake_call(messages):
        calls["n"] += 1
        if calls["n"] <= 5:
            return response(block_tool("keyword_search", {"pattern": "test"}, id=f"t{calls['n']}"))
        return response(block_tool("submit_answer", submitted))
    monkeypatch.setattr(agent, "LLMClient", lambda: SimpleNamespace(call=fake_call))
    result = agent.run("Test round limit")
    assert calls["n"] == 6
    assert result.status == "insufficient_evidence"
