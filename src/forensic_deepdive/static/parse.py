"""Tree-sitter parsing layer for forensic-deepdive.

Turns source files into tree-sitter parse trees and maps file extensions to
grammar names. Grammars come from ``tree-sitter-language-pack`` (300+ bundled
grammars); the parser and query runtime come from the ``tree-sitter`` package.

Interop note: ``tree_sitter_language_pack.get_parser()`` returns a parser from
the pack's *vendored* core whose ``Node`` objects are not type-compatible with
``tree_sitter.QueryCursor`` (it raises ``TypeError: ... not tree_sitter.Node``).
We therefore take only the raw ``Language`` from the pack via ``get_language()``
and build the ``Parser`` ourselves, so every object downstream is a genuine
``tree_sitter`` object. ``tests/test_parse.py`` guards this.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from tree_sitter import Parser, Tree
from tree_sitter_language_pack import get_language

# Extension -> tree-sitter grammar name. Only languages that also have a
# tags.scm entry in ``tags.py`` contribute symbols to the graph; others still
# parse cleanly but yield no tags. Keep this in sync with ``tags.TAGS_SCM``.
LANG_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".dart": "dart",
    ".c": "c",
    ".h": "c",
    ".swift": "swift",
    # DEC-020: v0.2 expands to 8 languages.
    ".ts": "typescript",
    ".tsx": "tsx",  # tsx grammar is a JSX-aware superset
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",  # the JS grammar accepts JSX
    ".java": "java",
    ".go": "go",
}


@dataclass(frozen=True, slots=True)
class ParsedFile:
    """A successfully parsed source file and everything downstream needs."""

    path: Path
    rel_path: str
    language: str
    source: bytes
    tree: Tree


def detect_language(path: Path) -> str | None:
    """Return the tree-sitter grammar name for *path*, or None if unsupported."""
    return LANG_BY_EXT.get(path.suffix.lower())


@cache
def _parser_for(language: str) -> Parser:
    """Return a cached ``tree_sitter.Parser`` for *language*."""
    return Parser(get_language(language))


def parse_source(source: bytes, language: str) -> Tree:
    """Parse raw *source* bytes with the grammar for *language*."""
    return _parser_for(language).parse(source)


def parse_file(path: Path, rel_path: str | None = None) -> ParsedFile | None:
    """Parse *path*.

    Returns ``None`` for unsupported extensions or unreadable files rather than
    raising — the inventory stage feeds this every file in the repo.

    *rel_path* is the repo-relative identifier used as the graph node name; it
    defaults to the file name when not supplied.
    """
    language = detect_language(path)
    if language is None:
        return None
    try:
        source = path.read_bytes()
    except OSError:
        return None
    tree = parse_source(source, language)
    return ParsedFile(
        path=path,
        rel_path=rel_path if rel_path is not None else path.name,
        language=language,
        source=source,
        tree=tree,
    )
