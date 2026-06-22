"""Markdown-aware `@`-reference tokenizer + path resolver.

A reference looks like ``@docs/file.md`` or ``@~/notes.md``. The tokenizer
respects fenced code (``` ``` / ``` ~~~ ```), indented code blocks, inline
backtick spans, and HTML comments. Email-like strings, doubled ``@@``
mentions, and Bazel-style labels are skipped.

Path resolution: absolute paths are used as-is, `~` is expanded, relative
paths resolve against the directory of the source file.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

_REFERENCE_RE = re.compile(r"(?:^|\s)@(?P<token>[^\s`<>'\"]+)")
_TRAILING_PUNCT = ".,;:!?)]}"
_FIRST_CHAR_SAFE = frozenset("./\\~_-")


_TEXT_FILE_EXTENSIONS = frozenset(
    {
        ".adoc",
        ".asciidoc",
        ".astro",
        ".bash",
        ".bat",
        ".c",
        ".cc",
        ".cfg",
        ".cjs",
        ".clj",
        ".cljs",
        ".cljc",
        ".cmake",
        ".cmd",
        ".conf",
        ".config",
        ".cpp",
        ".cs",
        ".css",
        ".csv",
        ".cts",
        ".cxx",
        ".dart",
        ".diff",
        ".edn",
        ".ejs",
        ".elm",
        ".env",
        ".erb",
        ".erl",
        ".ex",
        ".exs",
        ".f",
        ".f90",
        ".f95",
        ".fish",
        ".for",
        ".go",
        ".gql",
        ".gradle",
        ".graphql",
        ".h",
        ".hbs",
        ".hpp",
        ".hrl",
        ".hs",
        ".htm",
        ".html",
        ".hxx",
        ".ini",
        ".jade",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".kts",
        ".latex",
        ".less",
        ".lhs",
        ".lock",
        ".log",
        ".lua",
        ".make",
        ".makefile",
        ".md",
        ".mjs",
        ".ml",
        ".mli",
        ".mts",
        ".org",
        ".patch",
        ".php",
        ".pl",
        ".pm",
        ".properties",
        ".proto",
        ".ps1",
        ".pug",
        ".py",
        ".pyi",
        ".pyw",
        ".r",
        ".rake",
        ".rb",
        ".rs",
        ".rst",
        ".sass",
        ".sbt",
        ".scala",
        ".scss",
        ".sh",
        ".sql",
        ".svelte",
        ".swift",
        ".tex",
        ".text",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".vue",
        ".xml",
        ".yaml",
        ".yml",
        ".zsh",
    }
)


def extract_tokens(text: str) -> list[str]:
    """Find all bare `@`-references in `text`, skipping code regions."""
    tokens: list[str] = []
    state = _TokenizerState()
    for line in text.splitlines():
        for segment in state.segments_in_line(line):
            for match in _REFERENCE_RE.finditer(_strip_inline_code(segment)):
                token = match["token"].rstrip(_TRAILING_PUNCT)
                if _is_reference_token(token):
                    tokens.append(token)
    return tokens


def resolve(token: str, base: Path) -> Path:
    """Resolve a bare reference token against `base`."""
    path = Path(token).expanduser()
    return path if path.is_absolute() else base / path


def looks_like_text_file(path: Path) -> bool:
    """Whitelist of file extensions we consider readable as text."""
    return path.suffix == "" or path.suffix.lower() in _TEXT_FILE_EXTENSIONS


class _TokenizerState:
    """Tracks block-level Markdown state across lines.

    Code fences and HTML comments can span multiple lines, so we keep enough
    state between line-scans to know whether we're still inside one.
    """

    def __init__(self) -> None:
        self._fence: str | None = None
        self._in_html_comment = False

    def segments_in_line(self, line: str) -> Iterator[str]:
        """Yield prose segments of `line` (zero or more) after applying block-level filtering."""
        stripped = line.lstrip()
        if self._fence is not None:
            if stripped.startswith(self._fence):
                self._fence = None
            return
        if stripped.startswith(("```", "~~~")):
            self._fence = stripped[:3]
            return
        if line.startswith("    ") or line.startswith("\t"):
            return
        yield from self._segments_outside_html_comments(line)

    def _segments_outside_html_comments(self, line: str) -> Iterator[str]:
        start = 0
        while start < len(line):
            if self._in_html_comment:
                end = line.find("-->", start)
                if end == -1:
                    return
                self._in_html_comment = False
                start = end + len("-->")
                continue

            comment_start = line.find("<!--", start)
            if comment_start == -1:
                yield line[start:]
                return
            if start < comment_start:
                yield line[start:comment_start]
            self._in_html_comment = True
            start = comment_start + len("<!--")


def _is_reference_token(token: str) -> bool:
    if not token or token.startswith(("@", "#")):
        return False
    return token[0].isalnum() or token[0] in _FIRST_CHAR_SAFE


def _strip_inline_code(line: str) -> str:
    """Remove backtick-fenced spans (`code` / ``with`tick``) from `line`."""
    output: list[str] = []
    index = 0
    open_tick_count = 0
    while index < len(line):
        if line[index] == "`":
            end = index + 1
            while end < len(line) and line[end] == "`":
                end += 1
            tick_count = end - index
            if open_tick_count == 0:
                open_tick_count = tick_count
            elif tick_count >= open_tick_count:
                open_tick_count = 0
            index = end
            continue
        if open_tick_count == 0:
            output.append(line[index])
        index += 1
    return "".join(output)
