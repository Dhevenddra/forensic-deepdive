"""Python ``requests`` / ``httpx`` consumer extractor (DEC-046, v0.4 Item G).

Emits consumer ``CALLS_ENDPOINT`` records for the two dominant Python HTTP
clients::

    requests.get(f"/api/users/{id}")             # module verb, url = arg 0
    requests.post("/api/users", json=body)
    requests.request("DELETE", "/api/users/1")   # verb = arg 0, url = arg 1
    httpx.get("/api/things")
    client.get("/api/things")                    # client-var receiver (INFERRED)

Two receiver classes, deliberately split by how much we trust them:
- **Module receivers** ``requests`` / ``httpx`` are unambiguous — a literal URL is
  EXTRACTED (template/numeric → INFERRED).
- **Client-var receivers** (``client`` / ``session`` / ``http`` …) are a *guess*
  that the variable is an HTTP client; to avoid mis-reading ``d.get("key")`` we
  both restrict the receiver name to a small allowlist **and** force the edge to
  INFERRED (the "is this even an HTTP call" is itself inferred).

Caller ``symbol_id`` is the enclosing ``def`` (``Client.add`` via ``_parent_chain``),
or the file ``<module>``. A non-literal URL (concatenation / bare variable) is
dropped.
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
    py_is_fstring,
    py_url_text,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"requests", b"httpx")
_LANGS = ("python",)
_MODULE = "<module>"
_MODULE_RECEIVERS = frozenset({"requests", "httpx"})
# Conservative allowlist of HTTP-client variable names (avoids dict.get etc.).
_CLIENT_RECEIVERS = frozenset(
    {"client", "session", "http", "_client", "_session", "_http", "http_client", "httpx_client"}
)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _positional_strings(call: Node) -> list[Node]:
    """Positional argument nodes (skipping keyword args) of a Python ``call``."""
    args = call.child_by_field_name("arguments")
    if args is None:
        return []
    return [c for c in args.children if c.is_named and c.type != "keyword_argument"]


def _enclosing_symbol(call: Node, src: bytes, rel_path: str) -> str:
    """Nearest enclosing ``def``'s qualified id (``_parent_chain`` for the class
    prefix), or the file ``<module>`` — the same convention the graph uses."""
    node = call.parent
    while node is not None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                parent = _parent_chain(name_node, "python")
                name = _text(name_node, src)
                qn_local = f"{parent}.{name}" if parent else name
                return f"{rel_path}::{qn_local}"
        node = node.parent
    return f"{rel_path}::{_MODULE}"


def _resolve_call(fn: Node, call: Node, src: bytes) -> tuple[str, Node, bool] | None:
    """``(verb, url_node, is_client_var)`` for a requests/httpx call, or ``None``.

    ``is_client_var`` marks the heuristic receiver class (→ forced INFERRED)."""
    if fn.type != "attribute":
        return None
    obj = fn.child_by_field_name("object")
    attr = fn.child_by_field_name("attribute")
    if obj is None or attr is None or obj.type != "identifier":
        return None
    obj_name = _text(obj, src)
    is_module = obj_name in _MODULE_RECEIVERS
    is_client = obj_name in _CLIENT_RECEIVERS
    if not (is_module or is_client):
        return None
    method = _text(attr, src)
    pos = _positional_strings(call)
    if method == "request":
        # requests.request("DELETE", url)
        if len(pos) < 2 or pos[0].type != "string":
            return None
        verb_literal = py_url_text(pos[0], src)
        if verb_literal is None or verb_literal.lower() not in HTTP_VERBS:
            return None
        return verb_literal.lower(), pos[1], is_client
    if method in HTTP_VERBS and pos:
        return method, pos[0], is_client
    return None


def extract_py_requests_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call":
                continue
            fn = node.child_by_field_name("function")
            if fn is None:
                continue
            resolved = _resolve_call(fn, node, src)
            if resolved is None:
                continue
            verb, url_node, is_client = resolved
            raw_url = py_url_text(url_node, src)
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
            # literal + module receiver → EXTRACTED; template/numeric or a guessed
            # client-var receiver → INFERRED.
            literal = "{param}" not in normalized and not py_is_fstring(url_node, src)
            confidence = Confidence.EXTRACTED if literal and not is_client else Confidence.INFERRED
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=confidence,
                    evidence=f"requests {verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="requests/httpx",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
