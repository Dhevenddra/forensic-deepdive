"""Registry-dispatch registration-provider extractor (DEC-058, v0.5 Step 3).

A registration is a *provider* of a registry tool — the ``HANDLES`` side of an
``Endpoint(protocol='registry')``. Three Python shapes (research §3)::

    @registry.register("greet")      # decorator, literal key
    def greet(): ...

    @registry.register               # decorator, bare → key = function name
    def wave(): ...

    TOOLS = {"add": add, "sub": sub}  # dict-literal map name → callable

    registry["mul"] = mul            # subscript assignment

Each registration emits **two** provider Contracts (the fan-out mechanism, DEC-047
inverted to the consumer-dynamic case): the **exact** ``registry::<id>::<key>`` (so a
literal-key dispatch resolves the single handler) and the **wildcard**
``registry::<id>::*`` (so a dynamic-key dispatch fans out to every handler through
the unchanged ``base.join``). The wildcard fan-out is **capped** per registry
(:data:`_FANOUT_CAP`, deterministic sort) so a giant registry can't explode the
graph — the cap is surfaced honestly via a ``logging.warning`` ("…and N more").

Registry identity ``<id>`` = the registry *variable name* (``TOOLS``/``registry``),
not its file-qualified name, so a registry registered across modules and dispatched
in another unions on the bare name (best-effort cross-module — PRD §3.3 deferral).
The indirection is real, so every registration is **INFERRED**-confidence (a name
match, not a direct call); the join then makes a unique literal-key match INFERRED
and a multi-handler dynamic match AMBIGUOUS. Handler ``symbol_id`` via
``_parent_chain`` (decorator) or ``<rel_path>::<name>`` (dict/subscript value), or
the edge is filtered against ``valid_symbol_qns``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.dispatch.normalize import (
    registry_contract_id,
    registry_wildcard_id,
)
from forensic_deepdive.contracts.http.scan import (
    first_positional_string,
    iter_candidate_files,
    py_string_literal,
    rightmost_name,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

logger = logging.getLogger(__name__)

_MARKERS = (b".register", b"= {", b"={", b"] =", b"]=")
_LANGS = ("python",)
# Per-registry dynamic-dispatch fan-out cap (mirrors the trace BFS path cap).
_FANOUT_CAP = 25


class _Registration(NamedTuple):
    registry_id: str
    key: str
    symbol_id: str
    rel_path: str
    line: int


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _value_symbol_id(value: Node, src: bytes, rel_path: str) -> str | None:
    """``symbol_id`` for a registration *value* (a dict/subscript RHS): a bare
    ``identifier`` referencing a module-level callable → ``<rel_path>::<name>``.
    Anything else (a lambda, ``obj.method``, a call) → ``None`` (skipped)."""
    if value.type != "identifier":
        return None
    return f"{rel_path}::{_text(value, src)}"


def _decorator_registration(decorator: Node, src: bytes) -> tuple[str, str | None] | None:
    """``(registry_id, explicit_key)`` for a ``@<recv>.register(...)`` / bare
    ``@<recv>.register`` / ``@register(...)`` decorator, or ``None``. A bare/empty
    decorator yields ``explicit_key=None`` (the caller uses the function name)."""
    expr = next(
        (c for c in decorator.children if c.type in ("call", "attribute", "identifier")), None
    )
    if expr is None:
        return None
    if expr.type == "attribute":  # @recv.register
        attr = expr.child_by_field_name("attribute")
        obj = expr.child_by_field_name("object")
        if attr is None or obj is None or _text(attr, src) != "register":
            return None
        recv = rightmost_name(obj, src)
        return (recv, None) if recv is not None else None
    if expr.type == "identifier":  # @register (bare module-level decorator)
        return (_text(expr, src), None) if _text(expr, src) == "register" else None
    # call form: @recv.register("x") or @register("x")
    fn = expr.child_by_field_name("function")
    if fn is None:
        return None
    args = expr.child_by_field_name("arguments")
    key = first_positional_string(args, src) if args is not None else None
    if fn.type == "attribute":
        attr = fn.child_by_field_name("attribute")
        obj = fn.child_by_field_name("object")
        if attr is None or obj is None or _text(attr, src) != "register":
            return None
        recv = rightmost_name(obj, src)
        return (recv, key) if recv is not None else None
    if fn.type == "identifier" and _text(fn, src) == "register":
        return "register", key
    return None


def _handler_symbol_id(definition: Node, src: bytes, rel_path: str) -> str | None:
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        return None
    parent = _parent_chain(name_node, "python")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return f"{rel_path}::{qn_local}"


def _collect_decorator_regs(root: Node, src: bytes, rel_path: str) -> list[_Registration]:
    regs: list[_Registration] = []
    for node in _walk(root):
        if node.type != "decorated_definition":
            continue
        definition = node.child_by_field_name("definition")
        if definition is None or definition.type != "function_definition":
            continue
        name_node = definition.child_by_field_name("name")
        if name_node is None:
            continue
        symbol_id = _handler_symbol_id(definition, src, rel_path)
        if symbol_id is None:
            continue
        for decorator in node.children:
            if decorator.type != "decorator":
                continue
            parsed = _decorator_registration(decorator, src)
            if parsed is None:
                continue
            registry_id, explicit = parsed
            key = explicit if explicit is not None else _text(name_node, src)
            if key:
                regs.append(
                    _Registration(registry_id, key, symbol_id, rel_path, name_node.start_point[0])
                )
    return regs


def _collect_assignment_regs(root: Node, src: bytes, rel_path: str) -> list[_Registration]:
    """Dict-literal (``TOOLS = {"k": fn}``) and subscript-assign (``reg["k"] = fn``)
    registrations."""
    regs: list[_Registration] = []
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None:
            continue
        # TOOLS = { "name": fn, ... }
        if left.type == "identifier" and right.type == "dictionary":
            registry_id = _text(left, src)
            for pair in right.children:
                if pair.type != "pair":
                    continue
                k = pair.child_by_field_name("key")
                v = pair.child_by_field_name("value")
                if k is None or v is None or k.type != "string":
                    continue
                key = py_string_literal(k, src)
                symbol_id = _value_symbol_id(v, src, rel_path)
                if key and symbol_id is not None:
                    regs.append(
                        _Registration(registry_id, key, symbol_id, rel_path, k.start_point[0])
                    )
        # registry["name"] = fn
        elif left.type == "subscript":
            obj = left.child_by_field_name("value")
            idx = left.child_by_field_name("subscript")
            if obj is None or idx is None or idx.type != "string":
                continue
            registry_id = rightmost_name(obj, src)
            key = py_string_literal(idx, src)
            symbol_id = _value_symbol_id(right, src, rel_path)
            if registry_id and key and symbol_id is not None:
                regs.append(
                    _Registration(registry_id, key, symbol_id, rel_path, left.start_point[0])
                )
    return regs


def _provider(reg: _Registration, contract_id: str) -> Contract:
    return Contract(
        role=ContractRole.PROVIDER,
        contract_id=contract_id,
        symbol_id=reg.symbol_id,
        confidence=Confidence.INFERRED,
        evidence=f"registry {reg.registry_id!r} registers {reg.key!r}",
        protocol="registry",
        method="",
        normalized_path=f"{reg.registry_id}::{reg.key}",
        raw_path=f"{reg.registry_id}[{reg.key!r}]",
        framework="registry-dispatch",
        rel_path=reg.rel_path,
        line=reg.line,
    )


def extract_registry_providers(ctx: ContractContext) -> list[Contract]:
    registrations: list[_Registration] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        registrations.extend(_collect_decorator_regs(root, src, rel_path))
        registrations.extend(_collect_assignment_regs(root, src, rel_path))

    contracts: list[Contract] = []
    seen_exact: set[tuple[str, str]] = set()
    # Exact providers — every registration, full HANDLES under its named endpoint.
    for reg in registrations:
        contract_id = registry_contract_id(reg.registry_id, reg.key)
        if (contract_id, reg.symbol_id) in seen_exact:
            continue
        seen_exact.add((contract_id, reg.symbol_id))
        contracts.append(_provider(reg, contract_id))

    # Wildcard providers — the dynamic-dispatch fan-out, capped per registry.
    by_registry: dict[str, list[_Registration]] = {}
    for reg in registrations:
        by_registry.setdefault(reg.registry_id, []).append(reg)
    for registry_id in sorted(by_registry):
        wildcard_id = registry_wildcard_id(registry_id)
        # Deduplicate handlers, deterministic order, then cap the fan-out.
        handlers = sorted(
            {(r.key, r.symbol_id, r.rel_path, r.line) for r in by_registry[registry_id]}
        )
        if len(handlers) > _FANOUT_CAP:
            logger.warning(
                "registry %r dynamic-dispatch fan-out capped at %d (%d more handler(s) omitted)",
                registry_id,
                _FANOUT_CAP,
                len(handlers) - _FANOUT_CAP,
            )
        for key, symbol_id, rel_path, line in handlers[:_FANOUT_CAP]:
            contracts.append(
                _provider(_Registration(registry_id, key, symbol_id, rel_path, line), wildcard_id)
            )
    return contracts
