from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.db import connection
from app.agent.agent import run

app = FastAPI(title="Camply Code Explainer")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/ask")
def ask(request: AskRequest):
    result = run(request.question)
    return {
        "trace_id": result.trace.get("trace_id"),
        "status": result.status,
        "answer": result.answer,
        "citations": [citation.model_dump() for citation in result.citations],
        "confidence": result.confidence,
    }


@app.get("/trace/{trace_id}")
def trace(trace_id: str):
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT trace_json FROM queries WHERE id = %s", (trace_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "trace not found", "code": "TRACE_NOT_FOUND"})
    return row[0]


@app.get("/design-notes")
def design_notes():
    with open(__import__("pathlib").Path(__file__).parent / "design_notes.json") as handle:
        import json
        return json.load(handle)


@app.get("/health")
def health():
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM chunks")
                chunks = cur.fetchone()[0]
        return {"db": "ok", "chunks": chunks}
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": str(exc), "code": "DB_UNAVAILABLE"})


app.mount("/static", StaticFiles(directory=str(__import__("pathlib").Path(__file__).parent / "static")), name="static")


@app.get("/")
def index():
    return FileResponse(__import__("pathlib").Path(__file__).parent / "static" / "index.html")
