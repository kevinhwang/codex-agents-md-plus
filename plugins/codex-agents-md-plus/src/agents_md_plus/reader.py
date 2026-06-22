from __future__ import annotations

from pathlib import Path


def read_text_capped(path: Path, max_bytes: int) -> tuple[str, bool]:
    """Read a file up to `max_bytes`, reporting whether it was truncated.

    Reads `max_bytes + 1` to detect truncation without buffering the whole
    file. Decodes as UTF-8 with replacement for malformed bytes.
    """
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace"), truncated
