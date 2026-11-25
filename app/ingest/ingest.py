import hashlib
import time
from pathlib import Path
from pgvector.psycopg import register_vector

from app.db import connection, apply_schema
from app.ingest.walker import walk_repo
from app.ingest.chunker import chunk_file, redact_secrets
from app.ingest.embedder import embed_texts


def file_kind(path: Path) -> str:
    if path.suffix in {".ts", ".js"}:
        if "tests" in path.parts:
            return "test"
        return "code"
    if path.suffix in {".yml", ".yaml", ".json", ".prisma"}:
        return "config"
    return "doc"


def ingest() -> dict:
    apply_schema()
    indexed = skipped = chunks_created = 0
    started = time.time()
    for path in walk_repo():
        raw = path.read_text(errors="replace")
        sha = hashlib.sha256(raw.encode()).hexdigest()
        relative = path.resolve().relative_to(__import__("app.config", fromlist=["settings"]).settings.repo_root.resolve()).as_posix()
        redacted = redact_secrets(raw)
        windows = chunk_file(redacted)

        with connection() as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT id, sha256 FROM files WHERE path = %s", (relative,))
                existing = cur.fetchone()
                if existing and existing[1] == sha:
                    skipped += 1
                    continue

                cur.execute(
                    "INSERT INTO files (path, sha256, kind) VALUES (%s, %s, %s) "
                    "ON CONFLICT (path) DO UPDATE SET sha256 = EXCLUDED.sha256, kind = EXCLUDED.kind "
                    "RETURNING id",
                    (relative, sha, file_kind(path)),
                )
                file_id = cur.fetchone()[0]
                cur.execute("DELETE FROM chunks WHERE file_id = %s", (file_id,))

            texts = [
                f"File: {relative} | lines {start}-{end}\n{content}"
                for start, end, content in windows
            ]
            vectors = embed_texts(texts) if texts else []
            with conn.cursor() as cur:
                for (start, end, content), vector in zip(windows, vectors):
                    cur.execute(
                        "INSERT INTO chunks (file_id, start_line, end_line, content, embedding) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (file_id, start, end, content, vector),
                    )
                    chunks_created += 1
            indexed += 1

    return {
        "files_indexed": indexed,
        "skipped": skipped,
        "chunks_created": chunks_created,
        "seconds": round(time.time() - started, 3),
    }


if __name__ == "__main__":
    result = ingest()
    print(
        f"files indexed: {result['files_indexed']}, skipped: {result['skipped']}, "
        f"chunks created: {result['chunks_created']}, seconds: {result['seconds']}"
    )
