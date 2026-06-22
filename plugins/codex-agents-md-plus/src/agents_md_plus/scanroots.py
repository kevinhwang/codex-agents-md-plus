"""Plan the set of directories to scan for instruction files.

The plan is expressed as `ScanRoots`:

  * `pairs` — primary directory (an entry on the session-anchor → active-cwd
    chain) paired with its main-worktree-parallel counterpart, or `None`
    when the active cwd is not inside a linked worktree.
  * `extra_parallel_dirs` — directories above the main worktree root that
    have no primary counterpart but should still be scanned so AGENTS
    files outside both the worktree and the main repo can be discovered.
  * `native_project_root` — closest `.git`-ancestor of the active cwd
    (Codex's default project-root marker), used to decide which files
    Codex's native discovery would already have surfaced.
"""

from __future__ import annotations

from pathlib import Path

from . import gitworktree
from .models import ScanPair, ScanRoots
from .paths import chain_to, normalize


def build(payload_cwd: Path, session_cwd: Path | None) -> ScanRoots:
    payload_cwd = normalize(payload_cwd)
    anchor = normalize(session_cwd) if session_cwd is not None else payload_cwd

    primary_dirs = chain_to(anchor, payload_cwd) if payload_cwd.is_relative_to(anchor) else (payload_cwd,)

    pairs, extra = _resolve_worktree_parallels(payload_cwd, primary_dirs)
    return ScanRoots(
        pairs=pairs,
        extra_parallel_dirs=extra,
        native_project_root=_nearest_dot_git_parent(payload_cwd),
    )


def _resolve_worktree_parallels(
    payload_cwd: Path,
    primary_dirs: tuple[Path, ...],
) -> tuple[tuple[ScanPair, ...], tuple[Path, ...]]:
    """Pair each primary dir with its main-worktree-parallel path, and collect
    main-repo-ancestor dirs (which have no primary).

    Returns `(pairs, extra_parallel_dirs)`. When `payload_cwd` is not inside
    a linked git worktree, all parallels are `None` and `extra_parallel_dirs`
    is empty.
    """
    no_parallels = tuple(ScanPair(primary=p, parallel=None) for p in primary_dirs)

    main_root = gitworktree.main_worktree_root(payload_cwd)
    if main_root is None:
        return no_parallels, ()
    worktree_root = _nearest_dot_git_parent(payload_cwd)
    if worktree_root is None:
        return no_parallels, ()

    pairs: list[ScanPair] = []
    paired_parallels: set[Path] = set()
    for primary in primary_dirs:
        if primary.is_relative_to(worktree_root):
            parallel = normalize(main_root / primary.relative_to(worktree_root))
            pairs.append(ScanPair(primary=primary, parallel=parallel))
            paired_parallels.add(parallel)
        else:
            pairs.append(ScanPair(primary=primary, parallel=None))

    candidates = (normalize(path) for path in (*reversed(main_root.parents), main_root))
    extra = tuple(dict.fromkeys(path for path in candidates if path not in paired_parallels))
    return tuple(pairs), extra


def _nearest_dot_git_parent(start: Path) -> Path | None:
    for ancestor in (start, *start.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return None
