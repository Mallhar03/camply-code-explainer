from app.agent.models import Answer, Citation, Chunk
from app.agent.validate import verify_citations


def test_citation_validator_drops_unseen_citation():
    evidence = [Chunk(id=1, path="src/app.ts", start_line=10, end_line=40, content="code")]
    answer = Answer(answer="uses app", citations=[
        Citation(path="src/app.ts", start_line=20, end_line=30),
        Citation(path="src/secret.ts", start_line=1, end_line=5),
    ], insufficient_evidence=False)
    verified, invalid = verify_citations(answer, evidence)
    assert len(verified) == 1
    assert invalid[0]["citation"]["path"] == "src/secret.ts"
