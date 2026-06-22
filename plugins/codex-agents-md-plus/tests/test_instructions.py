from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.instructions import resolve_for_directory
from agents_md_plus.models import InstructionFamily


def test_resolves_primary_when_present(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    primary.mkdir()
    (primary / "AGENTS.md").write_text("primary content")
    files = resolve_for_directory(primary, None, Config())
    assert len(files) == 1
    assert files[0].path == (primary / "AGENTS.md").resolve()
    assert files[0].family is InstructionFamily.PROJECT


def test_override_takes_precedence_over_default(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    primary.mkdir()
    (primary / "AGENTS.override.md").write_text("override")
    (primary / "AGENTS.md").write_text("default")
    files = resolve_for_directory(primary, None, Config())
    assert files[0].path.name == "AGENTS.override.md"


def test_falls_back_to_parallel_when_primary_missing(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    parallel = tmp_path / "parallel"
    primary.mkdir()
    parallel.mkdir()
    (parallel / "AGENTS.md").write_text("from parallel")
    files = resolve_for_directory(primary, parallel, Config())
    assert len(files) == 1
    assert files[0].path == (parallel / "AGENTS.md").resolve()
    assert files[0].family is InstructionFamily.PROJECT


def test_local_overlay_independent_of_project_file(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    parallel = tmp_path / "parallel"
    primary.mkdir()
    parallel.mkdir()
    (primary / "AGENTS.local.md").write_text("local in primary")
    (parallel / "AGENTS.md").write_text("project in parallel")
    files = resolve_for_directory(primary, parallel, Config())
    by_family = {file.family: file for file in files}
    assert by_family[InstructionFamily.OVERLAY].path == (primary / "AGENTS.local.md").resolve()
    assert by_family[InstructionFamily.PROJECT].path == (parallel / "AGENTS.md").resolve()


def test_local_falls_back_to_parallel(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    parallel = tmp_path / "parallel"
    primary.mkdir()
    parallel.mkdir()
    (parallel / "AGENTS.local.md").write_text("local from parallel")
    files = resolve_for_directory(primary, parallel, Config())
    overlays = [f for f in files if f.family is InstructionFamily.OVERLAY]
    assert len(overlays) == 1
    assert overlays[0].path == (parallel / "AGENTS.local.md").resolve()


def test_skips_empty_files(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    primary.mkdir()
    (primary / "AGENTS.md").write_text("   \n\n")
    files = resolve_for_directory(primary, None, Config())
    assert files == ()
