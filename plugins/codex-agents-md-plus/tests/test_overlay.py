"""End-to-end tests for the `overlay.build` orchestrator."""

from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.models import InstructionRole
from agents_md_plus.overlay import build


def _make_main_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "main"
    (repo / ".git").mkdir(parents=True)
    return repo


def _make_linked_worktree(tmp_path: Path, main: Path, name: str = "wt") -> Path:
    wt = tmp_path / name
    wt.mkdir()
    gitdir = main / ".git" / "worktrees" / name
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..", encoding="utf-8")
    (wt / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    return wt


def test_simple_repo_local_overlay(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    (repo / "AGENTS.md").write_text("repo agents")
    (repo / "AGENTS.local.md").write_text("repo local")

    overlay = build(payload_cwd=repo, session_cwd=repo, config=Config())

    by_role = {f.role: f.path for f in overlay.instructions}
    assert by_role[InstructionRole.NATIVE] == (repo / "AGENTS.md").resolve()
    assert by_role[InstructionRole.OVERLAY] == (repo / "AGENTS.local.md").resolve()
    # The renderable view drops the NATIVE entry.
    renderable_paths = {f.path for f in overlay.renderable_instructions}
    assert (repo / "AGENTS.md").resolve() not in renderable_paths
    assert (repo / "AGENTS.local.md").resolve() in renderable_paths


def test_worktree_falls_back_to_main_repo_local(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    (main / "AGENTS.md").write_text("main agents")
    (main / "AGENTS.local.md").write_text("main local sentinel")
    wt = _make_linked_worktree(tmp_path, main)
    # Worktree has tracked AGENTS.md (Codex sees it natively), no AGENTS.local.md.
    (wt / "AGENTS.md").write_text("worktree agents")

    overlay = build(payload_cwd=wt, session_cwd=wt, config=Config())

    overlay_paths = {f.path for f in overlay.instructions if f.role is InstructionRole.OVERLAY}
    fallback_paths = {f.path for f in overlay.instructions if f.role is InstructionRole.FALLBACK}
    native_paths = {f.path for f in overlay.instructions if f.role is InstructionRole.NATIVE}

    assert (main / "AGENTS.local.md").resolve() in overlay_paths
    # Worktree's own AGENTS.md is on Codex's native chain → not re-rendered.
    assert (wt / "AGENTS.md").resolve() in native_paths
    # Main repo's AGENTS.md isn't pulled in once worktree has its own (per-file
    # primary-wins precedence at the per-directory pair).
    assert (main / "AGENTS.md").resolve() not in fallback_paths


def test_worktree_pulls_main_agents_when_worktree_missing(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    (main / "AGENTS.md").write_text("main agents only")
    wt = _make_linked_worktree(tmp_path, main)
    # Worktree has no AGENTS.md at all.

    overlay = build(payload_cwd=wt, session_cwd=wt, config=Config())

    fallback_paths = {f.path for f in overlay.instructions if f.role is InstructionRole.FALLBACK}
    assert (main / "AGENTS.md").resolve() in fallback_paths


def test_native_chain_dedupe_for_root_doc(tmp_path: Path) -> None:
    """An AGENTS.md at the same path Codex's walk would visit shouldn't render."""
    repo = _make_main_repo(tmp_path)
    sub = repo / "pkg"
    sub.mkdir()
    (sub / "AGENTS.md").write_text("local doc")

    overlay = build(payload_cwd=sub, session_cwd=repo, config=Config())

    renderable_paths = {f.path for f in overlay.renderable_instructions}
    assert (sub / "AGENTS.md").resolve() not in renderable_paths


def test_local_overlay_in_subdir_of_main_repo_session(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    sub = repo / "pkg"
    sub.mkdir()
    (repo / "AGENTS.md").write_text("root doc")
    (sub / "AGENTS.local.md").write_text("subdir overlay")

    overlay = build(payload_cwd=sub, session_cwd=repo, config=Config())

    overlay_paths = {f.path for f in overlay.instructions if f.role is InstructionRole.OVERLAY}
    assert (sub / "AGENTS.local.md").resolve() in overlay_paths


def test_references_resolve_through_fallback(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    (main / "AGENTS.local.md").write_text("@docs/extra.md\n")
    docs = main / "docs"
    docs.mkdir()
    (docs / "extra.md").write_text("extra-from-main-repo")
    wt = _make_linked_worktree(tmp_path, main)

    overlay = build(payload_cwd=wt, session_cwd=wt, config=Config())

    ref_paths = {r.path for r in overlay.references}
    assert (docs / "extra.md").resolve() in ref_paths


def test_empty_when_nothing_to_show(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    overlay = build(payload_cwd=repo, session_cwd=repo, config=Config())
    assert overlay.is_empty
