from contextlib import contextmanager
from pathlib import Path
import psycopg

from app.config import settings


@contextmanager
def connection():
    with psycopg.connect(settings.database_url) as conn:
        yield conn


def apply_schema() -> None:
    sql = (Path(__file__).parent / "schema.sql").read_text()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
