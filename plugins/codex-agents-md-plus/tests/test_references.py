from __future__ import annotations

from pathlib import Path

from agents_md_plus.references import extract_tokens, looks_like_text_file, resolve


def test_extracts_plain_token() -> None:
    assert extract_tokens("see @docs/foo.md for more") == ["docs/foo.md"]


def test_ignores_fenced_code() -> None:
    text = "outer @real.md\n```\n@fenced.md\n```\n@after.md"
    assert extract_tokens(text) == ["real.md", "after.md"]


def test_ignores_indented_code() -> None:
    text = "outer @real.md\n    @indented.md"
    assert extract_tokens(text) == ["real.md"]


def test_ignores_inline_backticks() -> None:
    text = "use `@inline.md` here but @bare.md works"
    assert extract_tokens(text) == ["bare.md"]


def test_ignores_html_comments() -> None:
    text = "out @real.md <!-- @hidden.md --> after"
    assert extract_tokens(text) == ["real.md"]


def test_ignores_email_like() -> None:
    text = "ping name@example.com please"
    assert extract_tokens(text) == []


def test_resolve_relative(tmp_path: Path) -> None:
    src = tmp_path / "a" / "AGENTS.md"
    assert resolve("docs/foo.md", src.parent) == tmp_path / "a" / "docs" / "foo.md"


def test_resolve_absolute(tmp_path: Path) -> None:
    abs_path = tmp_path / "extra.md"
    assert resolve(str(abs_path), tmp_path / "elsewhere") == abs_path


def test_resolve_expanduser() -> None:
    resolved = resolve("~/notes.md", Path("/anchor"))
    assert resolved.is_absolute()
    assert str(resolved).endswith("notes.md")


def test_text_extension_whitelist() -> None:
    assert looks_like_text_file(Path("a.md"))
    assert looks_like_text_file(Path("Makefile"))  # no suffix → allowed
    assert not looks_like_text_file(Path("a.png"))
