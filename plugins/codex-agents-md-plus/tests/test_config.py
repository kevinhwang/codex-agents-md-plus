from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config


def test_defaults_when_env_empty() -> None:
    cfg = Config.from_env({})
    assert cfg.max_depth == 5
    assert cfg.max_files == 32
    assert cfg.max_file_bytes == 32 * 1024
    assert cfg.max_total_reference_bytes == 128 * 1024
    assert cfg.allow_outside_root is False
    assert cfg.fallback_filenames == ()
    assert cfg.codex_home == Path.home() / ".codex"


def test_env_parsing() -> None:
    cfg = Config.from_env(
        {
            "CODEX_AGENTS_MD_PLUS_MAX_DEPTH": "9",
            "CODEX_AGENTS_MD_PLUS_MAX_FILES": "1",
            "CODEX_AGENTS_MD_PLUS_MAX_FILE_BYTES": "2048",
            "CODEX_AGENTS_MD_PLUS_MAX_TOTAL_REFERENCE_BYTES": "8192",
            "CODEX_AGENTS_MD_PLUS_ALLOW_OUTSIDE_ROOT": "yes",
            "CODEX_AGENTS_MD_PLUS_FALLBACK_FILENAMES": "INSTRUCTIONS.md,CONTRIBUTING.md,, ",
            "CODEX_HOME": "/tmp/codex-home",
        }
    )
    assert cfg.max_depth == 9
    assert cfg.max_files == 1
    assert cfg.max_file_bytes == 2048
    assert cfg.max_total_reference_bytes == 8192
    assert cfg.allow_outside_root is True
    assert cfg.fallback_filenames == ("INSTRUCTIONS.md", "CONTRIBUTING.md")
    assert cfg.codex_home == Path("/tmp/codex-home")


def test_prefixed_codex_home_overrides_codex_home() -> None:
    cfg = Config.from_env(
        {
            "CODEX_HOME": "/tmp/default-codex-home",
            "CODEX_AGENTS_MD_PLUS_CODEX_HOME": "/tmp/plugin-codex-home",
        }
    )

    assert cfg.codex_home == Path("/tmp/plugin-codex-home")


def test_bad_int_falls_back_to_default() -> None:
    cfg = Config.from_env({"CODEX_AGENTS_MD_PLUS_MAX_DEPTH": "not-an-int"})
    assert cfg.max_depth == Config.max_depth


def test_negative_int_clamped_to_zero() -> None:
    cfg = Config.from_env({"CODEX_AGENTS_MD_PLUS_MAX_FILES": "-5"})
    assert cfg.max_files == 0


def test_native_project_filenames_default() -> None:
    assert Config().native_project_filenames == ("AGENTS.override.md", "AGENTS.md")


def test_native_project_filenames_with_fallbacks() -> None:
    cfg = Config(fallback_filenames=("INSTRUCTIONS.md",))
    assert cfg.native_project_filenames == ("AGENTS.override.md", "AGENTS.md", "INSTRUCTIONS.md")


def test_native_project_filenames_reserved_local_excluded() -> None:
    cfg = Config(fallback_filenames=("AGENTS.local.md",))
    assert cfg.native_project_filenames == ("AGENTS.override.md", "AGENTS.md")
