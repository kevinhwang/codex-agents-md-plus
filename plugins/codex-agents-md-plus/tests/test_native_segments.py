from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.native_segments import discover


def _make_config(tmp_path: Path, *, max_file_bytes: int = 32 * 1024) -> Config:
    return Config(codex_home=tmp_path / "codex-home", max_file_bytes=max_file_bytes)


def test_global_segment_precedes_project_chain(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    repo = tmp_path / "repo"
    child = repo / "pkg"
    codex_home.mkdir()
    (repo / ".git").mkdir(parents=True)
    child.mkdir()
    (codex_home / "AGENTS.md").write_text("global first line\nmore", encoding="utf-8")
    (repo / "AGENTS.md").write_text("root first line", encoding="utf-8")
    (child / "AGENTS.md").write_text("child first line", encoding="utf-8")

    segments = discover(child, _make_config(tmp_path))

    assert [segment.path for segment in segments] == [
        (codex_home / "AGENTS.md").resolve(),
        (repo / "AGENTS.md").resolve(),
        (child / "AGENTS.md").resolve(),
    ]
    assert [segment.first_line for segment in segments] == [
        "global first line",
        "root first line",
        "child first line",
    ]


def test_global_override_preferred_but_empty_override_falls_through(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    repo = tmp_path / "repo"
    codex_home.mkdir()
    repo.mkdir()
    (codex_home / "AGENTS.override.md").write_text(" \n", encoding="utf-8")
    (codex_home / "AGENTS.md").write_text("global default", encoding="utf-8")

    segments = discover(repo, _make_config(tmp_path))

    assert [segment.path for segment in segments] == [(codex_home / "AGENTS.md").resolve()]


def test_project_override_shadows_default_in_same_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "AGENTS.override.md").write_text("override", encoding="utf-8")
    (repo / "AGENTS.md").write_text("default", encoding="utf-8")

    segments = discover(repo, _make_config(tmp_path))

    assert [segment.path for segment in segments] == [(repo / "AGENTS.override.md").resolve()]
    assert [segment.first_line for segment in segments] == ["override"]


def test_empty_project_override_shadows_default_without_segment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "AGENTS.override.md").write_text(" \n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("default", encoding="utf-8")

    assert discover(repo, _make_config(tmp_path)) == ()


def test_project_chain_stops_at_aggregate_budget(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    child = repo / "pkg"
    (repo / ".git").mkdir(parents=True)
    child.mkdir()
    (repo / "AGENTS.md").write_text("root doc", encoding="utf-8")
    (child / "AGENTS.md").write_text("child doc", encoding="utf-8")

    segments = discover(child, _make_config(tmp_path, max_file_bytes=len("root doc")))

    assert [segment.path for segment in segments] == [(repo / "AGENTS.md").resolve()]


def test_without_project_root_only_cwd_is_considered(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = parent / "child"
    child.mkdir(parents=True)
    (parent / "AGENTS.md").write_text("parent", encoding="utf-8")
    (child / "AGENTS.md").write_text("child", encoding="utf-8")

    segments = discover(child, _make_config(tmp_path))

    assert [segment.path for segment in segments] == [(child / "AGENTS.md").resolve()]


def test_fallback_filename_used_after_standard_candidates(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "INSTRUCTIONS.md").write_text("fallback", encoding="utf-8")

    segments = discover(repo, Config(codex_home=tmp_path / "codex-home", fallback_filenames=("INSTRUCTIONS.md",)))

    assert [segment.path for segment in segments] == [(repo / "INSTRUCTIONS.md").resolve()]
