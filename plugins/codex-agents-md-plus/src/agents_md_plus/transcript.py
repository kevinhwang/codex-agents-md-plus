"""Read the session-start `cwd` from a Codex rollout transcript.

The transcript is a JSONL file. The session-meta record (`type ==
"session_meta"`) appears near the top; we scan the first 200 lines and
stop on the first match.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_SCAN_LINE_LIMIT = 200


def session_start_cwd(transcript_path: Path | None) -> Path | None:
    """Return the recorded session-start cwd, or `None`."""
    if transcript_path is None:
        return None
    try:
        with transcript_path.expanduser().open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle):
                if line_number >= _SCAN_LINE_LIMIT:
                    return None
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("type") != "session_meta":
                    continue
                return _extract_cwd(item.get("payload"))
    except OSError:
        return None
    return None


def transcript_tail_contains(transcript_path: Path, needle: str, tail_bytes: int = 5_000_000) -> bool:
    """Whether `needle` appears in the last `tail_bytes` of the transcript."""
    try:
        with transcript_path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - tail_bytes))
            tail = handle.read().decode("utf-8", errors="ignore")
    except OSError:
        return False
    return needle in tail


def _extract_cwd(payload: Any) -> Path | None:
    if not isinstance(payload, dict):
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str):
        meta = payload.get("meta")
        cwd = meta.get("cwd") if isinstance(meta, dict) else None
    if isinstance(cwd, str) and cwd.strip():
        return Path(cwd).expanduser()
    return None
