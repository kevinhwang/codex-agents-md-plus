"""Path utilities used across modules."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def normalize(path: Path) -> Path:
    """Expand `~` and resolve symlinks/`..` without requiring the path to exist."""
    return path.expanduser().resolve(strict=False)


def is_within_any(path: Path, roots: Iterable[Path]) -> bool:
    """Whether `path` is at-or-under any of `roots` (after resolution)."""
    return any(path.is_relative_to(root.resolve(strict=False)) for root in roots)


def chain_to(root: Path, leaf: Path) -> tuple[Path, ...]:
    """Ordered directories from `root` to `leaf` inclusive.

    If `leaf` is not under `root`, returns just `(leaf,)`.
    """
    root = root.resolve(strict=False)
    leaf = leaf.resolve(strict=False)
    if not leaf.is_relative_to(root):
        return (leaf,)

    dirs: list[Path] = [root]
    current = root
    for part in leaf.relative_to(root).parts:
        current = current / part
        dirs.append(current)
    return tuple(dirs)
