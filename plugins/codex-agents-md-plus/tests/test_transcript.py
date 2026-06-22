from __future__ import annotations

import json
from pathlib import Path

from agents_md_plus.transcript import session_start_cwd, transcript_tail_contains


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n", encoding="utf-8")


def test_reads_session_meta_cwd(tmp_path: Path) -> None:
    transcript = tmp_path / "rollout.jsonl"
    _write_jsonl(
        transcript,
        [
            {"type": "noise", "payload": {}},
            {"type": "session_meta", "payload": {"cwd": "/repo/origin"}},
        ],
    )
    assert session_start_cwd(transcript) == Path("/repo/origin")


def test_falls_back_to_meta_dot_cwd(tmp_path: Path) -> None:
    transcript = tmp_path / "rollout.jsonl"
    _write_jsonl(
        transcript,
        [
            {"type": "session_meta", "payload": {"meta": {"cwd": "/inner/cwd"}}},
        ],
    )
    assert session_start_cwd(transcript) == Path("/inner/cwd")


def test_returns_none_when_no_session_meta(tmp_path: Path) -> None:
    transcript = tmp_path / "rollout.jsonl"
    _write_jsonl(transcript, [{"type": "noise"}])
    assert session_start_cwd(transcript) is None


def test_returns_none_when_path_none() -> None:
    assert session_start_cwd(None) is None


def test_returns_none_when_path_missing(tmp_path: Path) -> None:
    assert session_start_cwd(tmp_path / "missing.jsonl") is None


def test_tail_contains_marker(tmp_path: Path) -> None:
    transcript = tmp_path / "rollout.jsonl"
    transcript.write_text("preamble\n<!-- needle-here -->\ntrailer\n", encoding="utf-8")
    assert transcript_tail_contains(transcript, "<!-- needle-here -->")
    assert not transcript_tail_contains(transcript, "<!-- absent -->")
