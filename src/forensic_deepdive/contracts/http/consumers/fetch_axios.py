"""fetch / axios frontend consumer extractor (DEC-046, v0.4 Item G — first instance).

Emits consumer :class:`~forensic_deepdive.contracts.base.Contract` records (the
``CALLS_ENDPOINT`` side) for js/ts/tsx call sites:
- ``fetch(url, { method })`` — method from the options object, **default GET**;
- ``axios.<verb>(url, …)`` — verb from the member property;
- ``axios({ method, url })`` — both from the object literal.

The URL runs through :func:`normalize_consumer_path` (template ``${x}`` and
numeric segments collapse to ``{param}``), so a client ``/users/${id}`` joins a
provider ``/users/{id}`` on the same ``contract_id``. A fully-dynamic URL (a bare
variable) is dropped (no stable id — DEC-037 posture).

Caller ``symbol_id`` is the nearest enclosing named callable (``_parent_chain``
convention), or the file's ``<module>`` symbol at module scope. Confidence:
literal URL = EXTRACTED; template/numeric-normalized = INFERRED. (The ROUTES_TO
join carries its own confidence — DEC-043/047.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_consumer_path,
)
from forensic_deepdive.contracts.http.scan import (
    HTTP_VERBS,
    iter_candidate_files,
    js_object_string_prop,
    js_url_text,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"fetch", b"axios")
_LANGS = ("javascript", "typescript", "tsx")
_MODULE = "<module>"
# JS nodes that name an enclosing callable we can attribute a call to.
_NAMED_FUNCTION = {"function_declaration", "generator_function_declaration", "method_definition"}
_ANON_FUNCTION = {"arrow_function", "function_expression", "generator_function"}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _positional_args(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    return [c for c in args.children if c.is_named] if args is not None else []


def _enclosing_symbol(call: Node, src: bytes, rel_path: str) -> str:
    """The nearest enclosing named callable's qualified id, or the file's
    ``<module>`` symbol. Reuses ``_parent_chain`` so the id matches the graph."""
    node = call.parent
    while node is not None:
        name_node = None
        if node.type in _NAMED_FUNCTION:
            name_node = node.child_by_field_name("name")
        elif node.type in _ANON_FUNCTION and node.parent is not None:
            if node.parent.type == "variable_declarator":
                name_node = node.parent.child_by_field_name("name")
            elif node.parent.type == "pair":
                name_node = node.parent.child_by_field_name("key")
        if name_node is not None and name_node.type in ("identifier", "property_identifier"):
            parent = _parent_chain(name_node, "javascript")
            name = _text(name_node, src)
            qn_local = f"{parent}.{name}" if parent else name
            return f"{rel_path}::{qn_local}"
        node = node.parent
    return f"{rel_path}::{_MODULE}"


def _classify(call: Node, src: bytes) -> tuple[str, Node] | None:
    """Return ``(verb, url_node)`` for a fetch/axios call, or ``None``. ``url_node``
    is the node to read the URL from (a string/template, or an options object for
    ``axios({url})``)."""
    fn = call.child_by_field_name("function")
    if fn is None:
        return None
    pos = _positional_args(call)
    if fn.type == "identifier":
        name = _text(fn, src)
        if name == "fetch" and pos:
            verb = "get"
            if len(pos) > 1 and pos[1].type == "object":
                method = js_object_string_prop(pos[1], "method", src)
                if method and method.lower() in HTTP_VERBS:
                    verb = method.lower()
            return verb, pos[0]
        if name == "axios" and pos and pos[0].type == "object":
            method = js_object_string_prop(pos[0], "method", src) or "get"
            verb = method.lower() if method.lower() in HTTP_VERBS else "get"
            return verb, pos[0]  # url read from the same object below
        return None
    if fn.type == "member_expression":
        obj = fn.child_by_field_name("object")
        prop = fn.child_by_field_name("property")
        if obj is None or prop is None or obj.type != "identifier":
            return None
        if _text(obj, src) == "axios" and _text(prop, src) in HTTP_VERBS and pos:
            return _text(prop, src), pos[0]
    return None


def _url_from(node: Node, src: bytes) -> str | None:
    """URL text from a string/template node, or from an ``axios({url})`` object."""
    if node.type == "object":
        return js_object_string_prop(node, "url", src)
    return js_url_text(node, src)


def extract_fetch_axios_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            classified = _classify(node, src)
            if classified is None:
                continue
            verb, url_node = classified
            raw_url = _url_from(url_node, src)
            if raw_url is None:
                continue  # fully dynamic → drop
            normalized = normalize_consumer_path(raw_url)
            if is_noise_path(normalized):
                continue
            contract_id = http_contract_id(verb, normalized)
            symbol_id = _enclosing_symbol(node, src, rel_path)
            key = (contract_id, symbol_id)
            if key in seen:
                continue
            seen.add(key)
            confidence = (
                Confidence.EXTRACTED if "{param}" not in normalized else Confidence.INFERRED
            )
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=confidence,
                    evidence=f"{verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="fetch/axios",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
