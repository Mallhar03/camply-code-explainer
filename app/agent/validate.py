from pydantic import ValidationError
from app.agent.models import Answer, Citation, Chunk
from app.config import settings


def validate_schema(value: dict) -> tuple[Answer | None, str | None]:
    try:
        return Answer.model_validate(value), None
    except ValidationError as exc:
        return None, exc.json()


def verify_citations(answer: Answer, evidence: list[Chunk]) -> tuple[list[Citation], list[dict]]:
    verified = []
    invalid = []
    seen = {(chunk.path, chunk.start_line, chunk.end_line) for chunk in evidence}
    for citation in answer.citations:
        overlap = any(
            citation.path == path and citation.start_line <= end and citation.end_line >= start
            for path, start, end in seen
        )
        if overlap:
            if citation not in verified:
                verified.append(citation)
        else:
            invalid.append({"citation": citation.model_dump(), "reason": "no overlap with evidence seen in this run"})
    return verified, invalid


def confidence_for(citations: list[Citation], best_seed_score: float) -> str:
    if len(citations) >= 2 and best_seed_score >= settings.sim_threshold:
        return "high"
    if len(citations) >= 1:
        return "medium"
    return "low"


def status_for(answer: Answer, citations: list[Citation]) -> str:
    if answer.insufficient_evidence:
        return "insufficient_evidence"
    if not citations and len(answer.answer) > 20:
        return "insufficient_evidence"
    return "answered"
