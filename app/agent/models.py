from pydantic import BaseModel, Field


class Chunk(BaseModel):
    id: int
    path: str
    start_line: int
    end_line: int
    score: float = 0.0
    content: str


class Citation(BaseModel):
    path: str
    start_line: int
    end_line: int


class Answer(BaseModel):
    answer: str = Field(max_length=2500)
    citations: list[Citation]
    insufficient_evidence: bool


class TraceStep(BaseModel):
    kind: str
    detail: dict
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0


class AgentResult(BaseModel):
    status: str
    answer: str
    citations: list[Citation]
    confidence: str
    trace: dict
