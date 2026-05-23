"""Tests for the Tree-sitter parsing layer."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.parse import detect_language, parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_language() -> None:
    assert detect_language(Path("a.py")) == "python"
    assert detect_language(Path("a.pyi")) == "python"
    assert detect_language(Path("a.dart")) == "dart"
    assert detect_language(Path("a.c")) == "c"
    assert detect_language(Path("a.h")) == "c"
    assert detect_language(Path("a.swift")) == "swift"
    # DEC-020
    assert detect_language(Path("a.ts")) == "typescript"
    assert detect_language(Path("a.tsx")) == "tsx"
    assert detect_language(Path("a.js")) == "javascript"
    assert detect_language(Path("a.mjs")) == "javascript"
    assert detect_language(Path("a.cjs")) == "javascript"
    assert detect_language(Path("a.jsx")) == "javascript"
    assert detect_language(Path("A.java")) == "java"
    assert detect_language(Path("a.go")) == "go"
    assert detect_language(Path("README.md")) is None


def test_parse_python_fixture() -> None:
    parsed = parse_file(FIXTURES / "python_sample" / "greeter.py")
    assert parsed is not None
    assert parsed.language == "python"
    assert parsed.tree.root_node.type == "module"
    assert not parsed.tree.root_node.has_error


def test_parse_all_languages() -> None:
    """Regression: every grammar must round-trip through the genuine
    ``tree_sitter`` Parser (not the language-pack's incompatible core)."""
    cases = {
        "python_sample/greeter.py": "python",
        "dart_sample/greeter.dart": "dart",
        "c_sample/mathutil.c": "c",
        "swift_sample/Greeter.swift": "swift",
        # DEC-020
        "typescript_sample/greeter.ts": "typescript",
        "javascript_sample/greeter.js": "javascript",
        "java_sample/Greeter.java": "java",
        "go_sample/greeter.go": "go",
    }
    for rel, language in cases.items():
        parsed = parse_file(FIXTURES / rel)
        assert parsed is not None, rel
        assert parsed.language == language
        assert parsed.tree.root_node.child_count > 0
        assert not parsed.tree.root_node.has_error, rel


def test_parse_unsupported_extension_returns_none() -> None:
    assert parse_file(FIXTURES / "python_sample" / "greeter.py.txt") is None


def test_rel_path_defaults_to_filename() -> None:
    parsed = parse_file(FIXTURES / "python_sample" / "app.py")
    assert parsed is not None
    assert parsed.rel_path == "app.py"
    parsed = parse_file(FIXTURES / "python_sample" / "app.py", rel_path="pkg/app.py")
    assert parsed is not None
    assert parsed.rel_path == "pkg/app.py"
