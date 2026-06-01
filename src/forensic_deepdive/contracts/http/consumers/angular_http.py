"""Angular ``HttpClient`` consumer extractor (DEC-046, v0.4 Item G).

Emits consumer ``CALLS_ENDPOINT`` records for Angular's ``HttpClient`` calls
(typescript)::

    @Injectable()
    export class UserService {
      constructor(private http: HttpClient) {}
      getUser(id: string)  { return this.http.get(`/api/users/${id}`); }
      addUser(body)        { return this.http.post('/api/users', body); }
    }

The call is ``<receiver>.<verb>(url, …)`` where ``<receiver>`` is an
``http``-ish member (``this.http`` / ``this.httpClient`` / ``this._http``) — the
``HttpClient``-typed field. We can't see the field's *type* without resolution,
so we guard on the receiver name (the property identifier of the member access
contains ``http``, case-insensitive) plus the verb being an HTTP method. The URL
is the first positional argument (HttpClient's signature for every verb).

Caller ``symbol_id`` is the enclosing class method (``UserService.getUser`` — a
real graph symbol via ``_parent_chain``). Confidence: literal URL = EXTRACTED,
template/numeric = INFERRED.
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
from forensic_deepdive.contracts.http.scan import HTTP_VERBS, iter_candidate_files
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"HttpClient", b".http", b"httpClient")
_LANGS = ("typescript", "tsx")


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _is_http_receiver(obj: Node, src: bytes) -> bool:
    """True when *obj* is an ``http``-ish member access — ``this.http`` /
    ``this.httpClient`` / ``this._http`` (the receiver's property name contains
    ``http``). Also accepts a bare ``http`` identifier (a local HttpClient)."""
    if obj.type == "member_expression":
        prop = obj.child_by_field_name("property")
        return prop is not None and "http" in _text(prop, src).lower()
    if obj.type == "identifier":
        return "http" in _text(obj, src).lower()
    return False


def extract_angular_http_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call_expression":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "member_expression":
                continue
            prop = fn.child_by_field_name("property")
            obj = fn.child_by_field_name("object")
            if prop is None or obj is None:
                continue
            verb = _text(prop, src)
            if verb not in HTTP_VERBS or not _is_http_receiver(obj, src):
                continue
            pos = _positional_args(node)
            if not pos:
                continue
            raw_url = _url_from(pos[0], src)
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
                    evidence=f"angular {verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework="angular-httpclient",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
