"""RTK Query (Redux Toolkit) consumer extractor (DEC-046, v0.4 Item G).

Emits consumer ``CALLS_ENDPOINT`` records for the RTK Query ``createApi`` /
``api.injectEndpoints`` builder pattern (js/ts/tsx)::

    createApi({
      endpoints: (builder) => ({
        getUser:  builder.query({    query: (id)   => `/users/${id}` }),
        listUsers: builder.query({   query: ()     => ({ url: '/users', method: 'GET' }) }),
        addUser:  builder.mutation({ query: (body) => ({ url: '/users', method: 'POST', body }) }),
      }),
    })

The signature we key on is a ``<builder>.query(...)`` / ``<builder>.mutation(...)``
member call whose sole object argument carries a ``query:`` arrow — a shape
specific enough to RTK that the ``createApi``/``injectEndpoints`` marker pre-filter
plus this guard avoids false positives on unrelated ``.query()`` calls. The
``query`` arrow's body is the URL source: a string/template literal is the URL
directly (method defaults to GET); a returned ``{ url, method }`` object supplies
both.

**Attribution.** RTK endpoints are module-scope *declarations*, not calls nested
in a named callable — and the endpoint key (``getUser``) and the ``createApi``
const are object/arrow-bound names the JS symbol graph does not capture as
symbols. So a CALLS_ENDPOINT attributed to them would be silently filtered. We
attribute to the file's ``<module>`` symbol (always in the graph) and carry the
endpoint key in the evidence string. Confidence: literal URL = EXTRACTED;
template/numeric-normalized = INFERRED (the ROUTES_TO join carries its own).
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

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"createApi", b"injectEndpoints")
_LANGS = ("javascript", "typescript", "tsx")
_MODULE = "<module>"
_BUILDER_METHODS = frozenset({"query", "mutation"})


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _object_arg(call: Node) -> Node | None:
    """The first object-literal positional argument of *call*, or ``None``."""
    args = call.child_by_field_name("arguments")
    if args is None:
        return None
    for child in args.children:
        if child.type == "object":
            return child
    return None


def _pair_value(obj: Node, name: str) -> Node | None:
    """The value node of property *name* in an ``object`` literal (raw node)."""
    for pair in obj.children:
        if pair.type != "pair":
            continue
        key = pair.child_by_field_name("key")
        value = pair.child_by_field_name("value")
        if key is not None and value is not None and _text_key(key) == name:
            return value
    return None


def _text_key(key: Node) -> str:
    # property_identifier or string key
    if key.type == "string":
        return "".join(
            c.text.decode("utf-8", "replace") for c in key.children if c.type == "string_fragment"
        )
    return key.text.decode("utf-8", "replace")


def _query_arrow_body(query_value: Node) -> Node | None:
    """The body expression of a ``query`` arrow, unwrapping an ``=> ({...})``
    parenthesis and a ``=> { return ... }`` block to the returned expression."""
    if query_value.type != "arrow_function":
        return None
    body = query_value.child_by_field_name("body")
    if body is None:
        return None
    if body.type == "parenthesized_expression":
        for child in body.named_children:
            return child
        return None
    if body.type == "statement_block":
        for node in _walk(body):
            if node.type == "return_statement":
                for child in node.named_children:
                    return child
        return None
    return body


def _url_and_verb(body: Node, src: bytes) -> tuple[str, str] | None:
    """``(raw_url, verb)`` from a query-arrow body: a string/template → URL with
    default GET; a returned ``{ url, method }`` object → both."""
    if body.type == "object":
        url = js_object_string_prop(body, "url", src)
        if url is None:
            return None
        method = js_object_string_prop(body, "method", src)
        verb = method.lower() if method and method.lower() in HTTP_VERBS else "get"
        return url, verb
    url = js_url_text(body, src)
    if url is None:
        return None
    return url, "get"


def extract_rtk_query_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        symbol_id = f"{rel_path}::{_MODULE}"
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "member_expression":
                continue
            prop = fn.child_by_field_name("property")
            if prop is None or _text(prop, src) not in _BUILDER_METHODS:
                continue
            obj_arg = _object_arg(node)
            if obj_arg is None:
                continue
            query_value = _pair_value(obj_arg, "query")
            if query_value is None:
                continue
            body = _query_arrow_body(query_value)
            if body is None:
                continue
            resolved = _url_and_verb(body, src)
            if resolved is None:
                continue
            raw_url, verb = resolved
            normalized = normalize_consumer_path(raw_url)
            if is_noise_path(normalized):
                continue
            contract_id = http_contract_id(verb, normalized)
            key = (contract_id, symbol_id)
            if key in seen:
                continue
            seen.add(key)
            confidence = (
                Confidence.EXTRACTED if "{param}" not in normalized else Confidence.INFERRED
            )
            endpoint_key = _endpoint_name(node, src)
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=confidence,
                    evidence=f"rtk {endpoint_key}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="rtk-query",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts


def _endpoint_name(builder_call: Node, src: bytes) -> str:
    """The endpoint key (``getUser``) — the ``pair`` key enclosing the
    ``builder.query(...)`` call — for the evidence string. ``?`` if not found."""
    node = builder_call.parent
    while node is not None:
        if node.type == "pair":
            key = node.child_by_field_name("key")
            if key is not None:
                return _text_key(key)
        node = node.parent
    return "?"
