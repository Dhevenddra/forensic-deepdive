"""Configured-HTTP-client consumer extractor (DEC-056, v0.5 Step 1 — the
flagship-gap closer).

v0.4 scored ``0 ROUTES_TO`` on Superset partly because its frontend never calls
``fetch``/``axios`` directly — it goes through a configured client wrapper,
``SupersetClient.get/post/put/delete({ endpoint })`` (252 call sites, matched by
none of the seven raw consumer extractors). This generalizes the existing
``axios({ url })`` object path to **any** receiver whose call is
``<recv>.<verb>({ endpoint | url | path: '…' })``.

**The false-positive guard is the SHAPE, not a client allowlist** (no one-repo
hacks): we fire only when the call is ``<recv>.<http-verb>(...)`` **and** the
first argument is an *object literal* carrying a string-valued ``endpoint`` /
``url`` / ``path`` key. A bare ``axios`` receiver is skipped — the fetch/axios
extractor already owns the ``axios.<verb>({ url })`` shape (DEC-046), so skipping
it here avoids a double-emitted consumer. A ``<recv>.request({ method, endpoint })``
form is also matched, with the verb read from the object's ``method`` key.

URL via :func:`normalize_consumer_path` (so a templated ``/chart/${id}`` joins a
provider ``/chart/{id}``); caller ``symbol_id`` via the shared ``_parent_chain``
convention (:func:`_enclosing_symbol`). Confidence: literal endpoint = EXTRACTED;
templated/numeric-normalized = INFERRED (the ROUTES_TO join carries its own
confidence — DEC-043/047).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.consumers.fetch_axios import (
    _enclosing_symbol,
    _positional_args,
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

# Pre-filter: a configured-client call is a member call on an HTTP verb (or
# ``.request``). Broad on purpose — the AST shape guard does the real filtering.
_MARKERS = (b".get(", b".post(", b".put(", b".delete(", b".patch(", b".request(")
_LANGS = ("javascript", "typescript", "tsx")
# Object-literal keys that name the endpoint path, in priority order.
_URL_KEYS = ("endpoint", "url", "path")
# Receivers the fetch/axios extractor already owns — skip to avoid double emit.
_OWNED_RECEIVERS = {"axios"}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _object_url(obj: Node, src: bytes) -> str | None:
    """The first present string-valued ``endpoint``/``url``/``path`` of an object
    literal (priority order), or ``None`` when none is a static/template string."""
    for key in _URL_KEYS:
        value = js_object_string_prop(obj, key, src)
        if value is not None:
            return value
    return None


def _classify(call: Node, src: bytes) -> tuple[str, str] | None:
    """Return ``(verb, raw_url)`` for a configured-client call, or ``None``.

    Fires only for ``<recv>.<verb>(objLiteral)`` where the object literal carries
    a string ``endpoint``/``url``/``path`` — the shape guard. ``<recv>.request``
    reads the verb from the object's ``method`` key (default GET)."""
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "member_expression":
        return None
    obj = fn.child_by_field_name("object")
    prop = fn.child_by_field_name("property")
    if obj is None or prop is None or prop.type != "property_identifier":
        return None
    # The fetch/axios extractor already handles ``axios.<verb>({ url })``.
    if obj.type == "identifier" and _text(obj, src) in _OWNED_RECEIVERS:
        return None
    prop_text = _text(prop, src)
    pos = _positional_args(call)
    if not pos or pos[0].type != "object":
        return None
    arg0 = pos[0]
    raw_url = _object_url(arg0, src)
    if raw_url is None:
        return None
    if prop_text in HTTP_VERBS:
        return prop_text, raw_url
    if prop_text == "request":
        method = js_object_string_prop(arg0, "method", src) or "get"
        verb = method.lower() if method.lower() in HTTP_VERBS else "get"
        return verb, raw_url
    return None


def extract_configured_client_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            classified = _classify(node, src)
            if classified is None:
                continue
            verb, raw_url = classified
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
                    evidence=f"client.{verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="configured-client",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
