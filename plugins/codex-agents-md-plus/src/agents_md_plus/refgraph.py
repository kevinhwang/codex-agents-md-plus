"""BFS expansion of `@`-references with budget + cycle tracking."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import references
from .config import Config
from .models import ExpandResult, InstructionFile, ReferenceDoc, SkippedReference
from .paths import is_within_any, normalize
from .reader import read_text_capped

# Headroom subtracted from `max_total_reference_bytes` to account for the
# renderer's non-content overhead: preamble, section headings + intros,
# per-file `<file:HASH path="...">` wrappers, the outer `<agents_md_extra_context>`
# wrapper, the SHA-256 marker comment, and the skipped-references list.
# A conservative flat value — the renderer's overhead is bounded by a small
# constant per file (~200 B) plus ~2 KB fixed for preamble + section bodies.
_RENDER_OVERHEAD_HEADROOM_BYTES = 4 * 1024


@dataclass(frozen=True)
class _PendingRef:
    source: Path
    token: str
    target: Path
    depth: int
    guards: tuple[Path, ...]


class _DropKind(Enum):
    """Why a reference is dropped without being read."""

    SILENT = "silent"  # already seen or is a seed — no skip entry
    REPORT = "report"  # record as a SkippedReference for the renderer


@dataclass(frozen=True)
class _Drop:
    kind: _DropKind
    reason: str = ""


def expand(
    seeds: tuple[InstructionFile, ...],
    guards: tuple[Path, ...],
    config: Config,
    *,
    seed_guards: Mapping[Path, tuple[Path, ...]] | None = None,
) -> ExpandResult:
    """Walk `@`-references starting from `seeds`.

    `guards` bounds where references can resolve — files outside every guard
    are skipped unless `config.allow_outside_root` is True. Seeds themselves
    are excluded from the result (they're rendered separately).
    """
    seed_paths = {item.path for item in seeds}
    references_out: list[ReferenceDoc] = []
    skipped: list[SkippedReference] = []
    seen: set[Path] = set()
    pending: deque[_PendingRef] = deque()
    effective_budget = max(0, config.max_total_reference_bytes - _RENDER_OVERHEAD_HEADROOM_BYTES)

    seed_guards = seed_guards or {}
    for seed in seeds:
        _enqueue_from(pending, seed.path, seed.text, depth=1, guards=seed_guards.get(seed.path, guards))

    total_bytes = 0
    while pending:
        ref = pending.popleft()
        target = normalize(ref.target)

        drop = _classify(ref, target, seed_paths, seen, len(references_out), total_bytes, effective_budget, config)
        if drop is not None:
            if drop.kind is _DropKind.REPORT:
                skipped.append(SkippedReference(token=ref.token, source=ref.source, reason=drop.reason))
            continue

        remaining = effective_budget - total_bytes
        try:
            text, truncated = read_text_capped(target, min(config.max_file_bytes, remaining))
        except OSError as exc:
            skipped.append(SkippedReference(token=ref.token, source=ref.source, reason=f"failed to read target: {exc}"))
            continue

        total_bytes += len(text.encode("utf-8", errors="replace"))
        seen.add(target)
        references_out.append(ReferenceDoc(path=target, text=text, truncated=truncated))

        _enqueue_from(pending, target, text, depth=ref.depth + 1, guards=ref.guards)

    return ExpandResult(references=tuple(references_out), skipped=tuple(skipped))


def _enqueue_from(
    pending: deque[_PendingRef],
    source: Path,
    text: str,
    *,
    depth: int,
    guards: tuple[Path, ...],
) -> None:
    """Tokenize `text` and enqueue each `@`-reference as a `_PendingRef`."""
    for token in references.extract_tokens(text):
        pending.append(
            _PendingRef(
                source=source,
                token=token,
                target=references.resolve(token, source.parent),
                depth=depth,
                guards=guards,
            )
        )


def _classify(
    ref: _PendingRef,
    target: Path,
    seed_paths: set[Path],
    seen: set[Path],
    accepted_count: int,
    total_bytes: int,
    effective_budget: int,
    config: Config,
) -> _Drop | None:
    """Whether to drop this pending reference, and how to report it."""
    if ref.depth > config.max_depth:
        return _Drop(_DropKind.REPORT, f"max depth {config.max_depth} exceeded")
    if target in seed_paths or target in seen:
        return _Drop(_DropKind.SILENT)
    if not config.allow_outside_root and not is_within_any(target, ref.guards):
        guards_text = "; ".join(str(g) for g in ref.guards)
        return _Drop(_DropKind.REPORT, f"resolved outside session/cwd guards: {guards_text}")
    if not references.looks_like_text_file(target):
        return _Drop(_DropKind.REPORT, "target does not look like a text file")
    if not target.is_file():
        return _Drop(_DropKind.REPORT, "target is not a readable file")
    if accepted_count >= config.max_files:
        return _Drop(_DropKind.REPORT, f"max referenced files {config.max_files} reached")
    if effective_budget - total_bytes <= 0:
        return _Drop(_DropKind.REPORT, f"max total referenced bytes {config.max_total_reference_bytes} reached")
    return None
