"""Flask route-provider extractor (DEC-045, v0.4 Item F — research §2 gap-closer).

Flask differs from FastAPI in three ways the extractor must handle:
- the verb lives in a ``methods=[...]`` kwarg on ``@app.route`` / ``@bp.route``
  (absent → ``GET``); Flask 2.0 ``@app.get`` / ``@app.post`` shortcuts are also
  supported;
- path params use the ``<int:user_id>`` / ``<user_id>`` angle syntax (the
  provider normalizer learned ``<…>`` for this);
- prefixes come from ``Blueprint(url_prefix="/api")`` and the route's full path
  is ``register_blueprint`` url_prefix (override) **or** the blueprint's own
  url_prefix — Flask *replaces*, it does not stack (unlike FastAPI's additive
  ``include_router``).

Confidence (DEC-045): an **app** route with a literal path is **EXTRACTED**; a
**blueprint** route is **INFERRED** (its external path depends on registration,
resolved by name across files).
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
    keyword_arg_node,
    keyword_arg_value,
    rightmost_name,
    string_list_values,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"flask", b"Flask", b"Blueprint")
_FACTORIES = {"Flask": "app", "Blueprint": "blueprint"}


class _Route(NamedTuple):
    object_name: str
    verbs: tuple[str, ...]
    raw_path: str
    symbol_id: str
    line: int


class _FileScan(NamedTuple):
    objects: dict[str, tuple[str, str]]  # name -> (kind 'app'|'blueprint', own_prefix)
    routes: list[_Route]
    mounts: list[tuple[str, str | None]]  # (blueprint_name, override_prefix or None)


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _collect_object(assign: Node, src: bytes, objects: dict[str, tuple[str, str]]) -> None:
    left = assign.child_by_field_name("left")
    right = assign.child_by_field_name("right")
    if left is None or right is None or left.type != "identifier" or right.type != "call":
        return
    fn = right.child_by_field_name("function")
    kind = _FACTORIES.get(rightmost_name(fn, src) or "") if fn is not None else None
    if kind is None:
        return
    name = src[left.start_byte : left.end_byte].decode("utf-8", "replace")
    args = right.child_by_field_name("arguments")
    prefix = (keyword_arg_value(args, "url_prefix", src) or "") if args is not None else ""
    objects[name] = (kind, prefix)


def _collect_mount(call: Node, src: bytes, mounts: list[tuple[str, str | None]]) -> None:
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return
    attr = fn.child_by_field_name("attribute")
    if attr is None or src[attr.start_byte : attr.end_byte] != b"register_blueprint":
        return
    args = call.child_by_field_name("arguments")
    if args is None:
        return
    bp_arg = next((c for c in args.children if c.type in ("identifier", "attribute")), None)
    if bp_arg is None:
        return
    name = rightmost_name(bp_arg, src)
    if name is None:
        return
    mounts.append((name, keyword_arg_value(args, "url_prefix", src)))


def _decorator_verbs_path(call: Node, src: bytes) -> tuple[str, tuple[str, ...] | None]:
    """Return ``(object_name, verbs)`` data for a Flask route decorator call.
    ``verbs`` is ``None`` when the decorator isn't a route (``.route`` or a verb
    shortcut on a recognised object)."""
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return "", None
    attr_node = fn.child_by_field_name("attribute")
    obj_node = fn.child_by_field_name("object")
    if attr_node is None or obj_node is None:
        return "", None
    attr = src[attr_node.start_byte : attr_node.end_byte].decode("utf-8", "replace")
    object_name = rightmost_name(obj_node, src) or ""
    args = call.child_by_field_name("arguments")
    if attr == "route":
        if args is None:
            return object_name, None
        methods_node = keyword_arg_node(args, "methods", src)
        verbs = (
            tuple(
                v.lower() for v in string_list_values(methods_node, src) if v.lower() in HTTP_VERBS
            )
            if methods_node is not None
            else ()
        )
        return object_name, verbs or ("get",)  # @route with no methods → GET
    if attr.lower() in HTTP_VERBS:
        return object_name, (attr.lower(),)
    return object_name, None


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
        object_name, verbs = _decorator_verbs_path(call, src)
        if not verbs:
            continue
        args = call.child_by_field_name("arguments")
        raw_path = first_positional_string(args, src) if args is not None else None
        if raw_path is None:
            continue
        routes.append(_Route(object_name, verbs, raw_path, symbol_id, name_node.start_point[0]))


def _scan_file(rel_path: str, root: Node, src: bytes) -> _FileScan:
    objects: dict[str, tuple[str, str]] = {}
    routes: list[_Route] = []
    mounts: list[tuple[str, str | None]] = []
    for node in _walk(root):
        if node.type == "assignment":
            _collect_object(node, src, objects)
        elif node.type == "call":
            _collect_mount(node, src, mounts)
        elif node.type == "decorated_definition":
            _collect_routes(rel_path, node, src, routes)
    return _FileScan(objects, routes, mounts)


def extract_flask_providers(ctx: ContractContext) -> list[Contract]:
    scans: list[tuple[str, _FileScan]] = []
    # blueprint name -> set of override prefixes seen at register_blueprint sites
    # (a member of None means "registered with no url_prefix override").
    mounts_by_name: dict[str, set[str | None]] = {}
    for rel_path, src, root in iter_candidate_files(ctx, languages=("python",), markers=_MARKERS):
        scan = _scan_file(rel_path, root, src)
        for name, override in scan.mounts:
            mounts_by_name.setdefault(name, set()).add(override)
        scans.append((rel_path, scan))

    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, scan in scans:
        for route in scan.routes:
            obj = scan.objects.get(route.object_name)
            if obj is None:
                continue
            kind, own_prefix = obj
            if kind == "app":
                prefixes: list[str] = [own_prefix]
                confidence = Confidence.EXTRACTED
            else:
                overrides = mounts_by_name.get(route.object_name)
                # Flask replaces: an override url_prefix wins; else the blueprint's own.
                prefixes = (
                    sorted({ov if ov is not None else own_prefix for ov in overrides})
                    if overrides
                    else [own_prefix]
                )
                confidence = Confidence.INFERRED
            for prefix in prefixes:
                for verb in route.verbs:
                    raw = prefix + route.raw_path
                    normalized = normalize_provider_path(raw)
                    if is_noise_path(normalized):
                        continue
                    contract_id = http_contract_id(verb, normalized)
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
                            evidence=f"flask @{route.object_name}.route({route.raw_path!r})",
                            protocol="http",
                            method=verb.upper(),
                            normalized_path=normalized,
                            raw_path=raw,
                            framework="flask",
                            rel_path=rel_path,
                            line=route.line,
                        )
                    )
    return contracts
