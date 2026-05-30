"""Dotted method-call extraction (v0.3 Item C, DEC-037).

DEC-025's resolver is bare-name only: ``tags.scm`` routes dotted callees
(``obj.foo()``, ``Cls.foo()``) through ``@_drop_method`` so they never become
references. That's why Omi shows 449-caller ``AMBIGUOUS`` rows and method-heavy
code resolves poorly. Item C recovers those calls *without* the false edges by
capturing the **receiver expression** alongside the method name, so a
:class:`ReceiverTypeResolver` (see ``resolver.py``) can infer the receiver's
type and resolve the method against that type's members.

This module only *extracts* — it records ``(receiver, method, enclosing_scope)``
triples and leaves resolution to the resolver. A code-walk (not a Tree-sitter
query) mirrors ``imports.py`` / ``inheritance.py``: dotted-call shapes are
simple field lookups and a walk is easier to read and keep precise than
correlating two captures per match.

Language scope (v0.3): **Python, TypeScript, TSX, JavaScript, Java** (DEC-037)
plus **Rust** (DEC-040) — the v0.4-wedge-relevant stack (React TS + Spring Java)
plus our own Python dogfood and the new Rust support. Dart / Swift / Go / C
dotted calls stay dropped as today (no regression, no new edges) — a documented
follow-on. The bare-name path (DEC-025) is unchanged for all languages.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from forensic_deepdive.static.parse import ParsedFile
from forensic_deepdive.static.tags import _enclosing_scope_qn, _row


@dataclass(frozen=True, slots=True)
class MethodCall:
    """One ``receiver.method(...)`` call site.

    ``receiver`` is the raw text of the receiver expression — ``"self"``,
    ``"this"``, a variable ``"x"``, a type ``"Foo"``, an import alias ``"mod"``,
    or a complex expression (``"a.b"``, ``"foo()"``). The resolver acts only on
    simple single-identifier receivers and marks the rest AMBIGUOUS, keeping the
    inference intra-scope and honest (DEC-037). ``enclosing_scope`` is the
    caller's dotted qn_local (same attribution as DEC-025 refs)."""

    rel_path: str
    receiver: str
    method: str
    enclosing_scope: str
    line: int  # 0-based start row of the method name
    language: str


def _make(parsed: ParsedFile, receiver_node: Node, method_node: Node) -> MethodCall:
    return MethodCall(
        rel_path=parsed.rel_path,
        receiver=receiver_node.text.decode("utf-8", "replace"),
        method=method_node.text.decode("utf-8", "replace"),
        enclosing_scope=_enclosing_scope_qn(method_node, parsed.language),
        line=_row(method_node),
        language=parsed.language,
    )


def _python_method_call(node: Node, parsed: ParsedFile) -> MethodCall | None:
    # `obj.foo()` → call(function: attribute(object: <recv>, attribute: foo))
    if node.type != "call":
        return None
    fn = node.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return None
    obj = fn.child_by_field_name("object")
    attr = fn.child_by_field_name("attribute")
    if obj is None or attr is None:
        return None
    return _make(parsed, obj, attr)


def _ts_js_method_call(node: Node, parsed: ParsedFile) -> MethodCall | None:
    # `obj.foo()` → call_expression(function: member_expression(object, property))
    if node.type != "call_expression":
        return None
    fn = node.child_by_field_name("function")
    if fn is None or fn.type != "member_expression":
        return None
    obj = fn.child_by_field_name("object")
    prop = fn.child_by_field_name("property")
    if obj is None or prop is None:
        return None
    return _make(parsed, obj, prop)


def _java_method_call(node: Node, parsed: ParsedFile) -> MethodCall | None:
    # `Recv.foo()` → method_invocation(object: <recv>, name: foo). A bare
    # `foo()` has no `object:` field and is handled by the DEC-025 bare path.
    if node.type != "method_invocation":
        return None
    obj = node.child_by_field_name("object")
    name = node.child_by_field_name("name")
    if obj is None or name is None:
        return None
    return _make(parsed, obj, name)


def _rust_method_call(node: Node, parsed: ParsedFile) -> MethodCall | None:
    # `g.greet()` → call_expression(function: field_expression(value, field))
    # `Greeter::new()` → call_expression(function: scoped_identifier(path, name))
    # The latter is Rust's static/associated call; the receiver is the path.
    if node.type != "call_expression":
        return None
    fn = node.child_by_field_name("function")
    if fn is None:
        return None
    if fn.type == "field_expression":
        value = fn.child_by_field_name("value")
        field = fn.child_by_field_name("field")
        if value is None or field is None:
            return None
        return _make(parsed, value, field)
    if fn.type == "scoped_identifier":
        path = fn.child_by_field_name("path")
        name = fn.child_by_field_name("name")
        if path is None or name is None:
            return None
        return _make(parsed, path, name)
    return None


_HANDLERS = {
    "python": _python_method_call,
    "typescript": _ts_js_method_call,
    "tsx": _ts_js_method_call,
    "javascript": _ts_js_method_call,
    "java": _java_method_call,
    "rust": _rust_method_call,  # DEC-040
}


def extract_method_calls(parsed: ParsedFile) -> list[MethodCall]:
    """Walk *parsed*'s tree and extract every dotted method call.

    Empty list for languages outside the v0.3 scope. Output is sorted by
    ``(line, receiver, method)`` for deterministic, golden-friendly order."""
    handler = _HANDLERS.get(parsed.language)
    if handler is None:
        return []
    out: list[MethodCall] = []
    stack = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        call = handler(node, parsed)
        if call is not None:
            out.append(call)
        stack.extend(node.children)
    out.sort(key=lambda m: (m.line, m.receiver, m.method))
    return out
