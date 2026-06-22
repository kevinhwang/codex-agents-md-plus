"""Codex hook input/output. The transport contract is JSON over stdio."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

SUPPORTED_EVENTS = frozenset({"SessionStart", "SubagentStart"})


@dataclass(frozen=True)
class HookPayload:
    """Typed view of the Codex hook stdin JSON.

    Codex's hook protocol passes a JSON object on stdin with at minimum:
    `hook_event_name`, `cwd`, and (for SessionStart) `source`. Fields are
    coerced/validated here so downstream code never touches the raw dict.
    """

    event: str
    cwd: Path
    source: str | None
    transcript_path: Path | None

    @property
    def is_supported(self) -> bool:
        return self.event in SUPPORTED_EVENTS

    @property
    def is_resume(self) -> bool:
        return self.event == "SessionStart" and self.source == "resume"


def parse_payload(raw: str) -> HookPayload | None:
    """Parse a hook payload off stdin; return `None` for empty input."""
    if not raw.strip():
        return None
    obj: Any = json.loads(raw)
    if not isinstance(obj, dict):
        return None

    event = obj.get("hook_event_name") or obj.get("hookEventName")
    if not isinstance(event, str):
        return None

    cwd_text = obj.get("cwd")
    if not isinstance(cwd_text, str) or not cwd_text.strip():
        return None

    raw_source = obj.get("source")
    source = raw_source if isinstance(raw_source, str) else None
    raw_transcript = obj.get("transcript_path")
    transcript_path = Path(raw_transcript).expanduser() if isinstance(raw_transcript, str) and raw_transcript else None

    return HookPayload(
        event=event,
        cwd=Path(cwd_text).expanduser(),
        source=source,
        transcript_path=transcript_path,
    )


def emit(stdout: TextIO, event: str, additional_context: str) -> None:
    """Write the Codex hook reply (compact JSON, trailing newline)."""
    result = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": additional_context,
        }
    }
    stdout.write(json.dumps(result, separators=(",", ":")))
    stdout.write("\n")
