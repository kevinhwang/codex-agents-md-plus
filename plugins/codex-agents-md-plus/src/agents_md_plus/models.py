"""Typed values that flow between the plugin's primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

LOCAL_NAME = "AGENTS.local.md"
"""Filename of the additive local overlay. Reserved — never used as a fallback."""


class InstructionRole(StrEnum):
    """Final role of an instruction file in the rendered overlay.

    NATIVE   - Codex's own walk would have loaded this file; the plugin skips
               re-rendering its body to avoid duplicating it.
    OVERLAY  - an `AGENTS.local.md` file. Codex never loads these; the plugin
               always renders them.
    FALLBACK - a project-typed file pulled in via the worktree-parallel walk
               that Codex's native walk would not reach. The plugin renders it.
    """

    NATIVE = "native"
    OVERLAY = "overlay"
    FALLBACK = "fallback"


class InstructionFamily(StrEnum):
    """Discovery-time classification, before native-pull reclassification.

    PROJECT - one of `AGENTS.override.md` / `AGENTS.md` / configured fallback
              names (first match wins at each directory).
    OVERLAY - `AGENTS.local.md`.
    """

    PROJECT = "project"
    OVERLAY = "overlay"


@dataclass(frozen=True)
class ResolvedFile:
    """An instruction file located by `instructions.resolve_for_directory`."""

    path: Path
    text: str
    truncated: bool
    family: InstructionFamily


@dataclass(frozen=True)
class InstructionFile:
    path: Path
    text: str
    truncated: bool
    role: InstructionRole


@dataclass(frozen=True)
class ReferenceDoc:
    path: Path
    text: str
    truncated: bool


@dataclass(frozen=True)
class SkippedReference:
    token: str
    source: Path
    reason: str


@dataclass(frozen=True)
class ScanPair:
    """A primary directory and its optional worktree-parallel counterpart.

    `parallel` is the corresponding path in the main worktree when the
    active cwd is inside a linked git worktree; `None` otherwise.
    """

    primary: Path
    parallel: Path | None


@dataclass(frozen=True)
class ScanRoots:
    """Directories to inspect for instruction files.

    `pairs` walks top-down from the session anchor down to the active cwd,
    with each primary directory paired with its main-worktree counterpart
    (or `None` when not in a linked worktree).

    `extra_parallel_dirs` are paths above the main-worktree root (ancestors
    of the main repo). They have no primary counterpart and are scanned
    standalone so AGENTS files outside both the worktree and the main repo
    (e.g., an overlay at `$HOME`) can be discovered.

    `native_project_root` is the closest `.git`-ancestor of the active cwd
    (Codex's default project-root marker). Used to decide which files
    Codex would already have surfaced natively.
    """

    pairs: tuple[ScanPair, ...]
    extra_parallel_dirs: tuple[Path, ...]
    native_project_root: Path | None


@dataclass(frozen=True)
class ExpandResult:
    """Output of `refgraph.expand`."""

    references: tuple[ReferenceDoc, ...]
    skipped: tuple[SkippedReference, ...]


@dataclass(frozen=True)
class Overlay:
    """Final structured result of a walk, ready for rendering."""

    instructions: tuple[InstructionFile, ...]
    references: tuple[ReferenceDoc, ...]
    skipped: tuple[SkippedReference, ...]

    @property
    def renderable_instructions(self) -> tuple[InstructionFile, ...]:
        """Instructions whose body should be emitted (excludes NATIVE)."""
        return tuple(item for item in self.instructions if item.role is not InstructionRole.NATIVE)

    @property
    def is_empty(self) -> bool:
        if self.references or self.skipped:
            return False
        return not any(item.role is not InstructionRole.NATIVE for item in self.instructions)
