"""JAX-RS / Jakarta REST route-provider extractor (DEC-062, v0.5 Step 6).

A JAX-RS resource class carries a class-level ``@Path("resource")`` and methods
annotated with ``@GET``/``@POST``/``@PUT``/``@DELETE`` (+ an optional method-level
``@Path("sub")``)::

    @Path("/owners")
    public class OwnerResource {
        @GET                       public List<Owner> list() {}
        @GET @Path("/{id}")        public Owner get() {}
        @POST                      public void create() {}
    }

Route = class ``@Path`` + method ``@Path`` → ``http::<VERB>::<path>``. **Enclosing-class
guard** (Spring precedent): a verb annotation counts only inside an ``@Path`` class.
Both literals → EXTRACTED. Modeled on the Spring provider (Java annotations, class
prefix + method route).

Deferred (DEC-062): ``@ApplicationPath`` app-prefix nesting; sub-resource locators
(a method returning a sub-resource class); ``@Produces``/``@Consumes`` content
negotiation; a ``@Path`` value that is a constant/computed expression.
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

_MARKERS = (b"javax.ws.rs", b"jakarta.ws.rs", b"@Path")
_VERB_ANNOTATIONS = {
    "GET": "get",
    "POST": "post",
    "PUT": "put",
    "DELETE": "delete",
    "PATCH": "patch",
}


class _Route(NamedTuple):
    verbs: tuple[str, ...]
    raw_path: str
    symbol_id: str
    line: int


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


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


def _path_value(anno: Node, src: bytes) -> str:
    """The literal value of an ``@Path("...")`` annotation (positional or
    ``value=``), or ``""``."""
    args = next((c for c in anno.children if c.type == "annotation_argument_list"), None)
    if args is None:
        return ""
    for child in args.children:
        if child.type == "string_literal":
            return java_string_literal(child, src) or ""
        if child.type == "element_value_pair":
            key = child.child_by_field_name("key")
            value = child.child_by_field_name("value")
            if (
                key is not None
                and value is not None
                and _text(key, src) == "value"
                and value.type == "string_literal"
            ):
                return java_string_literal(value, src) or ""
    return ""


def _class_path(class_node: Node, src: bytes) -> str | None:
    """The class-level ``@Path`` value (``""`` for a bare ``@Path``), or ``None`` when
    the class has no ``@Path`` at all — the enclosing-class guard."""
    modifiers = next((c for c in class_node.children if c.type == "modifiers"), None)
    for anno in _annotations(modifiers):
        if _anno_name(anno, src) == "Path":
            return _path_value(anno, src)
    return None


def _join(prefix: str, path: str) -> str:
    parts = [p.strip("/") for p in (prefix, path) if p.strip("/")]
    return "/" + "/".join(parts) if parts else "/"


def _method_route(method: Node, src: bytes, rel_path: str) -> _Route | None:
    modifiers = next((c for c in method.children if c.type == "modifiers"), None)
    name_node = method.child_by_field_name("name")
    if name_node is None:
        return None
    verbs: list[str] = []
    method_path = ""
    for anno in _annotations(modifiers):
        anno_name = _anno_name(anno, src)
        if anno_name in _VERB_ANNOTATIONS:
            verbs.append(_VERB_ANNOTATIONS[anno_name])
        elif anno_name == "Path":
            method_path = _path_value(anno, src) or method_path
    if not verbs:
        return None
    parent = _parent_chain(name_node, "java")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return _Route(tuple(verbs), method_path, f"{rel_path}::{qn_local}", name_node.start_point[0])


def extract_jaxrs_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=("java",), markers=_MARKERS):
        for node in _walk(root):
            if node.type != "class_declaration":
                continue
            class_path = _class_path(node, src)
            if class_path is None:
                continue  # not a JAX-RS resource — enclosing-class guard
            body = next((c for c in node.children if c.type == "class_body"), None)
            if body is None:
                continue
            for member in body.children:
                if member.type != "method_declaration":
                    continue
                route = _method_route(member, src, rel_path)
                if route is None:
                    continue
                normalized = normalize_provider_path(_join(class_path, route.raw_path))
                if is_noise_path(normalized):
                    continue
                for verb in route.verbs:
                    contract_id = http_contract_id(verb, normalized)
                    if (contract_id, route.symbol_id) in seen:
                        continue
                    seen.add((contract_id, route.symbol_id))
                    contracts.append(
                        Contract(
                            role=ContractRole.PROVIDER,
                            contract_id=contract_id,
                            symbol_id=route.symbol_id,
                            confidence=Confidence.EXTRACTED,
                            evidence=f"jaxrs {route.symbol_id.rsplit('::', 1)[-1]} {verb.upper()}",
                            protocol="http",
                            method=verb.upper(),
                            normalized_path=normalized,
                            raw_path=_join(class_path, route.raw_path),
                            framework="jaxrs",
                            rel_path=rel_path,
                            line=route.line,
                        )
                    )
    return contracts
