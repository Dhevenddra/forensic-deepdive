"""FastAPI route-provider extractor (DEC-045, v0.4 Item F — first instance).

Mines provider :class:`~forensic_deepdive.contracts.base.Contract` records from
``@app.<verb>`` / ``@router.<verb>`` decorators, joining the router's own
``APIRouter(prefix=…)`` and cross-file ``include_router(…, prefix=…)`` mounts.

Confidence (DEC-045):
- an **app** route (``@app.get("/x")`` on a ``FastAPI()`` instance) with a literal
  path is a syntactic fact → **EXTRACTED**;
- a **router** route is **INFERRED** — its externally-visible path depends on where
  the router is mounted, which we resolve heuristically by matching the router's
  local variable name to ``include_router`` sites (cross-file, name-based).

A computed/f-string path can't form a stable ``contract_id`` and is dropped
(the honest "type unknown" posture of DEC-037), and a decorator whose object isn't
a recognised ``FastAPI()``/``APIRouter()`` instance is ignored (the guard).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_provider_path,
)
from forensic_deepdive.contracts.http.scan import (
    HTTP_VERBS,
    first_positional_string,
    iter_candidate_files,
    keyword_arg_value,
    rightmost_name,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"fastapi", b"FastAPI", b"APIRouter")
_FACTORIES = {"FastAPI": "app", "APIRouter": "router"}


class _Route(NamedTuple):
    object_name: str  # the app/router variable the decorator hangs off
    verb: str
    raw_path: str
    symbol_id: str
    line: int


class _FileScan(NamedTuple):
    objects: dict[str, tuple[str, str]]  # name -> (kind 'app'|'router', own_prefix)
    routes: list[_Route]
    mounts: list[tuple[str, str]]  # (router_local_name, mount_prefix)


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _call_callee_name(call: Node, src: bytes) -> str | None:
    fn = call.child_by_field_name("function")
    return rightmost_name(fn, src) if fn is not None else None


def _scan_file(rel_path: str, root: Node, src: bytes) -> _FileScan:
    objects: dict[str, tuple[str, str]] = {}
    routes: list[_Route] = []
    mounts: list[tuple[str, str]] = []

    for node in _walk(root):
        if node.type == "assignment":
            _collect_object(node, src, objects)
        elif node.type == "call":
            _collect_mount(node, src, mounts)
        elif node.type == "decorated_definition":
            _collect_routes(rel_path, node, src, routes)

    return _FileScan(objects, routes, mounts)


def _collect_object(assign: Node, src: bytes, objects: dict[str, tuple[str, str]]) -> None:
    left = assign.child_by_field_name("left")
    right = assign.child_by_field_name("right")
    if left is None or right is None or left.type != "identifier" or right.type != "call":
        return
    callee = _call_callee_name(right, src)
    kind = _FACTORIES.get(callee or "")
    if kind is None:
        return
    name = src[left.start_byte : left.end_byte].decode("utf-8", "replace")
    args = right.child_by_field_name("arguments")
    prefix = (keyword_arg_value(args, "prefix", src) or "") if args is not None else ""
    objects[name] = (kind, prefix)


def _collect_mount(call: Node, src: bytes, mounts: list[tuple[str, str]]) -> None:
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return
    attr = fn.child_by_field_name("attribute")
    if attr is None or src[attr.start_byte : attr.end_byte] != b"include_router":
        return
    args = call.child_by_field_name("arguments")
    if args is None:
        return
    router_arg = next(
        (c for c in args.children if c.type in ("identifier", "attribute")),
        None,
    )
    if router_arg is None:
        return
    name = rightmost_name(router_arg, src)
    if name is None:
        return
    mounts.append((name, keyword_arg_value(args, "prefix", src) or ""))


def _collect_routes(rel_path: str, decorated: Node, src: bytes, routes: list[_Route]) -> None:
    definition = decorated.child_by_field_name("definition")
    if definition is None or definition.type != "function_definition":
        return
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        return
    parent = _parent_chain(name_node, "python")
    handler = src[name_node.start_byte : name_node.end_byte].decode("utf-8", "replace")
    qn_local = f"{parent}.{handler}" if parent else handler
    symbol_id = f"{rel_path}::{qn_local}"

    for child in decorated.children:
        if child.type != "decorator":
            continue
        call = next((c for c in child.children if c.type == "call"), None)
        if call is None:
            continue
        fn = call.child_by_field_name("function")
        if fn is None or fn.type != "attribute":
            continue
        verb_node = fn.child_by_field_name("attribute")
        obj_node = fn.child_by_field_name("object")
        if verb_node is None or obj_node is None:
            continue
        verb = src[verb_node.start_byte : verb_node.end_byte].decode("utf-8", "replace").lower()
        if verb not in HTTP_VERBS:
            continue
        object_name = rightmost_name(obj_node, src)
        args = call.child_by_field_name("arguments")
        raw_path = first_positional_string(args, src) if args is not None else None
        if object_name is None or raw_path is None:
            continue  # computed path or unrecognised object → drop (DEC-037 posture)
        routes.append(_Route(object_name, verb, raw_path, symbol_id, name_node.start_point[0]))


def extract_fastapi_providers(ctx: ContractContext) -> list[Contract]:
    scans: list[tuple[str, _FileScan]] = []
    mounts_by_name: dict[str, set[str]] = {}
    for rel_path, src, root in iter_candidate_files(ctx, languages=("python",), markers=_MARKERS):
        scan = _scan_file(rel_path, root, src)
        for name, prefix in scan.mounts:
            mounts_by_name.setdefault(name, set()).add(prefix)
        scans.append((rel_path, scan))

    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, scan in scans:
        for route in scan.routes:
            obj = scan.objects.get(route.object_name)
            if obj is None:
                continue  # decorator object isn't a FastAPI app/router here
            kind, own_prefix = obj
            base = own_prefix + route.raw_path
            if kind == "app":
                candidates = [(base, Confidence.EXTRACTED)]
            else:
                mounts = sorted(mounts_by_name.get(route.object_name, set()))
                paths = [mp + base for mp in mounts] if mounts else [base]
                candidates = [(p, Confidence.INFERRED) for p in paths]

            for raw, confidence in candidates:
                normalized = normalize_provider_path(raw)
                if is_noise_path(normalized):
                    continue
                contract_id = http_contract_id(route.verb, normalized)
                key = (contract_id, route.symbol_id)
                if key in seen:
                    continue
                seen.add(key)
                contracts.append(
                    Contract(
                        role=ContractRole.PROVIDER,
                        contract_id=contract_id,
                        symbol_id=route.symbol_id,
                        confidence=confidence,
                        evidence=f"fastapi @{route.object_name}.{route.verb}({route.raw_path!r})",
                        protocol="http",
                        method=route.verb.upper(),
                        normalized_path=normalized,
                        raw_path=raw,
                        framework="fastapi",
                        rel_path=rel_path,
                        line=route.line,
                    )
                )
    return contracts
