"""jQuery AJAX consumer extractor (DEC-046, v0.4 Item G).

Emits consumer ``CALLS_ENDPOINT`` records for jQuery's AJAX shorthands
(javascript/typescript)::

    $.get(`/api/users/${id}`, cb);          // GET, url = first arg
    $.post('/api/users', { name });         // POST, url = first arg
    $.getJSON('/api/users', cb);            // GET
    $.ajax({ url: '/api/users', method: 'DELETE' });   // verb from method|type
    jQuery.ajax({ url: '/api/things', type: 'PUT' });

The receiver is the jQuery object (``$`` or ``jQuery``). ``$.get``/``$.post``/
``$.getJSON`` take the URL as the first positional argument; ``$.ajax`` takes a
config object whose ``url`` is the path and whose ``method`` (or the legacy
``type``) is the verb (default GET). A computed URL (string concatenation, bare
variable) is dropped (no stable id).

Caller ``symbol_id`` is the nearest enclosing named callable (``_enclosing_symbol``),
or the file ``<module>``. Confidence: literal URL = EXTRACTED, template/numeric =
INFERRED.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.consumers.fetch_axios import (
    _enclosing_symbol,
    _positional_args,
    _url_from,
    _walk,
)
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_consumer_path,
)
from forensic_deepdive.contracts.http.scan import (
    HTTP_VERBS,
    iter_candidate_files,
    js_object_string_prop,
)
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"$.", b"jQuery")
_LANGS = ("javascript", "typescript", "tsx")
_JQUERY_OBJECTS = frozenset({"$", "jQuery"})
# shorthand method → verb (url is the first positional arg)
_SHORTHAND = {"get": "get", "post": "post", "getjson": "get"}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _ajax_url_verb(obj_arg: Node, src: bytes) -> tuple[str, str] | None:
    """``(raw_url, verb)`` from a ``$.ajax({ url, method|type })`` config object."""
    url = js_object_string_prop(obj_arg, "url", src)
    if url is None:
        return None
    method = js_object_string_prop(obj_arg, "method", src) or js_object_string_prop(
        obj_arg, "type", src
    )
    verb = method.lower() if method and method.lower() in HTTP_VERBS else "get"
    return url, verb


def extract_jquery_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "member_expression":
                continue
            obj = fn.child_by_field_name("object")
            prop = fn.child_by_field_name("property")
            if obj is None or prop is None or _text(obj, src) not in _JQUERY_OBJECTS:
                continue
            method_name = _text(prop, src).lower()
            pos = _positional_args(node)
            if method_name in _SHORTHAND and pos:
                verb = _SHORTHAND[method_name]
                raw_url = _url_from(pos[0], src)
            elif method_name == "ajax" and pos and pos[0].type == "object":
                resolved = _ajax_url_verb(pos[0], src)
                if resolved is None:
                    continue
                raw_url, verb = resolved
            else:
                continue
            if raw_url is None:
                continue
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
                    evidence=f"jquery {verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="jquery",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
