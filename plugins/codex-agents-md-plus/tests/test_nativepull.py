from __future__ import annotations

from pathlib import Path

from agents_md_plus.config import Config
from agents_md_plus.nativepull import is_natively_loaded, native_chain


def test_native_chain_no_root_returns_just_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "x"
    cwd.mkdir()
    assert native_chain(None, cwd) == (cwd,)


def test_native_chain_root_to_cwd(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    cwd = root / "a" / "b"
    cwd.mkdir(parents=True)
    chain = native_chain(root, cwd)
    assert chain == (root, root / "a", root / "a" / "b")


def test_natively_loaded_default(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    cwd = root / "x"
    cwd.mkdir(parents=True)
    (cwd / "AGENTS.md").write_text("doc")
    assert is_natively_loaded(cwd / "AGENTS.md", cwd, root, Config())


def test_overridden_default_not_loaded(tmp_path: Path) -> None:
    cwd = tmp_path / "repo" / "x"
    cwd.mkdir(parents=True)
    (cwd / "AGENTS.override.md").write_text("ov")
    (cwd / "AGENTS.md").write_text("doc")
    assert is_natively_loaded(cwd / "AGENTS.override.md", cwd, tmp_path / "repo", Config())
    # The plain AGENTS.md is shadowed by override at the same dir → NOT native.
    assert not is_natively_loaded(cwd / "AGENTS.md", cwd, tmp_path / "repo", Config())


def test_local_overlay_never_native(tmp_path: Path) -> None:
    cwd = tmp_path / "repo"
    cwd.mkdir()
    (cwd / "AGENTS.local.md").write_text("local")
    assert not is_natively_loaded(cwd / "AGENTS.local.md", cwd, cwd, Config())


def test_outside_native_chain_not_loaded(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    cwd = root / "inside"
    cwd.mkdir(parents=True)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "AGENTS.md").write_text("doc")
    assert not is_natively_loaded(outside / "AGENTS.md", cwd, root, Config())


def test_fallback_filename_counted_as_native(tmp_path: Path) -> None:
    cwd = tmp_path / "repo"
    cwd.mkdir()
    (cwd / "INSTRUCTIONS.md").write_text("doc")
    cfg = Config(fallback_filenames=("INSTRUCTIONS.md",))
    assert is_natively_loaded(cwd / "INSTRUCTIONS.md", cwd, cwd, cfg)
