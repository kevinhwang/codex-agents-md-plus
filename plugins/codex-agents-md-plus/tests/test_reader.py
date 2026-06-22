from __future__ import annotations

from pathlib import Path

from agents_md_plus.reader import read_text_capped


def test_full_read(tmp_path: Path) -> None:
    p = tmp_path / "f.txt"
    p.write_text("hello")
    text, truncated = read_text_capped(p, 100)
    assert text == "hello"
    assert truncated is False


def test_truncated(tmp_path: Path) -> None:
    p = tmp_path / "f.txt"
    p.write_text("abcdefghij")
    text, truncated = read_text_capped(p, 4)
    assert text == "abcd"
    assert truncated is True


def test_decodes_invalid_utf8(tmp_path: Path) -> None:
    p = tmp_path / "f.txt"
    p.write_bytes(b"hello\xff\xfeworld")
    text, _ = read_text_capped(p, 100)
    assert "hello" in text and "world" in text
