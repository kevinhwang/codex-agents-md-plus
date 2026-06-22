from __future__ import annotations

from pathlib import Path

from agents_md_plus.paths import chain_to, is_within_any


def test_chain_to_walks_ancestor_to_descendant(tmp_path: Path) -> None:
    leaf = tmp_path / "a" / "b" / "c"
    leaf.mkdir(parents=True)
    assert chain_to(tmp_path, leaf) == (
        tmp_path,
        tmp_path / "a",
        tmp_path / "a" / "b",
        tmp_path / "a" / "b" / "c",
    )


def test_chain_to_returns_leaf_when_not_under_root(tmp_path: Path) -> None:
    other = tmp_path.parent
    assert chain_to(tmp_path / "a", other) == (other.resolve(),)


def test_is_within_any(tmp_path: Path) -> None:
    inner = tmp_path / "inner"
    inner.mkdir()
    other = tmp_path.parent
    assert is_within_any(inner, (other, tmp_path))
    assert not is_within_any(tmp_path.parent.parent, (tmp_path,))
