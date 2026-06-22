"""Top-of-stack tests for the hook entry point (`agents_md_plus.main.run`)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.main import run
from agents_md_plus.renderer import MARKER_PREFIX


def _payload(
    cwd: Path, *, event: str = "SessionStart", source: str = "startup", transcript: Path | None = None
) -> dict:
    p = {
        "session_id": "session-1",
        "transcript_path": str(transcript) if transcript else None,
        "cwd": str(cwd),
        "hook_event_name": event,
        "model": "gpt-test",
        "permission_mode": "workspace-write",
    }
    if event == "SessionStart":
        p["source"] = source
    if event == "SubagentStart":
        p["turn_id"] = "turn-1"
        p["agent_id"] = "agent-1"
        p["agent_type"] = "default"
    return p


def _additional_context(stdout: io.StringIO) -> str:
    raw = stdout.getvalue().strip()
    if not raw:
        return ""
    parsed = json.loads(raw)
    return parsed["hookSpecificOutput"]["additionalContext"]


def _write_session_meta(tmp_path: Path, cwd: Path) -> Path:
    transcript = tmp_path / "rollout.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "timestamp": "2026-06-17T00:00:00Z",
                "type": "session_meta",
                "payload": {"id": "session-1", "cwd": str(cwd), "originator": "t"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return transcript


def test_session_start_emits_when_overlay_present(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "AGENTS.local.md").write_text("local overlay")
    stdin = io.StringIO(json.dumps(_payload(repo)))
    stdout = io.StringIO()
    rc = run(stdin, stdout, io.StringIO(), Config())
    assert rc == 0
    text = _additional_context(stdout)
    assert MARKER_PREFIX in text
    assert "local overlay" in text


def test_emits_nothing_for_empty_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    stdin = io.StringIO(json.dumps(_payload(repo)))
    stdout = io.StringIO()
    rc = run(stdin, stdout, io.StringIO(), Config())
    assert rc == 0
    assert stdout.getvalue() == ""


def test_subagent_start_uses_correct_event_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "AGENTS.local.md").write_text("subagent overlay")
    stdin = io.StringIO(json.dumps(_payload(repo, event="SubagentStart")))
    stdout = io.StringIO()
    rc = run(stdin, stdout, io.StringIO(), Config())
    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["hookSpecificOutput"]["hookEventName"] == "SubagentStart"


def test_unsupported_event_emits_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "AGENTS.local.md").write_text("x")
    stdin = io.StringIO(json.dumps({**_payload(repo), "hook_event_name": "PreToolUse"}))
    stdout = io.StringIO()
    rc = run(stdin, stdout, io.StringIO(), Config())
    assert rc == 0
    assert stdout.getvalue() == ""


def test_empty_stdin(tmp_path: Path) -> None:
    rc = run(io.StringIO(""), io.StringIO(), io.StringIO(), Config())
    assert rc == 0


def test_invalid_json_logged_and_zero_exit() -> None:
    stderr = io.StringIO()
    rc = run(io.StringIO("not json"), io.StringIO(), stderr, Config())
    assert rc == 0
    assert "invalid hook input JSON" in stderr.getvalue()


def test_resume_suppresses_same_hash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "AGENTS.local.md").write_text("local overlay")
    # First emit: capture stdout and stash it in the transcript file.
    transcript = tmp_path / "rollout.jsonl"
    stdin = io.StringIO(json.dumps(_payload(repo, transcript=transcript)))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())
    transcript.write_text(stdout.getvalue(), encoding="utf-8")

    # Second emit, now `source=resume`: should suppress.
    stdin2 = io.StringIO(json.dumps(_payload(repo, source="resume", transcript=transcript)))
    stdout2 = io.StringIO()
    run(stdin2, stdout2, io.StringIO(), Config())
    assert stdout2.getvalue() == ""


def test_resume_emits_when_content_changed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    local = repo / "AGENTS.local.md"
    local.write_text("v1")
    transcript = tmp_path / "rollout.jsonl"
    stdin = io.StringIO(json.dumps(_payload(repo, transcript=transcript)))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())
    transcript.write_text(stdout.getvalue(), encoding="utf-8")

    local.write_text("v2")
    stdin2 = io.StringIO(json.dumps(_payload(repo, source="resume", transcript=transcript)))
    stdout2 = io.StringIO()
    run(stdin2, stdout2, io.StringIO(), Config())
    text = _additional_context(stdout2)
    assert "v2" in text
    assert MARKER_PREFIX in text


def test_transcript_anchor_above_payload_cwd(tmp_path: Path) -> None:
    project = tmp_path / "project"
    cwd = project / "worktree" / "child"
    cwd.mkdir(parents=True)
    (cwd / "AGENTS.md").write_text("@../../shared.md")
    (project / "shared.md").write_text("Shared project docs.")
    stdin = io.StringIO(json.dumps(_payload(cwd, transcript=_write_session_meta(tmp_path, project))))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())
    text = _additional_context(stdout)
    assert "Shared project docs." in text


def test_missing_transcript_falls_back_to_cwd(tmp_path: Path) -> None:
    project = tmp_path / "project"
    cwd = project / "child"
    cwd.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.local.md").write_text("Project overlay")
    (cwd / "AGENTS.local.md").write_text("Cwd overlay")
    stdin = io.StringIO(json.dumps(_payload(cwd, transcript=tmp_path / "missing.jsonl")))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())
    text = _additional_context(stdout)
    assert "Cwd overlay" in text
    # No transcript anchor → walk doesn't ascend, so the project-level overlay is missed.
    assert "Project overlay" not in text


def test_subagent_ignores_transcript_anchor(tmp_path: Path) -> None:
    """A subagent's walk is anchored to its own cwd, not the parent session's.

    Setup: parent session launched at `project/`; subagent dispatched at
    `project/leaf` (an ancestor walk would normally include `project/AGENTS.local.md`).
    With the SubagentStart-specific anchor logic, the walk should start at `leaf`
    and *not* climb into `project/`.
    """
    project = tmp_path / "project"
    leaf = project / "leaf"
    leaf.mkdir(parents=True)
    (project / "AGENTS.local.md").write_text("Parent-session overlay")
    (leaf / "AGENTS.local.md").write_text("Subagent overlay")
    transcript = _write_session_meta(tmp_path, project)

    stdin = io.StringIO(json.dumps(_payload(leaf, event="SubagentStart", transcript=transcript)))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())

    text = _additional_context(stdout)
    assert "Subagent overlay" in text
    assert "Parent-session overlay" not in text


def test_session_start_still_uses_transcript_anchor(tmp_path: Path) -> None:
    """SessionStart with a transcript anchor still walks from the recorded cwd."""
    project = tmp_path / "project"
    leaf = project / "leaf"
    leaf.mkdir(parents=True)
    (project / "AGENTS.local.md").write_text("Parent overlay")
    (leaf / "AGENTS.local.md").write_text("Leaf overlay")
    transcript = _write_session_meta(tmp_path, project)

    stdin = io.StringIO(json.dumps(_payload(leaf, transcript=transcript)))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())

    text = _additional_context(stdout)
    assert "Parent overlay" in text
    assert "Leaf overlay" in text


def test_compact_json_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "AGENTS.local.md").write_text("x")
    stdin = io.StringIO(json.dumps(_payload(repo)))
    stdout = io.StringIO()
    run(stdin, stdout, io.StringIO(), Config())
    line = stdout.getvalue().rstrip("\n")
    parsed = json.loads(line)
    assert "hookSpecificOutput" in parsed
    assert " " not in line[:50]  # compact, no pretty-printed whitespace at the start
