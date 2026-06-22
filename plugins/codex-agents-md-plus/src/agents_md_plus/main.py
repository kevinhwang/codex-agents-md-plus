#!/usr/bin/env python3
"""Codex SessionStart / SubagentStart hook entry point.

Reads a Codex hook payload from stdin and emits an `additionalContext` block
(when there is content) describing the AGENTS overlays + reference index
that Codex's native discovery would not have surfaced on its own.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from . import overlay, renderer, transcript
from .config import Config
from .hookio import HookPayload, emit, parse_payload


def main() -> int:
    return run(sys.stdin, sys.stdout, sys.stderr, Config.from_env())


def run(stdin: TextIO, stdout: TextIO, stderr: TextIO, config: Config) -> int:
    raw = stdin.read()
    try:
        payload = parse_payload(raw)
    except json.JSONDecodeError as exc:
        print(f"codex-agents-md-plus: invalid hook input JSON: {exc}", file=stderr)
        return 0
    if payload is None or not payload.is_supported:
        return 0

    reply = _build_reply(payload, config)
    if reply is None:
        return 0

    emit(stdout, payload.event, reply)
    return 0


def _build_reply(payload: HookPayload, config: Config) -> str | None:
    # SubagentStart: anchor the walk to the subagent's own cwd. The transcript's
    # `session_meta.cwd` is the *parent* session's cwd, which is not the right
    # anchor for a subagent that was dispatched into a different directory.
    # SessionStart (incl. resume/clear/compact): use the transcript anchor when
    # available so the walk reflects the directory Codex was originally launched
    # from, even if the active cwd has drifted.
    session_cwd: Path | None = (
        None if payload.event == "SubagentStart" else transcript.session_start_cwd(payload.transcript_path)
    )

    built = overlay.build(payload.cwd, session_cwd, config)
    if built.is_empty:
        return None

    body, marker = renderer.render_with_marker(built)
    if payload.is_resume and _resume_already_has_marker(payload, marker):
        return None
    return f"{marker}\n\n{body}"


def _resume_already_has_marker(payload: HookPayload, marker: str) -> bool:
    path = payload.transcript_path
    if path is None or not path.is_file():
        return False
    return transcript.transcript_tail_contains(path, marker)


if __name__ == "__main__":
    raise SystemExit(main())
