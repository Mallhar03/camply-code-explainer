from pathlib import Path
from app.config import settings
from app.db import connection
from app.agent.models import Chunk


def _truncate(text: str) -> str:
    if len(text) <= 6000:
        return text
    return text[:6000] + "\n[TRUNCATED]"


def _guard_path(path: str) -> Path:
    root = settings.repo_root.resolve()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path escapes REPO_ROOT")
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM files WHERE path = %s", (path,))
            if cur.fetchone() is None:
                raise ValueError("path is not indexed")
    return candidate


def keyword_search(pattern: str, path_glob: str | None = None, limit: int = 10) -> list[Chunk]:
    limit = max(1, min(limit, 10))
    where = "c.content ILIKE %s"
    params: list = [f"%{pattern}%"]
    if path_glob:
        where += " AND f.path LIKE %s"
        params.append(path_glob.replace("*", "%"))
    params.append(limit)
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT c.id, f.path, c.start_line, c.end_line, c.content
                FROM chunks c JOIN files f ON f.id = c.file_id
                WHERE {where}
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cur.fetchall()
    return [Chunk(id=r[0], path=r[1], start_line=r[2], end_line=r[3], content=_truncate(r[4])) for r in rows]


def read_file(path: str, start_line: int, end_line: int) -> Chunk:
    candidate = _guard_path(path)
    start_line = max(1, start_line)
    end_line = min(start_line + 199, end_line)
    lines = candidate.read_text(errors="replace").splitlines()
    end_line = min(end_line, len(lines))
    content = "\n".join(lines[start_line - 1:end_line])
    return Chunk(id=0, path=path, start_line=start_line, end_line=end_line, content=_truncate(content))
