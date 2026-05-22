"""Tests for Tree-sitter tag extraction across all v0.1 languages."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import TAGS_SCM, Tag, extract_tags

FIXTURES = Path(__file__).parent / "fixtures"


def _tags(rel: str) -> list[Tag]:
    parsed = parse_file(FIXTURES / rel, rel_path=Path(rel).name)
    assert parsed is not None, rel
    return extract_tags(parsed)


def _names(tags: list[Tag], kind: str) -> set[str]:
    return {t.name for t in tags if t.kind == kind}


def test_all_queries_compile() -> None:
    """Every tags.scm string must compile against its grammar."""
    from forensic_deepdive.static.tags import _query_for

    for language in TAGS_SCM:
        assert _query_for(language) is not None, language


def test_python_tags() -> None:
    tags = _tags("python_sample/greeter.py")
    assert {"Greeter", "format_message", "greet"} <= _names(tags, "def")
    assert "format_message" in _names(tags, "ref")


def test_c_tags() -> None:
    assert {"add", "multiply"} <= _names(_tags("c_sample/mathutil.c"), "def")
    assert {"Vector", "Sign"} <= _names(_tags("c_sample/mathutil.h"), "def")
    assert {"add", "multiply"} <= _names(_tags("c_sample/main.c"), "ref")


def test_dart_tags() -> None:
    tags = _tags("dart_sample/greeter.dart")
    assert {"Greeter", "formatMessage"} <= _names(tags, "def")
    assert "Greeter" in _names(_tags("dart_sample/app.dart"), "ref")


def test_swift_tags() -> None:
    tags = _tags("swift_sample/Greeter.swift")
    assert {"Greeter", "Named", "formatMessage"} <= _names(tags, "def")
    assert "formatMessage" in _names(_tags("swift_sample/main.swift"), "ref")


def test_definition_name_is_not_self_referenced() -> None:
    """A definition's own name node must not also appear as a reference."""
    for tag in _tags("dart_sample/greeter.dart"):
        if tag.kind == "ref":
            # the def of `formatMessage`/`Greeter` lives on a different line
            assert not (tag.name == "Greeter" and tag.line == 1)


def test_tags_sorted_by_line() -> None:
    tags = _tags("python_sample/greeter.py")
    assert tags == sorted(tags, key=lambda t: (t.line, t.kind, t.name))
