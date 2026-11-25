import time
from types import SimpleNamespace
from app.config import settings

from google import genai
from google.genai import types


TOOLS = [
    {
        "name": "semantic_search",
        "description": "Search code chunks semantically.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer", "default": 6}}, "required": ["query"]},
    },
    {
        "name": "keyword_search",
        "description": "Search chunk text by case-insensitive pattern.",
        "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path_glob": {"type": ["string", "null"]}, "limit": {"type": "integer", "default": 10}}, "required": ["pattern"]},
    },
    {
        "name": "read_file",
        "description": "Read a safe slice of an indexed file.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["path", "start_line", "end_line"]},
    },
    {
        "name": "submit_answer",
        "description": "Submit the final structured answer exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "maxLength": 2500},
                "citations": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["path", "start_line", "end_line"]}},
                "insufficient_evidence": {"type": "boolean"},
            },
            "required": ["answer", "citations", "insufficient_evidence"],
        },
    },
]


class LLMClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    @staticmethod
    def _contents(messages: list[dict]):
        contents = []
        tool_names = {}
        for message in messages:
            role = "model" if message["role"] == "assistant" else "user"
            body = message["content"]
            if isinstance(body, str):
                contents.append(types.Content(role=role, parts=[types.Part(text=body)]))
                continue

            parts = []
            if role == "model":
                for block in body:
                    if getattr(block, "type", None) == "tool_use":
                        tool_names[block.id] = block.name
                        parts.append(types.Part(
                            function_call=types.FunctionCall(name=block.name, args=block.input)
                        ))
            else:
                for result in body:
                    call_name = tool_names.get(result["tool_use_id"])
                    if call_name:
                        parts.append(types.Part.from_function_response(
                            name=call_name,
                            response={"result": result["content"]},
                        ))
            if parts:
                contents.append(types.Content(role=role, parts=parts))
        return contents

    def call(self, messages: list[dict]):
        if self.client is None:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        last_error = None
        for attempt in range(3):
            try:
                function_declarations = [
                    types.FunctionDeclaration(
                        name=tool["name"],
                        description=tool["description"],
                        parameters_json_schema=tool["input_schema"],
                    )
                    for tool in TOOLS
                ]
                response = self.client.models.generate_content(
                    model=settings.llm_model,
                    contents=self._contents(messages),
                    config=types.GenerateContentConfig(
                        system_instruction=__import__("app.agent.prompts", fromlist=["SYSTEM_PROMPT"]).SYSTEM_PROMPT,
                        max_output_tokens=1200,
                        tools=[types.Tool(function_declarations=function_declarations)],
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                blocks = []
                candidate = response.candidates[0] if response.candidates else None
                for index, part in enumerate(candidate.content.parts if candidate and candidate.content else []):
                    call = getattr(part, "function_call", None)
                    if call and call.name:
                        blocks.append(SimpleNamespace(
                            type="tool_use",
                            name=call.name,
                            input=dict(call.args or {}),
                            id=getattr(call, "id", None) or f"gemini-call-{index}",
                        ))
                usage = response.usage_metadata
                return SimpleNamespace(
                    content=blocks,
                    usage=SimpleNamespace(
                        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                    ),
                )
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"LLM API failed after retries: {last_error}")
