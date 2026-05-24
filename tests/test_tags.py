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


def test_typescript_tags() -> None:
    """DEC-020. Definer + caller produce the expected def/ref shape; dotted
    method calls do NOT yield references (DEC-012 discipline)."""
    defs = _names(_tags("typescript_sample/greeter.ts"), "def")
    assert {"Greeter", "Named", "formatMessage", "greet"} <= defs
    app_refs = _names(_tags("typescript_sample/app.ts"), "ref")
    # Bare call + constructor reference, no dotted-method noise.
    assert "Greeter" in app_refs  # new Greeter(...)
    assert "formatMessage" in app_refs  # bare call
    assert "greet" not in app_refs  # g.greet() — dotted, dropped
    assert "log" not in app_refs  # console.log — dotted, dropped


def test_javascript_tags() -> None:
    """DEC-020. Same shape as TS without the type-system declarations."""
    defs = _names(_tags("javascript_sample/greeter.js"), "def")
    assert {"Greeter", "formatMessage", "greet"} <= defs
    app_refs = _names(_tags("javascript_sample/app.js"), "ref")
    assert "Greeter" in app_refs
    assert "formatMessage" in app_refs
    assert "greet" not in app_refs
    assert "log" not in app_refs


def test_java_tags() -> None:
    """DEC-020. Class / interface / enum / method definitions; bare-call
    references only (`Receiver.method(...)` is excluded via the
    object-field check on method_invocation)."""
    greeter = _tags("java_sample/Greeter.java")
    defs = _names(greeter, "def")
    assert {"Greeter", "Named", "Severity", "greet", "formatMessage"} <= defs
    greeter_refs = _names(greeter, "ref")
    # `formatMessage(name)` is a bare call inside Greeter.greet().
    assert "formatMessage" in greeter_refs
    # `name` field reference appears as a bare identifier — that's fine; the
    # discipline is that DOTTED calls don't leak.
    main_refs = _names(_tags("java_sample/Main.java"), "ref")
    assert "Greeter" in main_refs  # new Greeter(...) → object_creation_expression
    assert "greet" not in main_refs  # g.greet() — dotted, dropped
    assert "println" not in main_refs  # System.out.println — dotted, dropped


def test_go_tags() -> None:
    """DEC-020. Method receivers don't escape into the reference set;
    `pkg.Fn(...)` selector calls are dropped."""
    greeter = _tags("go_sample/greeter.go")
    defs = _names(greeter, "def")
    # struct / interface (via type_spec), method (via field_identifier),
    # function (via identifier).
    assert {"Greeter", "Named", "Greet", "Name", "formatMessage"} <= defs
    greeter_refs = _names(greeter, "ref")
    # `fmt.Sprintf(...)` — selector, dropped.
    assert "Sprintf" not in greeter_refs
    # `formatMessage(g.name)` — bare call inside Greet method.
    assert "formatMessage" in greeter_refs
    main_refs = _names(_tags("go_sample/main.go"), "ref")
    assert "formatMessage" in main_refs  # bare call
    assert "Greet" not in main_refs  # g.Greet() — selector, dropped


def test_dart_dotted_method_call_is_not_a_reference() -> None:
    """DEC-012 follow-up (Omi #1/#2). `obj.greet()` must not produce a
    `greet` reference — that would link the file to every other Dart file
    defining a method called `greet`. Bare calls (`formatMessage(...)`)
    still produce references."""
    refs = _names(_tags("dart_sample/app.dart"), "ref")
    # The bare-call reference is preserved.
    assert "formatMessage" in refs
    # `greeter.greet()` and `print(...)` would have been references under
    # the v0.1 catch-all; they must not be now.
    assert "greet" not in refs


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


def test_tags_carry_language() -> None:
    """Every tag records its source file's language (DEC-012)."""
    tags = _tags("python_sample/greeter.py")
    assert tags
    assert all(tag.language == "python" for tag in tags)
    dart_tags = _tags("dart_sample/greeter.dart")
    assert all(tag.language == "dart" for tag in dart_tags)


