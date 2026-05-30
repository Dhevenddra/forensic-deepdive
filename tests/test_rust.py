"""Rust language support (v0.3 Item D / DEC-040).

Covers the pieces unique to Rust: ``impl``-block parent binding (methods attribute
to their type, not a free-function bucket), ``impl Trait for Type`` ⇒ IMPLEMENTS,
``use`` imports with crate-internal resolution, and method-call resolution
through the DEC-037 receiver rules (``self.m()``, ``Type::assoc()``).
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.imports import extract_imports
from forensic_deepdive.static.inheritance import extract_inheritance
from forensic_deepdive.static.method_calls import extract_method_calls
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.resolver import resolve_calls, resolve_method_calls
from forensic_deepdive.static.tags import extract_tags

FIXTURES = Path(__file__).parent / "fixtures"
RUST = FIXTURES / "rust_sample"


def _parse(name: str):
    return parse_file(RUST / name, rel_path=name)


def _defs(parsed) -> dict[str, str]:
    """qn_local -> category for every def Tag."""
    out = {}
    for t in extract_tags(parsed):
        if t.kind == "def":
            qn = f"{t.parent}.{t.name}" if t.parent else t.name
            out[qn] = t.category
    return out


# ---------------------------------------------------------------------------
# Definitions + impl/trait parent binding
# ---------------------------------------------------------------------------


def test_impl_methods_attribute_to_their_type() -> None:
    defs = _defs(_parse("greeter.rs"))
    # Free items keep their categories.
    assert defs["Greet"] == "interface"  # trait
    assert defs["Greeter"] == "struct"
    assert defs["Mood"] == "enum"
    # impl methods bind to Greeter (the acceptance criterion), NOT a top-level
    # `new` / `render` / `greet` free-function bucket.
    assert "Greeter.new" in defs
    assert "Greeter.render" in defs
    assert "Greeter.greet" in defs
    assert "new" not in defs and "render" not in defs


def test_impl_trait_for_type_is_implements() -> None:
    records = extract_inheritance(_parse("greeter.rs"))
    assert [(r.child_qn_local, r.kind, r.parent_name) for r in records] == [
        ("Greeter", "implements", "Greet")
    ]


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


def test_use_imports_distinguish_crate_from_std() -> None:
    imports = {i.module_path: i for i in extract_imports(_parse("greeter.rs"))}
    assert "crate::util::shout" in imports
    assert "std::fmt" in imports
    # The crate import names the imported leaf so the bare-name walk can use it.
    assert [n.name for n in imports["crate::util::shout"].imported_names] == ["shout"]


# ---------------------------------------------------------------------------
# Method-call resolution (Item C rules on Rust shapes)
# ---------------------------------------------------------------------------


def _two_file_inputs():
    g, u = _parse("greeter.rs"), _parse("util.rs")
    tags = extract_tags(g) + extract_tags(u)
    imports = extract_imports(g) + extract_imports(u)
    method_calls = extract_method_calls(g) + extract_method_calls(u)
    sources = {"greeter.rs": "rust", "util.rs": "rust"}
    return tags, imports, method_calls, sources


def test_self_call_resolves_to_impl_member() -> None:
    tags, imports, method_calls, sources = _two_file_inputs()
    edges = resolve_method_calls(method_calls, tags, imports, sources)
    # `self.render()` inside greet → Greeter.render, via self.
    self_edges = [e for e in edges if e.via == "self"]
    assert any(e.callee_qn == "greeter.rs::Greeter.render" for e in self_edges)
    assert all(e.confidence is Confidence.INFERRED for e in self_edges)


def test_associated_call_resolves_static() -> None:
    tags, imports, method_calls, sources = _two_file_inputs()
    edges = resolve_method_calls(method_calls, tags, imports, sources)
    # `Greeter::new(...)` → Greeter.new, via static.
    assert any(e.callee_qn == "greeter.rs::Greeter.new" and e.via == "static" for e in edges)


def test_bare_call_resolves_across_crate_use() -> None:
    tags, imports, method_calls, sources = _two_file_inputs()
    calls = resolve_calls(tags, imports, sources)
    # `shout(&self.name)` in render → util.rs::shout via the crate:: use import.
    assert any(c.callee_qn == "util.rs::shout" for c in calls)
