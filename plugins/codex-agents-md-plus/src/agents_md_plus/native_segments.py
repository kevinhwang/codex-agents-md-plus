"""Discover filesystem-backed AGENTS files Codex renders natively.

This mirrors Codex's current AGENTS assembly for local filesystem sessions:

  * Codex-home user instructions: first non-empty of `AGENTS.override.md`,
    then `AGENTS.md`.
  * Project docs: for each directory from project root to cwd, the first
    existing candidate of `AGENTS.override.md`, `AGENTS.md`, then configured
    fallback names. If that selected file is empty, it contributes nothing and
    still shadows later candidates in the same directory.

The output is metadata only. Native file bodies are already present in Codex's
own `<INSTRUCTIONS>` block, so the renderer uses these records as a compact
provenance map rather than duplicating content.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .models import NativeSegment
from .paths import chain_to, normalize
from .reader import read_text_capped

_GLOBAL_NATIVE_FILENAMES = ("AGENTS.override.md", "AGENTS.md")


def discover(cwd: Path, config: Config) -> tuple[NativeSegment, ...]:
    cwd = normalize(cwd)
    segments: list[NativeSegment] = []

    global_segment = _discover_global(config)
    if global_segment is not None:
        segments.append(global_segment)

    segments.extend(_discover_project(cwd, config))
    return tuple(segments)


def _discover_global(config: Config) -> NativeSegment | None:
    if config.codex_home is None:
        return None
    codex_home = normalize(config.codex_home)
    for name in _GLOBAL_NATIVE_FILENAMES:
        segment = _read_segment_if_file(codex_home / name, config.max_file_bytes)
        if segment is not None:
            return segment
    return None


def _discover_project(cwd: Path, config: Config) -> tuple[NativeSegment, ...]:
    root = _nearest_project_root(cwd)
    remaining = config.max_file_bytes
    segments: list[NativeSegment] = []

    for directory in chain_to(root, cwd):
        if remaining == 0:
            break
        path = _first_existing_candidate(directory, config.native_project_filenames)
        if path is None:
            continue

        segment, bytes_read = _read_project_segment(path, remaining)
        remaining = max(0, remaining - bytes_read)
        if segment is not None:
            segments.append(segment)

    return tuple(segments)


def _nearest_project_root(start: Path) -> Path:
    for ancestor in (start, *start.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return start


def _first_existing_candidate(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = directory / name
        if path.is_file():
            return path
    return None


def _read_segment_if_file(path: Path, max_bytes: int) -> NativeSegment | None:
    if not path.is_file():
        return None
    try:
        text, _ = read_text_capped(path, max_bytes)
    except OSError:
        return None
    text = text.strip()
    if not text:
        return None
    return NativeSegment(path=normalize(path), first_line=_first_nonempty_line(text))


def _read_project_segment(path: Path, max_bytes: int) -> tuple[NativeSegment | None, int]:
    try:
        text, _ = read_text_capped(path, max_bytes)
    except OSError:
        return None, 0
    try:
        bytes_read = min(path.stat().st_size, max_bytes)
    except OSError:
        bytes_read = len(text.encode("utf-8", errors="replace"))
    if not text.strip():
        return None, bytes_read
    return NativeSegment(path=normalize(path), first_line=_first_nonempty_line(text)), bytes_read


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""
