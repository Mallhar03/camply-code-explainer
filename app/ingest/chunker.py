import re

SECRET_LINE = re.compile(r"(KEY\s*=|SECRET|TOKEN|PASSWORD|(?:[A-Za-z0-9+/]{32,}={0,2}))", re.I)


def redact_secrets(text: str) -> str:
    return "\n".join(line if not SECRET_LINE.search(line) else "[REDACTED]" for line in text.splitlines())


def chunk_file(content: str, window: int = 80, overlap: int = 15) -> list[tuple[int, int, str]]:
    lines = content.splitlines()
    if not lines:
        return []
    chunks = []
    start = 0
    step = window - overlap
    while start < len(lines):
        end = min(start + window, len(lines))
        text = "\n".join(lines[start:end]).strip()
        if text:
            chunks.append((start + 1, end, text))
        if end == len(lines):
            break
        start += step
    return chunks
