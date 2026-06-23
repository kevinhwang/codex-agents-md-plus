"""Compose primitives into an `Overlay`.

Pipeline:

  1. `scanroots.build`  — primary/parallel directory pairs + extras + native project root.
  2. For each pair, `instructions.resolve_for_directory` finds up-to-two
     `ResolvedFile`s (one PROJECT family, one OVERLAY family).
  3. Convert each `ResolvedFile` to an `InstructionFile` with the final role:
     OVERLAY for `AGENTS.local.md`, NATIVE if `nativepull` confirms Codex
     would load it natively, otherwise FALLBACK.
  4. Expand `@`-references over every instruction file (NATIVE included —
     Codex doesn't expand them on our behalf).
"""

from __future__ import annotations

from pathlib import Path

from . import instructions, native_segments, nativepull, refgraph, scanroots
from .config import Config
from .models import (
    InstructionFamily,
    InstructionFile,
    InstructionRole,
    Overlay,
    ResolvedFile,
    ScanRoots,
)
from .paths import normalize


def build(payload_cwd: Path, session_cwd: Path | None, config: Config) -> Overlay:
    roots = scanroots.build(payload_cwd, session_cwd)
    files = tuple(
        _as_instruction(raw, normalize(payload_cwd), roots.native_project_root, config)
        for raw in _discover_files(roots, config)
    )
    guards = _reference_guards(payload_cwd, session_cwd, roots, config)
    result = refgraph.expand(files, guards, config)
    native_cwd = session_cwd if session_cwd is not None else payload_cwd
    return Overlay(
        instructions=files,
        references=result.references,
        native_segments=native_segments.discover(native_cwd, config),
        skipped=result.skipped,
    )


def _discover_files(roots: ScanRoots, config: Config) -> tuple[ResolvedFile, ...]:
    """Discover instruction files across the primary + parallel walks.

    Walks each `ScanPair` (primary directory + optional parallel) and then
    each `extra_parallel_dirs` entry (ancestors of the main worktree root,
    which have no primary). Dedupes by absolute path.
    """
    seen: set[Path] = set()
    result: list[ResolvedFile] = []

    def emit(file: ResolvedFile) -> None:
        if file.path not in seen:
            seen.add(file.path)
            result.append(file)

    for pair in roots.pairs:
        for file in instructions.resolve_for_directory(pair.primary, pair.parallel, config):
            emit(file)
    for extra in roots.extra_parallel_dirs:
        for file in instructions.resolve_for_directory(extra, None, config):
            emit(file)

    return tuple(result)


def _as_instruction(
    file: ResolvedFile,
    payload_cwd: Path,
    native_root: Path | None,
    config: Config,
) -> InstructionFile:
    if file.family is InstructionFamily.OVERLAY:
        role = InstructionRole.OVERLAY
    elif nativepull.is_natively_loaded(file.path, payload_cwd, native_root, config):
        role = InstructionRole.NATIVE
    else:
        role = InstructionRole.FALLBACK
    return InstructionFile(path=file.path, text=file.text, truncated=file.truncated, role=role)


def _reference_guards(
    payload_cwd: Path,
    session_cwd: Path | None,
    roots: ScanRoots,
    config: Config,
) -> tuple[Path, ...]:
    """Where `@`-references are allowed to resolve.

    Always permits: payload cwd, session-start cwd, every parallel-walk
    root, and the extra-parallel ancestors. Empty when `allow_outside_root`
    is set — caller bypasses the check anyway.
    """
    if config.allow_outside_root:
        return ()

    guards: list[Path] = [normalize(payload_cwd)]
    if session_cwd is not None:
        guards.append(normalize(session_cwd))
    guards.extend(pair.parallel for pair in roots.pairs if pair.parallel is not None)
    guards.extend(roots.extra_parallel_dirs)
    return tuple(dict.fromkeys(guards))
