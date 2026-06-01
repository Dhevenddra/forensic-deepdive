"""Express route-provider extractor (DEC-045, v0.4 Item F — research §2 core).

Express has no decorators — routes are method calls ``app.<verb>(path, …handlers)``
on an ``express()`` app or an ``express.Router()`` instance, mounted with
``app.use(prefix, router)``. Covers javascript / typescript / tsx.

Handler attribution:
- a **named** handler (``app.post("/u", createUser)``) → that symbol if it's
  defined in the same file;
- an **inline** handler (``(req,res) => …``) is anonymous → attributed to the
  file's synthetic ``<module>`` symbol (which the graph always has).

Confidence (DEC-045): an **app** route with a literal path is **EXTRACTED**; a
**router** route is **INFERRED** (its external path depends on the ``app.use``
mount prefix, resolved by name across files). Template-literal/computed paths
are dropped (DEC-037 posture).
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
    iter_candidate_files,
    js_string_literal,
)
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"express", b"Router")
_LANGS = ("javascript", "typescript", "tsx")
_MODULE = "<module>"


class _Route(NamedTuple):
    object_name: str
    verb: str
    raw_path: str
    handler_local: str  # the handler's qn_local (a name or "<module>")
    line: int


class _FileScan(NamedTuple):
    objects: dict[str, str]  # name -> 'app' | 'router'
    routes: list[_Route]
    mounts: list[tuple[str, str]]  # (router_name, prefix)


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _member_parts(member: Node, src: bytes) -> tuple[Node | None, str | None]:
    """``(object_node, property_name)`` for a ``member_expression`` (``app.get``
    → object ``app``, property ``get``)."""
    obj = member.child_by_field_name("object")
    prop = member.child_by_field_name("property")
    return obj, (_text(prop, src) if prop is not None else None)


def _positional_args(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    if args is None:
        return []
    return [c for c in args.children if c.is_named]


def _collect_instance(declarator: Node, src: bytes, objects: dict[str, str]) -> None:
    name_node = declarator.child_by_field_name("name")
    value = declarator.child_by_field_name("value")
    if name_node is None or name_node.type != "identifier" or value is None:
        return
    if value.type != "call_expression":
        return
    fn = value.child_by_field_name("function")
    if fn is None:
        return
    name = _text(name_node, src)
    if fn.type == "identifier" and _text(fn, src) == "express":
        objects[name] = "app"
    elif fn.type == "member_expression":
        _, prop = _member_parts(fn, src)
        if prop == "Router":
            objects[name] = "router"
    elif fn.type == "identifier" and _text(fn, src) == "Router":
        objects[name] = "router"


def _collect_call(rel_path: str, call: Node, src: bytes, scan: _FileScan) -> None:
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "member_expression":
        return
    obj, prop = _member_parts(fn, src)
    if obj is None or obj.type != "identifier" or prop is None:
        return
    object_name = _text(obj, src)
    pos = _positional_args(call)

    if prop == "use":
        # app.use(prefix?, router) — a mount only when an identifier router arg exists.
        prefix = ""
        router_name = None
        for arg in pos:
            if arg.type in ("string", "template_string") and not prefix:
                prefix = js_string_literal(arg, src) or ""
            elif arg.type == "identifier":
                router_name = _text(arg, src)
        if router_name is not None:
            scan.mounts.append((router_name, prefix))
        return

    if prop in HTTP_VERBS and pos:
        raw_path = js_string_literal(pos[0], src)
        if raw_path is None:
            return  # computed path → drop
        handler = pos[-1] if len(pos) > 1 else None
        if handler is not None and handler.type == "identifier":
            handler_local = _text(handler, src)
        else:
            handler_local = _MODULE  # inline/absent → the module symbol
        scan.routes.append(_Route(object_name, prop, raw_path, handler_local, call.start_point[0]))


def _scan_file(rel_path: str, root: Node, src: bytes) -> _FileScan:
    scan = _FileScan(objects={}, routes=[], mounts=[])
    for node in _walk(root):
        if node.type == "variable_declarator":
            _collect_instance(node, src, scan.objects)
        elif node.type == "call_expression":
            _collect_call(rel_path, node, src, scan)
    return scan


def extract_express_providers(ctx: ContractContext) -> list[Contract]:
    scans: list[tuple[str, _FileScan]] = []
    mounts_by_name: dict[str, set[str]] = {}
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        scan = _scan_file(rel_path, root, src)
        for name, prefix in scan.mounts:
            mounts_by_name.setdefault(name, set()).add(prefix)
        scans.append((rel_path, scan))

    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, scan in scans:
        for route in scan.routes:
            kind = scan.objects.get(route.object_name)
            if kind is None:
                continue  # not a recognised express app/router
            symbol_id = f"{rel_path}::{route.handler_local}"
            if kind == "app":
                candidates = [(route.raw_path, Confidence.EXTRACTED)]
            else:
                mounts = sorted(mounts_by_name.get(route.object_name, set()))
                paths = [mp + route.raw_path for mp in mounts] if mounts else [route.raw_path]
                candidates = [(p, Confidence.INFERRED) for p in paths]
            for raw, confidence in candidates:
                normalized = normalize_provider_path(raw)
                if is_noise_path(normalized):
                    continue
                contract_id = http_contract_id(route.verb, normalized)
                key = (contract_id, symbol_id)
                if key in seen:
                    continue
                seen.add(key)
                contracts.append(
                    Contract(
                        role=ContractRole.PROVIDER,
                        contract_id=contract_id,
                        symbol_id=symbol_id,
                        confidence=confidence,
                        evidence=f"express {route.object_name}.{route.verb}({route.raw_path!r})",
                        protocol="http",
                        method=route.verb.upper(),
                        normalized_path=normalized,
                        raw_path=raw,
                        framework="express",
                        rel_path=rel_path,
                        line=route.line,
                    )
                )
    return contracts
