"""Runtime configuration parsed from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .models import LOCAL_NAME

_PREFIX = "CODEX_AGENTS_MD_PLUS_"


@dataclass(frozen=True)
class Config:
    max_depth: int = 5
    max_files: int = 32
    max_file_bytes: int = 32 * 1024
    max_total_reference_bytes: int = 128 * 1024
    allow_outside_root: bool = False
    fallback_filenames: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Config:
        environ = environ if environ is not None else dict(os.environ)
        return cls(
            max_depth=_env_int(environ, f"{_PREFIX}MAX_DEPTH", cls.max_depth),
            max_files=_env_int(environ, f"{_PREFIX}MAX_FILES", cls.max_files),
            max_file_bytes=_env_int(environ, f"{_PREFIX}MAX_FILE_BYTES", cls.max_file_bytes),
            max_total_reference_bytes=_env_int(
                environ,
                f"{_PREFIX}MAX_TOTAL_REFERENCE_BYTES",
                cls.max_total_reference_bytes,
            ),
            allow_outside_root=_env_bool(environ, f"{_PREFIX}ALLOW_OUTSIDE_ROOT", cls.allow_outside_root),
            fallback_filenames=_env_csv(environ, f"{_PREFIX}FALLBACK_FILENAMES"),
        )

    @property
    def native_project_filenames(self) -> tuple[str, ...]:
        """Filenames Codex's native discovery considers, in precedence order.

        Always starts with `AGENTS.override.md` then `AGENTS.md`, then any
        user-configured `fallback_filenames` not already listed. The reserved
        `AGENTS.local.md` slot is excluded — that name is the overlay slot,
        not a project-doc fallback.
        """
        names: list[str] = ["AGENTS.override.md", "AGENTS.md"]
        for name in self.fallback_filenames:
            if not name or name == LOCAL_NAME or name in names:
                continue
            names.append(name)
        return tuple(names)


def _env_int(environ: dict[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(0, value)


def _env_bool(environ: dict[str, str], name: str, default: bool) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(environ: dict[str, str], name: str) -> tuple[str, ...]:
    raw = environ.get(name, "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())
