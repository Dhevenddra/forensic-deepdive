"""Tests for the receiver-type method-call resolver (v0.3 Item C / DEC-037).

Each case builds the inputs the resolver consumes — Tags (defs), Imports,
MethodCalls — and asserts the resolved ``(callee_qn, confidence, via)`` for the
five receiver shapes: self/this, static class-qualified (same-file and
cross-file), module-alias, and the genuinely-unresolvable receiver (dropped).
"""

from __future__ import annotations

from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.imports import Import
from forensic_deepdive.static.method_calls import MethodCall
from forensic_deepdive.static.resolver import resolve_method_calls
from forensic_deepdive.static.tags import Tag


def _def(rel_path: str, name: str, parent: str = "", language: str = "python") -> Tag:
    return Tag(
        rel_path=rel_path,
        name=name,
        kind="def",
        category="method" if parent else "function",
        line=1,
        language=language,
        parent=parent,
    )


def _mc(receiver: str, method: str, scope: str, rel_path: str = "a.py", language: str = "python"):
    return MethodCall(
        rel_path=rel_path,
        receiver=receiver,
        method=method,
        enclosing_scope=scope,
        line=5,
        language=language,
    )


def _resolve(method_calls, tags, imports=()):
    sources = {t.rel_path: t.language for t in tags}
    sources.update({m.rel_path: m.language for m in method_calls})
    return resolve_method_calls(method_calls, tags, imports, sources)


def test_self_resolves_to_enclosing_class_member() -> None:
    tags = [
        _def("a.py", "Greeter", ""),
        _def("a.py", "render", "Greeter"),
        _def("a.py", "greet", "Greeter"),
    ]
    [edge] = _resolve([_mc("self", "render", "Greeter.greet")], tags)
    assert edge.callee_qn == "a.py::Greeter.render"
    assert edge.confidence is Confidence.INFERRED
    assert edge.via == "self"
    assert edge.caller_qn == "a.py::Greeter.greet"


def test_this_resolves_like_self() -> None:
    tags = [_def("a.ts", "Widget", "", "typescript"), _def("a.ts", "draw", "Widget", "typescript")]
    [edge] = _resolve([_mc("this", "draw", "Widget.render", "a.ts", "typescript")], tags)
    assert edge.callee_qn == "a.ts::Widget.draw"
    assert edge.via == "this"


def test_self_with_no_matching_member_is_dropped() -> None:
    tags = [_def("a.py", "Greeter", ""), _def("a.py", "greet", "Greeter")]
    assert _resolve([_mc("self", "missing", "Greeter.greet")], tags) == []


def test_static_same_file() -> None:
    tags = [_def("a.py", "Logger", ""), _def("a.py", "warn", "Logger")]
    [edge] = _resolve([_mc("Logger", "warn", "top")], tags)
    assert edge.callee_qn == "a.py::Logger.warn"
    assert edge.confidence is Confidence.INFERRED
    assert edge.via == "static"


def test_static_cross_file_single_is_inferred() -> None:
    tags = [
        _def("a.py", "caller", ""),
        _def("b.py", "Logger", ""),
        _def("b.py", "warn", "Logger"),
    ]
    [edge] = _resolve([_mc("Logger", "warn", "caller")], tags)
    assert edge.callee_qn == "b.py::Logger.warn"
    assert edge.confidence is Confidence.INFERRED


def test_static_cross_file_multiple_is_ambiguous() -> None:
    tags = [
        _def("b.py", "Logger", ""),
        _def("b.py", "warn", "Logger"),
        _def("c.py", "Logger", ""),
        _def("c.py", "warn", "Logger"),
    ]
    edges = _resolve([_mc("Logger", "warn", "top")], tags)
    assert {e.callee_qn for e in edges} == {"b.py::Logger.warn", "c.py::Logger.warn"}
    assert all(e.confidence is Confidence.AMBIGUOUS for e in edges)


def test_module_alias_resolves_to_imported_top_level() -> None:
    tags = [_def("a.py", "caller", ""), _def("util/helpers.py", "build", "")]
    imp = Import(
        rel_path="a.py",
        module_path="util.helpers",
        language="python",
        line=1,
        module_alias="helpers",
    )
    [edge] = _resolve([_mc("helpers", "build", "caller")], tags, [imp])
    assert edge.callee_qn == "util/helpers.py::build"
    assert edge.via == "module"
    assert edge.confidence is Confidence.INFERRED


def test_plain_import_last_segment_matches_receiver() -> None:
    tags = [_def("a.py", "caller", ""), _def("util/helpers.py", "build", "")]
    imp = Import(rel_path="a.py", module_path="util.helpers", language="python", line=1)
    # `import util.helpers` then `helpers.build()` — receiver is last segment.
    [edge] = _resolve([_mc("helpers", "build", "caller")], tags, [imp])
    assert edge.callee_qn == "util/helpers.py::build"
    assert edge.via == "module"


def test_unknown_receiver_is_dropped_not_ambiguous() -> None:
    # `x.foo()` where x's type is unknown and foo is defined somewhere — we drop
    # rather than flood AMBIGUOUS (DEC-037 anti-noise default).
    tags = [_def("a.py", "Other", ""), _def("a.py", "foo", "Other")]
    assert _resolve([_mc("x", "foo", "top")], tags) == []


def test_complex_receiver_is_dropped() -> None:
    tags = [_def("a.py", "foo", "")]
    assert _resolve([_mc("a.b", "foo", "top")], tags) == []
