"""Per-directory instruction-file resolution.

Three filename families are considered at each directory:

  * `AGENTS.override.md`  — project override (Codex-native; higher precedence)
  * `AGENTS.md`           — project doc       (Codex-native; default precedence)
  * `AGENTS.local.md`     — additive local overlay

Plus any user-configured fallback filenames (`Config.fallback_filenames`),
which behave like additional Codex-native project-doc names. `AGENTS.local.md`
is never treated as a fallback filename — it always occupies the overlay slot.

For a given primary directory `d_primary` and its main-worktree-parallel
directory `d_parallel` (which may be `None`), each filename family resolves
with per-file precedence: `d_primary/<name>` wins if it exists; otherwise
`d_parallel/<name>` if it exists; otherwise nothing.

The Codex-home `AGENTS.local.md` overlay is resolved separately because it is
user-tier guidance, not part of the project directory walk.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .models import LOCAL_NAME, InstructionFamily, ResolvedFile
from .paths import normalize
from .reader import read_text_capped


def resolve_codex_home_overlay(config: Config) -> ResolvedFile | None:
    if config.codex_home is None:
        return None
    return _read_if_present(normalize(config.codex_home) / LOCAL_NAME, InstructionFamily.OVERLAY, config.max_file_bytes)


def resolve_for_directory(
    primary: Path,
    parallel: Path | None,
    config: Config,
) -> tuple[ResolvedFile, ...]:
    """Resolve up to two instruction files for a directory pair.

    Returns: at most one PROJECT-family file (first existing of override /
    default / fallbacks) plus at most one OVERLAY-family file.
    """
    found: list[ResolvedFile] = []
    for candidates, family in (
        (config.native_project_filenames, InstructionFamily.PROJECT),
        ((LOCAL_NAME,), InstructionFamily.OVERLAY),
    ):
        file = _first_match(primary, parallel, candidates, family, config.max_file_bytes)
        if file is not None:
            found.append(file)
    return tuple(found)


def _first_match(
    primary: Path,
    parallel: Path | None,
    candidates: tuple[str, ...],
    family: InstructionFamily,
    max_bytes: int,
) -> ResolvedFile | None:
    """Return the first existing `candidate` under `primary`, else under `parallel`."""
    for root in (primary, parallel):
        if root is None:
            continue
        for name in candidates:
            file = _read_if_present(root / name, family, max_bytes)
            if file is not None:
                return file
    return None


def _read_if_present(path: Path, family: InstructionFamily, max_bytes: int) -> ResolvedFile | None:
    if not path.is_file():
        return None
    try:
        text, truncated = read_text_capped(path, max_bytes)
    except OSError:
        return None
    if not text.strip():
        return None
    return ResolvedFile(path=normalize(path), text=text, truncated=truncated, family=family)
