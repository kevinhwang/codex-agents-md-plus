"""Pure-Python git worktree resolution.

Given a directory inside a linked git worktree, resolves the working tree of
the *main* worktree (the one whose `.git` is a real directory). Returns
`None` for non-repos, the main worktree itself, or any path whose `.git`
linkfile chain fails validation.

The validation chain (modeled after the same defense-in-depth Claude Code
applies in its worktree resolver):

  1. Find the nearest ancestor `d` of the input path with a `.git` entry.
  2. If `.git` is a directory, `d` is the main worktree → return `None`.
  3. If `.git` is a file, read it; require a `gitdir:` line.
  4. Resolve the gitdir absolutely. It must look like
     `<main_repo>/.git/worktrees/<name>` — parent named `worktrees`.
  5. Read `<gitdir>/commondir` and resolve to `<main_repo>/.git`.
  6. The `worktrees/<name>` directory referenced by the gitdir line and the
     `worktrees/<name>` directory reachable from the main-repo `.git` must
     refer to the same path (symmetry check). This blocks a hostile `.git`
     file from redirecting our overlay walk to an arbitrary directory.
  7. Return `<main_repo_dot_git>.parent` = the main worktree.

No git binary needed; no filesystem state changes.
"""

from __future__ import annotations

from pathlib import Path


def main_worktree_root(start: Path) -> Path | None:
    """Return the main worktree's working-tree root, or `None`."""
    git_entry = _find_nearest_git_entry(start)
    if git_entry is None:
        return None

    # Regular working tree: `.git` is a directory.
    if git_entry.is_dir():
        return None

    if not git_entry.is_file():
        return None

    gitdir = _parse_gitdir_line(git_entry)
    if gitdir is None:
        return None

    if gitdir.parent.name != "worktrees":
        return None

    commondir = _read_commondir(gitdir)
    if commondir is None:
        return None

    if commondir.name != ".git":
        return None

    # Symmetry: the worktree pointer reachable from the main repo's .git
    # must resolve to the same on-disk directory we got from `.git`'s
    # gitdir: line.
    reflected = commondir / "worktrees" / gitdir.name
    try:
        if reflected.resolve(strict=False) != gitdir.resolve(strict=False):
            return None
    except OSError:
        return None

    return commondir.parent


def _find_nearest_git_entry(start: Path) -> Path | None:
    start = start.expanduser().resolve(strict=False)
    for ancestor in (start, *start.parents):
        candidate = ancestor / ".git"
        if candidate.exists():
            return candidate
    return None


def _parse_gitdir_line(git_file: Path) -> Path | None:
    try:
        contents = git_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in contents.splitlines():
        line = line.strip()
        if not line.startswith("gitdir:"):
            continue
        value = line[len("gitdir:") :].strip()
        if not value:
            return None
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = (git_file.parent / candidate).resolve(strict=False)
        return candidate
    return None


def _read_commondir(gitdir: Path) -> Path | None:
    commondir_file = gitdir / "commondir"
    try:
        contents = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not contents:
        return None
    candidate = Path(contents).expanduser()
    if not candidate.is_absolute():
        candidate = (gitdir / candidate).resolve(strict=False)
    return candidate
