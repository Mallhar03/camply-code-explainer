from pgvector.psycopg import register_vector
from app.db import connection
from app.agent.models import Chunk
from app.ingest.embedder import embed_texts


def semantic_search(query: str, k: int = 6) -> list[Chunk]:
    k = max(1, min(k, 8))
    vector = embed_texts([query])[0]
    with connection() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, f.path, c.start_line, c.end_line, c.content,
                       1 - (c.embedding <=> %s::vector) AS score
                FROM chunks c JOIN files f ON f.id = c.file_id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (vector, vector, k),
            )
            rows = cur.fetchall()
    return [
        Chunk(id=row[0], path=row[1], start_line=row[2], end_line=row[3], content=row[4], score=float(row[5]))
        for row in rows
    ]