# ---------------------------------------------------------------------------
# DEC-023 — parent chain on definition Tags
# ---------------------------------------------------------------------------


def _defs(rel: str) -> dict[tuple[str, str], str]:
    """Return ``{(name, category): parent}`` for every def Tag in *rel*."""
    return {(t.name, t.category): t.parent for t in _tags(rel) if t.kind == "def"}


def test_parent_top_level_is_empty_string_python() -> None:
    defs = _defs("python_sample/greeter.py")
    assert defs[("Greeter", "class")] == ""
    assert defs[("format_message", "function")] == ""


def test_parent_class_method_python() -> None:
    defs = _defs("python_sample/greeter.py")
    assert defs[("greet", "function")] == "Greeter"
    assert defs[("__init__", "function")] == "Greeter"


def test_parent_class_method_typescript() -> None:
    defs = _defs("typescript_sample/greeter.ts")
    assert defs[("greet", "method")] == "Greeter"
    assert defs[("formatMessage", "function")] == ""


def test_parent_java_methods_across_classes() -> None:
    """Two declarations named ``name`` — one in interface ``Named``, one
    in class ``Greeter`` — must each report their respective parent."""
    defs = _defs("java_sample/Greeter.java")
    # Tag dict keys (name, category) collide for `name` (one is interface
    # method, one is class method, same category "method"). Re-derive
    # without collapsing.
    raw_defs = [t for t in _tags("java_sample/Greeter.java") if t.kind == "def"]
    name_parents = {t.parent for t in raw_defs if t.name == "name"}
    assert name_parents == {"Named", "Greeter"}
    assert defs[("greet", "method")] == "Greeter"


def test_parent_go_receiver_methods() -> None:
    """Go's receiver-bound methods (``func (g *Greeter) Greet()``) are
    NOT lexically inside the type — the parent comes from the receiver
    type. DEC-023's Go branch handles this."""
    defs = _defs("go_sample/greeter.go")
    assert defs[("Greet", "method")] == "Greeter"
    assert defs[("Name", "method")] == "Greeter"
    assert defs[("formatMessage", "function")] == ""
    assert defs[("Greeter", "type")] == ""


def test_parent_dart_class_method() -> None:
    defs = _defs("dart_sample/greeter.dart")
    assert defs[("greet", "function")] == "Greeter"
    assert defs[("formatMessage", "function")] == ""


def test_parent_swift_class_method() -> None:
    defs = _defs("swift_sample/Greeter.swift")
    assert defs[("greet", "function")] == "Greeter"
    assert defs[("formatMessage", "function")] == ""


def test_parent_javascript_class_method() -> None:
    defs = _defs("javascript_sample/greeter.js")
    assert defs[("greet", "method")] == "Greeter"
    assert defs[("formatMessage", "function")] == ""


def test_parent_references_never_carry_parent() -> None:
    """Reference Tags don't carry parent today — their *resolution
    target's* parent is computed by the CALLS resolver."""
    for rel in (
        "python_sample/app.py",
        "java_sample/Main.java",
        "go_sample/main.go",
    ):
        for tag in _tags(rel):
            if tag.kind == "ref":
                assert tag.parent == "", (rel, tag)


def test_parent_class_never_lists_itself_as_parent() -> None:
    """Regression guard for the early-cycle bug: a class's own identifier
    walking up the AST hits its own class_definition and would have
    returned its own name as parent. DEC-023 skips the self-ancestor."""
    for rel in (
        "python_sample/greeter.py",
        "dart_sample/greeter.dart",
        "swift_sample/Greeter.swift",
        "typescript_sample/greeter.ts",
        "javascript_sample/greeter.js",
        "java_sample/Greeter.java",
    ):
        for tag in _tags(rel):
            if tag.kind == "def" and tag.category in {
                "class",
                "interface",
                "enum",
                "type",
            }:
                # Top-level types must not name themselves.
                assert tag.parent != tag.name, (rel, tag)
