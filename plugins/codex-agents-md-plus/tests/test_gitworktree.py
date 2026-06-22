from __future__ import annotations

from pathlib import Path

from agents_md_plus.gitworktree import main_worktree_root


def _make_main_repo(tmp_path: Path, name: str = "main") -> Path:
    """Make a fake "main repo" with a real `.git` directory."""
    repo = tmp_path / name
    (repo / ".git").mkdir(parents=True)
    return repo


def _make_linked_worktree(
    tmp_path: Path,
    main_repo: Path,
    name: str = "wt",
) -> Path:
    """Create a fake linked worktree pointing at `main_repo`."""
    worktree = tmp_path / name
    worktree.mkdir()
    gitdir = main_repo / ".git" / "worktrees" / name
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..", encoding="utf-8")
    (worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    return worktree


def test_regular_repo_returns_none(tmp_path: Path) -> None:
    repo = _make_main_repo(tmp_path)
    assert main_worktree_root(repo) is None


def test_linked_worktree_resolves_to_main(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    wt = _make_linked_worktree(tmp_path, main)
    assert main_worktree_root(wt) == main


def test_resolves_from_nested_subdir(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    wt = _make_linked_worktree(tmp_path, main)
    sub = wt / "a" / "b"
    sub.mkdir(parents=True)
    assert main_worktree_root(sub) == main


def test_non_git_path_returns_none(tmp_path: Path) -> None:
    assert main_worktree_root(tmp_path) is None


def test_hostile_gitfile_pointing_elsewhere_rejected(tmp_path: Path) -> None:
    _make_main_repo(tmp_path, "real-main")  # set up a real repo nearby that the gitfile does NOT point to
    decoy = tmp_path / "fake-worktrees-parent" / "worktrees" / "wt"
    decoy.mkdir(parents=True)
    (decoy / "commondir").write_text("../..", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {decoy}\n", encoding="utf-8")
    assert main_worktree_root(wt) is None


def test_missing_commondir_rejected(tmp_path: Path) -> None:
    main = _make_main_repo(tmp_path)
    gitdir = main / ".git" / "worktrees" / "wt"
    gitdir.mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    assert main_worktree_root(wt) is None


def test_garbage_gitfile_rejected(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("this is not a gitfile\n", encoding="utf-8")
    assert main_worktree_root(wt) is None
