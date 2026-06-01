"""Spring MVC route-provider extractor (DEC-045, v0.4 Item F — Java).

Spring controllers annotate methods with ``@GetMapping``/``@PostMapping``/… (or
``@RequestMapping(method=…)``) and optionally carry a class-level
``@RequestMapping`` path prefix. Unlike FastAPI routers / Express, the prefix is
**in the same class** as the method — so a literal-path Spring route is fully
determined syntactically → **EXTRACTED** (class prefix + method path, both
literals). A computed/constant path is dropped (DEC-037 posture).

Deferred (documented): interface→controller route inheritance (a controller
implementing an annotated interface — cross-file, harder); ``@RequestMapping``
``value``/``path`` *array* of multiple paths beyond the first; JAX-RS ``@Path``.
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
from forensic_deepdive.contracts.http.scan import iter_candidate_files, java_string_literal
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"Mapping",)
_VERB_ANNOTATIONS = {
    "GetMapping": "get",
    "PostMapping": "post",
    "PutMapping": "put",
    "DeleteMapping": "delete",
    "PatchMapping": "patch",
}


class _Route(NamedTuple):
    verbs: tuple[str, ...]
    raw_path: str
    symbol_id: str
    line: int


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _annotations(modifiers: Node | None) -> list[Node]:
    if modifiers is None:
        return []
    return [c for c in modifiers.children if c.type in ("annotation", "marker_annotation")]


def _anno_name(anno: Node, src: bytes) -> str:
    name = anno.child_by_field_name("name")
    if name is not None:
        return _text(name, src)
    ident = next((c for c in anno.children if c.type == "identifier"), None)
    return _text(ident, src) if ident is not None else ""


def _arg_list(anno: Node) -> Node | None:
    return next((c for c in anno.children if c.type == "annotation_argument_list"), None)


def _anno_path(anno: Node, src: bytes) -> str:
    """The route path declared by an annotation: a positional string literal, or
    the ``value=``/``path=`` element. ``""`` when none (e.g. bare
    ``@PostMapping`` → maps to the class prefix root)."""
    args = _arg_list(anno)
    if args is None:
        return ""
    for child in args.children:
        if child.type == "string_literal":
            return java_string_literal(child, src) or ""
        if child.type == "element_value_pair":
            key = child.child_by_field_name("key")
            value = child.child_by_field_name("value")
            if key is None or value is None:
                continue
            if _text(key, src) in ("value", "path") and value.type == "string_literal":
                return java_string_literal(value, src) or ""
    return ""


def _request_mapping_verbs(anno: Node, src: bytes) -> tuple[str, ...]:
    """Verbs from a ``@RequestMapping`` ``method=`` element (``RequestMethod.GET``
    or ``{RequestMethod.GET, RequestMethod.POST}``). Empty → method-agnostic."""
    args = _arg_list(anno)
    if args is None:
        return ()
    verbs: list[str] = []
    for child in args.children:
        if child.type != "element_value_pair":
            continue
        key = child.child_by_field_name("key")
        value = child.child_by_field_name("value")
        if key is None or value is None or _text(key, src) != "method":
            continue
        targets = (
            [c for c in value.children if c.type == "field_access"]
            if value.type == "element_value_array_initializer"
            else [value]
        )
        for tgt in targets:
            if tgt.type == "field_access":
                verb = _text(tgt, src).rsplit(".", 1)[-1].lower()
                if verb in {"get", "post", "put", "delete", "patch", "head", "options"}:
                    verbs.append(verb)
    return tuple(verbs)


def _class_prefix(class_node: Node, src: bytes) -> str:
    modifiers = next((c for c in class_node.children if c.type == "modifiers"), None)
    for anno in _annotations(modifiers):
        if _anno_name(anno, src) == "RequestMapping":
            return _anno_path(anno, src)
    return ""


def _method_route(method: Node, src: bytes, class_name: str, rel_path: str) -> _Route | None:
    modifiers = next((c for c in method.children if c.type == "modifiers"), None)
    name_node = method.child_by_field_name("name")
    if name_node is None:
        return None
    verbs: list[str] = []
    path = ""
    for anno in _annotations(modifiers):
        anno_name = _anno_name(anno, src)
        if anno_name in _VERB_ANNOTATIONS:
            verbs.append(_VERB_ANNOTATIONS[anno_name])
            path = _anno_path(anno, src) or path
        elif anno_name == "RequestMapping":
            rm_verbs = _request_mapping_verbs(anno, src)
            verbs.extend(rm_verbs or ("*",))  # no method= → method-agnostic
            path = _anno_path(anno, src) or path
    if not verbs:
        return None
    parent = _parent_chain(name_node, "java")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return _Route(tuple(verbs), path, f"{rel_path}::{qn_local}", name_node.start_point[0])


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def extract_spring_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=("java",), markers=_MARKERS):
        for node in _walk(root):
            if node.type != "class_declaration":
                continue
            prefix = _class_prefix(node, src)
            body = next((c for c in node.children if c.type == "class_body"), None)
            class_name_node = node.child_by_field_name("name")
            class_name = _text(class_name_node, src) if class_name_node is not None else ""
            if body is None:
                continue
            for member in body.children:
                if member.type != "method_declaration":
                    continue
                route = _method_route(member, src, class_name, rel_path)
                if route is None:
                    continue
                normalized = normalize_provider_path(prefix + route.raw_path)
                if is_noise_path(normalized):
                    continue
                for verb in route.verbs:
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
                            confidence=Confidence.EXTRACTED,  # prefix + path both literal
                            evidence=f"spring {route.symbol_id.rsplit('::', 1)[-1]} {verb.upper()}",
                            protocol="http",
                            method=verb.upper(),
                            normalized_path=normalized,
                            raw_path=prefix + route.raw_path,
                            framework="spring",
                            rel_path=rel_path,
                            line=route.line,
                        )
                    )
    return contracts
