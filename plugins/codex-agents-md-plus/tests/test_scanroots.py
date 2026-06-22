from __future__ import annotations

from pathlib import Path

from agents_md_plus.scanroots import build


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


def _primaries(roots) -> tuple[Path, ...]:
    return tuple(pair.primary for pair in roots.pairs)


def _parallels(roots) -> tuple[Path | None, ...]:
    return tuple(pair.parallel for pair in roots.pairs)


def test_simple_repo_primary_chain(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    sub = repo / "pkg"
    sub.mkdir()
    roots = build(payload_cwd=sub, session_cwd=repo)
    assert _primaries(roots) == (repo.resolve(), (repo / "pkg").resolve())
    assert _parallels(roots) == (None, None)
    assert roots.extra_parallel_dirs == ()
    assert roots.native_project_root == repo.resolve()


def test_no_session_cwd_uses_payload_only(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    roots = build(payload_cwd=sub, session_cwd=None)
    # When session anchor == payload cwd, the chain is just `[payload]`.
    assert _primaries(roots) == (sub.resolve(),)


def test_unrelated_session_anchor_falls_back_to_payload(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    roots = build(payload_cwd=repo, session_cwd=elsewhere)
    assert _primaries(roots) == (repo.resolve(),)


def test_linked_worktree_pairs_each_primary_with_parallel(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    wt = _make_linked_worktree(tmp_path, main)
    pkg = wt / "pkg"
    pkg.mkdir()
    roots = build(payload_cwd=pkg, session_cwd=wt)

    assert _primaries(roots) == (wt.resolve(), (wt / "pkg").resolve())
    # Each primary is paired with the corresponding main-repo path.
    assert _parallels(roots) == (main.resolve(), (main / "pkg").resolve())
    # Extra ancestors above main are reported separately and don't overlap.
    assert tmp_path.resolve() in roots.extra_parallel_dirs
    assert main.resolve() not in roots.extra_parallel_dirs  # already paired


def test_native_project_root_inside_worktree(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    wt = _make_linked_worktree(tmp_path, main)
    roots = build(payload_cwd=wt, session_cwd=wt)
    # Worktree itself has a `.git` linkfile so it counts as the project root.
    assert roots.native_project_root == wt.resolve()
