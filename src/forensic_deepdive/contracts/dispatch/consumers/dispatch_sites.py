"""Registry-dispatch dispatch-site consumer extractor (DEC-058, v0.5 Step 3).

A dispatch is a *consumer* of a registry tool — the ``CALLS_ENDPOINT`` side. Two
Python shapes (research §3)::

    registry[name]()          # subscript-then-call
    TOOLS["add"](a, b)        # literal key → exact endpoint
    registry.get(name)()      # .get-then-call

**Literal key** (``TOOLS["add"]()``) → keys the exact ``registry::<id>::add`` → the
join resolves the one handler → **INFERRED** (the registry indirection is real).
**Dynamic key** (``registry[var]()``) → keys the wildcard ``registry::<id>::*`` → the
unchanged ``base.join`` fans it out to every registered handler → **AMBIGUOUS-all**.
Either way the per-edge consumer confidence is **INFERRED** (we know the registry;
the join decides unique-vs-ambiguous). Caller ``symbol_id`` via ``_parent_chain``
(the enclosing ``def``, else ``<module>``), reused from the requests/httpx consumer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.dispatch.normalize import (
    WILDCARD,
    registry_contract_id,
)
from forensic_deepdive.contracts.http.consumers.py_requests import _enclosing_symbol, _walk
from forensic_deepdive.contracts.http.scan import (
    iter_candidate_files,
    py_string_literal,
    rightmost_name,
)
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"](", b".get(", b".get (")
_LANGS = ("python",)


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _dispatch(call: Node, src: bytes) -> tuple[str, str] | None:
    """``(registry_id, key)`` for a registry dispatch call, or ``None``. *key* is
    the literal dict key, or :data:`WILDCARD` when the dispatch key is a variable
    (dynamic → fan-out). Handles ``registry[key]()`` and ``registry.get(key)()``."""
    fn = call.child_by_field_name("function")
    if fn is None:
        return None
    # registry[ key ]()
    if fn.type == "subscript":
        obj = fn.child_by_field_name("value")
        idx = fn.child_by_field_name("subscript")
        if obj is None or idx is None:
            return None
        registry_id = rightmost_name(obj, src)
        if registry_id is None:
            return None
        key = py_string_literal(idx, src) if idx.type == "string" else None
        return registry_id, (key if key is not None else WILDCARD)
    # registry.get( key )()
    if fn.type == "call":
        inner_fn = fn.child_by_field_name("function")
        if inner_fn is None or inner_fn.type != "attribute":
            return None
        attr = inner_fn.child_by_field_name("attribute")
        obj = inner_fn.child_by_field_name("object")
        if attr is None or obj is None or _text(attr, src) != "get":
            return None
        registry_id = rightmost_name(obj, src)
        if registry_id is None:
            return None
        inner_args = fn.child_by_field_name("arguments")
        key_node = next(
            (c for c in inner_args.children if c.is_named) if inner_args is not None else (),
            None,
        )
        key = (
            py_string_literal(key_node, src)
            if key_node is not None and key_node.type == "string"
            else None
        )
        return registry_id, (key if key is not None else WILDCARD)
    return None


def extract_registry_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call":
                continue
            parsed = _dispatch(node, src)
            if parsed is None:
                continue
            registry_id, key = parsed
            if not registry_id:
                continue
            contract_id = registry_contract_id(registry_id, key)
            symbol_id = _enclosing_symbol(node, src, rel_path)
            if (contract_id, symbol_id) in seen:
                continue
            seen.add((contract_id, symbol_id))
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=Confidence.INFERRED,
                    evidence=f"{registry_id}[{key!r}]() dispatch",
                    protocol="registry",
                    method="",
                    normalized_path=f"{registry_id}::{key}",
                    raw_path=f"{registry_id}[{key}]",
                    framework="registry-dispatch",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
