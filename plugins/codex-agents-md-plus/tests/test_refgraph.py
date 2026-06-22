from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.models import InstructionFile, InstructionRole
from agents_md_plus.refgraph import expand


def _seed(path: Path, text: str) -> InstructionFile:
    return InstructionFile(path=path.resolve(), text=text, truncated=False, role=InstructionRole.OVERLAY)


def test_simple_reference_resolved(tmp_path: Path) -> None:
    target = tmp_path / "ref.md"
    target.write_text("hello from ref")
    seed_path = tmp_path / "AGENTS.local.md"
    seed_path.write_text("@ref.md")
    result = expand((_seed(seed_path, "@ref.md"),), (tmp_path,), Config())
    assert [r.path for r in result.references] == [target.resolve()]
    assert result.skipped == ()


def test_cycles_loaded_once(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("@b.md")
    (tmp_path / "b.md").write_text("@a.md")
    seed = _seed(tmp_path / "AGENTS.local.md", "@a.md\n@b.md")
    result = expand((seed,), (tmp_path,), Config())
    paths = [r.path for r in result.references]
    assert sorted(paths) == sorted([(tmp_path / "a.md").resolve(), (tmp_path / "b.md").resolve()])


def test_outside_guard_skipped(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    outside = tmp_path / "outside.md"
    inside.mkdir()
    outside.write_text("outside")
    seed = _seed(inside / "AGENTS.local.md", "@../outside.md")
    result = expand((seed,), (inside,), Config())
    assert result.references == ()
    assert len(result.skipped) == 1
    assert "outside" in result.skipped[0].reason


def test_outside_guard_allowed_when_configured(tmp_path: Path) -> None:
    inside = tmp_path / "inside"
    outside = tmp_path / "outside.md"
    inside.mkdir()
    outside.write_text("outside content")
    seed = _seed(inside / "AGENTS.local.md", "@../outside.md")
    result = expand((seed,), (inside,), Config(allow_outside_root=True))
    assert [r.path for r in result.references] == [outside.resolve()]


def test_max_files_limit(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("a")
    (tmp_path / "b.md").write_text("b")
    seed = _seed(tmp_path / "AGENTS.local.md", "@a.md\n@b.md")
    result = expand((seed,), (tmp_path,), Config(max_files=1))
    assert len(result.references) == 1
    assert any("max referenced files" in s.reason for s in result.skipped)


def test_max_depth_limit(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("@b.md")
    (tmp_path / "b.md").write_text("@c.md")
    (tmp_path / "c.md").write_text("done")
    seed = _seed(tmp_path / "AGENTS.local.md", "@a.md")
    result = expand((seed,), (tmp_path,), Config(max_depth=2))
    assert [r.path.name for r in result.references] == ["a.md", "b.md"]
    assert any("max depth" in s.reason for s in result.skipped)


def test_skips_non_text_files(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_text("not text")
    seed = _seed(tmp_path / "AGENTS.local.md", "@logo.png")
    result = expand((seed,), (tmp_path,), Config())
    assert result.references == ()
    assert any("text file" in s.reason for s in result.skipped)


def test_seed_self_reference_silently_skipped(tmp_path: Path) -> None:
    seed_path = tmp_path / "AGENTS.local.md"
    seed_path.write_text("@AGENTS.local.md")
    result = expand((_seed(seed_path, "@AGENTS.local.md"),), (tmp_path,), Config())
    assert result.references == ()
    assert result.skipped == ()
