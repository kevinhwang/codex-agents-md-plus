"""Decides whether Codex's native AGENTS discovery would have loaded a file.

Codex's native walk:

  1. Walk up from cwd looking for a project-root marker (default ``.git``).
  2. From project root down to cwd (inclusive), for each directory pick the
     first existing of ``AGENTS.override.md``, ``AGENTS.md``, plus any
     user-configured fallback filenames. ``AGENTS.local.md`` is *not* in
     Codex's list.

So a file at ``<dir>/<name>`` is natively loaded iff:

  * ``<name>`` is in the native filename precedence list, and
  * ``<dir>`` lies on the project-root → cwd chain, and
  * ``<name>`` is the first existing candidate at ``<dir>``.

The third bullet keeps an ``AGENTS.md`` from showing up as native when an
``AGENTS.override.md`` shadows it at the same level.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .paths import chain_to


def native_chain(project_root: Path | None, cwd: Path) -> tuple[Path, ...]:
    """Directories Codex's native walk would visit."""
    if project_root is None or not cwd.is_relative_to(project_root):
        return (cwd,)
    return chain_to(project_root, cwd)


def is_natively_loaded(
    file_path: Path,
    cwd: Path,
    project_root: Path | None,
    config: Config,
) -> bool:
    """Whether Codex's native discovery would load this exact path."""
    candidates = config.native_project_filenames
    if file_path.name not in candidates:
        return False
    if file_path.parent not in native_chain(project_root, cwd):
        return False
    for candidate in candidates:
        candidate_path = file_path.parent / candidate
        if candidate_path == file_path:
            return True
        if candidate_path.is_file():
            return False
    return False
