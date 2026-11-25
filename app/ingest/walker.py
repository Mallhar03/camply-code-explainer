from pathlib import Path
from app.config import settings

EXCLUDED_PARTS = {"node_modules", "dist", ".git", ".env"}


def is_allowlisted(path: Path) -> bool:
    root = settings.repo_root.resolve()
    relative = path.resolve().relative_to(root)
    text = relative.as_posix()
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if text == "prisma/schema.prisma" or text == "README.md":
        return True
    return text.startswith("src/") or text.startswith("tests/") or text.startswith(".github/workflows/")


def walk_repo() -> list[Path]:
    root = settings.repo_root.resolve()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith(".env"):
            continue
        try:
            if not is_allowlisted(path):
                continue
            if path.stat().st_size > 200 * 1024:
                continue
        except (ValueError, OSError):
            continue
        files.append(path)
    return files
