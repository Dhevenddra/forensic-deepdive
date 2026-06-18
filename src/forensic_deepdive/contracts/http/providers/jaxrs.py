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

**Sub-resource locators (DEC-066, v0.6 Step 3).** A ``@Path`` method with **no verb
annotation** is a *sub-resource locator* — it returns a resource object whose own
``@GET``/``@Path`` methods serve the routes under the locator's path::

    @Path("/")  class Bookstore {
        @Path("items/{id}/")  public Item getItem(...) { ... }   // locator → Item
    }
    class Item {                       // a sub-resource (no class @Path)
        @GET  public Item getXml() {}  // → GET /items/{id}/  (handler = Item.getXml)
    }

We resolve the locator's declared **return type** to its class (the shared
``resolve_name_to_files`` ladder + a JAX-RS resource-class index for the node), then
recurse into that class's verb / nested-locator methods, concatenating the prefix.
Confidence (DEC-066): a return type resolving to **exactly one** concrete resource class
→ EXTRACTED (the return type is a declared concrete fact); **several** candidate classes
→ AMBIGUOUS (emit every candidate); an ``Object`` / unresolvable return → the locator is
emitted **unmatched** (an Endpoint at its path, no handler — never a guessed sub-route).

**Application prefix + content negotiation (DEC-073, v0.7 Step 2).** A
``@ApplicationPath("/api")`` class (the JAX-RS ``Application`` subclass) sets the servlet
mount path for the whole application — every resource path is relative to it, so we
prepend that one app prefix to every route (EXTRACTED — a literal app-wide fact).
``@Produces``/``@Consumes`` (class- or method-level, method overriding class) carry the
media type(s) as an Endpoint **property** (``Contract.content_type``) — **never part of the
key** (the DEC-057 version-property precedent: two methods differing only by media type are
the same logical Endpoint). ``MediaType.*`` constants are mapped to their media strings;
string-literal and braced-array forms are also read.

**Interface/abstract-return locators (DEC-073).** When a locator's return type is an
*interface* (not a concrete class in the resource index) we look for an intra-repo
``implements`` resolution: **exactly one** concrete implementer → recurse into it as
**INFERRED** (the DI-ladder precedent); zero or several → the locator stays an honest
**unmatched** Endpoint (never a guessed sub-route).

Deferred (DEC-062): a ``@Path`` value that is a constant/computed expression; multiple
distinct ``@ApplicationPath`` classes attributed per-resource (one app prefix is the norm —
several → no prefix applied, never a guess).
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
from forensic_deepdive.static.resolver import resolve_name_to_files
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
    "HEAD": "head",
    "OPTIONS": "options",
}

# DEC-073: JAX-RS ``MediaType`` constants → their media-type strings (content negotiation).
# A ``@Produces(MediaType.APPLICATION_JSON)`` carries the string; an unknown constant keeps
# its trailing identifier verbatim (honest — never invented).
_MEDIA_TYPE_CONSTANTS = {
    "APPLICATION_JSON": "application/json",
    "APPLICATION_XML": "application/xml",
    "APPLICATION_FORM_URLENCODED": "application/x-www-form-urlencoded",
    "APPLICATION_OCTET_STREAM": "application/octet-stream",
    "APPLICATION_SVG_XML": "application/svg+xml",
    "APPLICATION_ATOM_XML": "application/atom+xml",
    "MULTIPART_FORM_DATA": "multipart/form-data",
    "TEXT_PLAIN": "text/plain",
    "TEXT_HTML": "text/html",
    "TEXT_XML": "text/xml",
    "WILDCARD": "*/*",
}

# Return types that are never a sub-resource (so a @Path-no-verb method returning one is
# not treated as a locator). ``Object`` IS treated as a locator but is unresolvable →
# the locator is emitted unmatched (DEC-066 / invariant 2).
_NON_RESOURCE_RETURNS = frozenset(
    {
        "void",
        "Response",
        "String",
        "boolean",
        "int",
        "long",
        "double",
        "float",
        "char",
        "byte",
        "short",
    }
)
_MAX_SUBRESOURCE_DEPTH = 6


class _Route(NamedTuple):
    verbs: tuple[str, ...]
    raw_path: str
    symbol_id: str
    line: int
    content_type: str


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


def _application_path(class_node: Node, src: bytes) -> str | None:
    """The ``@ApplicationPath("/api")`` value on a JAX-RS ``Application`` subclass
    (``""`` for a bare annotation), or ``None`` when the class has no ``@ApplicationPath``
    (DEC-073). This is the servlet mount prefix for the whole application."""
    modifiers = next((c for c in class_node.children if c.type == "modifiers"), None)
    for anno in _annotations(modifiers):
        if _anno_name(anno, src) == "ApplicationPath":
            return _path_value(anno, src)
    return None


def _media_values(anno: Node, src: bytes) -> list[str]:
    """The media type(s) named by a ``@Produces``/``@Consumes`` annotation: a
    ``MediaType.*`` constant (mapped to its string), a string literal, or a braced array
    of either (DEC-073). Deterministic source order; unknown constants keep their trailing
    identifier verbatim (never invented)."""
    args = next((c for c in anno.children if c.type == "annotation_argument_list"), None)
    if args is None:
        return []
    values: list[str] = []

    def _from_node(node: Node) -> None:
        if node.type == "string_literal":
            lit = java_string_literal(node, src)
            if lit:
                values.append(lit)
        elif node.type == "field_access":
            field = node.child_by_field_name("field")
            ident = _text(field, src) if field is not None else _text(node, src).rsplit(".", 1)[-1]
            values.append(_MEDIA_TYPE_CONSTANTS.get(ident, ident))
        elif node.type == "identifier":
            ident = _text(node, src)
            values.append(_MEDIA_TYPE_CONSTANTS.get(ident, ident))

    for child in args.children:
        if child.type in ("string_literal", "field_access", "identifier"):
            _from_node(child)
        elif child.type == "element_value_array_initializer":
            for elem in child.children:
                _from_node(elem)
        elif child.type == "element_value_pair":  # value = ...
            value = child.child_by_field_name("value")
            if value is not None:
                if value.type == "element_value_array_initializer":
                    for elem in value.children:
                        _from_node(elem)
                else:
                    _from_node(value)
    return values


def _media_annotations(modifiers: Node | None, src: bytes) -> tuple[list[str], list[str]]:
    """``(@Produces values, @Consumes values)`` declared on *modifiers* (DEC-073)."""
    produces: list[str] = []
    consumes: list[str] = []
    for anno in _annotations(modifiers):
        name = _anno_name(anno, src)
        if name == "Produces":
            produces.extend(_media_values(anno, src))
        elif name == "Consumes":
            consumes.extend(_media_values(anno, src))
    return produces, consumes


def _format_content_type(produces: list[str], consumes: list[str]) -> str:
    """A stable display string: ``produces=a,b; consumes=c`` (omitting absent halves)."""
    parts: list[str] = []
    if produces:
        parts.append("produces=" + ",".join(produces))
    if consumes:
        parts.append("consumes=" + ",".join(consumes))
    return "; ".join(parts)


def _join(prefix: str, path: str) -> str:
    parts = [p.strip("/") for p in (prefix, path) if p.strip("/")]
    return "/" + "/".join(parts) if parts else "/"


def _method_route(
    method: Node, src: bytes, rel_path: str, class_ct: tuple[list[str], list[str]]
) -> _Route | None:
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
    # DEC-073: method-level @Produces/@Consumes override the class-level defaults
    # (JAX-RS content-negotiation semantics); a missing half falls back to the class.
    m_produces, m_consumes = _media_annotations(modifiers, src)
    c_produces, c_consumes = class_ct
    content_type = _format_content_type(m_produces or c_produces, m_consumes or c_consumes)
    parent = _parent_chain(name_node, "java")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return _Route(
        tuple(verbs),
        method_path,
        f"{rel_path}::{qn_local}",
        name_node.start_point[0],
        content_type,
    )


def _return_type_name(method: Node, src: bytes) -> str | None:
    """The base type name of a method's declared return type: ``Item`` →
    ``Item``; ``Class<Item>`` / ``List<Item>`` → the first type argument (``Item``);
    ``void``/array/qualified → ``None`` (not a simple resource type)."""
    t = method.child_by_field_name("type")
    if t is None:
        return None
    if t.type == "type_identifier":
        return _text(t, src)
    if t.type == "generic_type":
        targs = next((c for c in t.children if c.type == "type_arguments"), None)
        if targs is not None:
            arg = next((c for c in targs.children if c.type == "type_identifier"), None)
            if arg is not None:
                return _text(arg, src)
        base = next((c for c in t.children if c.type == "type_identifier"), None)
        return _text(base, src) if base is not None else None
    return None


def _method_locator(method: Node, src: bytes) -> str | None:
    """A sub-resource locator is a method with a ``@Path`` and **no** verb annotation
    that returns a resource-ish type. Returns the locator's ``@Path`` value (``""`` for
    a bare ``@Path``), or ``None`` when the method isn't a locator."""
    modifiers = next((c for c in method.children if c.type == "modifiers"), None)
    has_verb = False
    has_path = False
    path = ""
    for anno in _annotations(modifiers):
        anno_name = _anno_name(anno, src)
        if anno_name in _VERB_ANNOTATIONS:
            has_verb = True
        elif anno_name == "Path":
            has_path = True
            path = _path_value(anno, src)
    if has_verb or not has_path:
        return None
    rt = _return_type_name(method, src)
    if rt is None or rt in _NON_RESOURCE_RETURNS:
        return None
    return path


def _min_conf(a: Confidence, b: Confidence) -> Confidence:
    order = {Confidence.EXTRACTED: 2, Confidence.INFERRED: 1, Confidence.AMBIGUOUS: 0}
    return a if order[a] <= order[b] else b


class _Resolver(NamedTuple):
    """Inputs for resolving a locator return-type name to its resource class(es)."""

    imports: list  # ctx.imports
    defs_top_by_file: dict[str, set[str]]
    defs_top_by_lang: dict[str, dict[str, list[str]]]
    source_files_by_path: dict[str, str]
    class_index: dict[str, list[tuple[str, bytes, Node]]]  # simple name -> class nodes
    # DEC-073: simple interface name -> concrete classes that ``implements`` it.
    impl_index: dict[str, list[tuple[str, bytes, Node]]]


def _resolve_resource_class(
    return_name: str, rel_path: str, r: _Resolver
) -> tuple[list[tuple[str, bytes, Node]], str]:
    """Resolve a locator's return-type name to its resource class node(s) and the
    resolution *kind*: ``"direct"`` (a concrete class of that name — EXTRACTED-grade) or
    ``"implements"`` (the return is an interface with exactly one intra-repo implementer —
    INFERRED-grade, DEC-073). Uses the shared name resolver to scope to file(s) (DEC-059).
    Returns ``([], "none")`` for an unresolvable / multiply-implemented interface return →
    the caller emits an honest unmatched locator."""
    candidates = r.class_index.get(return_name, [])
    if candidates:
        resolved = resolve_name_to_files(
            return_name,
            rel_path,
            "java",
            r.imports,
            r.defs_top_by_file,
            r.defs_top_by_lang,
            r.source_files_by_path,
        )
        if resolved is not None:
            files = set(resolved[0])
            narrowed = [c for c in candidates if c[0] in files]
            if narrowed:
                return narrowed, "direct"
        return candidates, "direct"
    # No concrete class of that name → an interface/abstract return. Accept it only when a
    # single intra-repo class implements it (the DI-ladder precedent → INFERRED); zero or
    # several implementers stay unmatched (no guess).
    implementers = r.impl_index.get(return_name, [])
    if len(implementers) == 1:
        return implementers, "implements"
    return [], "none"


class _Emit(NamedTuple):
    contracts: list[Contract]
    seen: set[tuple[str, str]]


def _emit_route(
    emit: _Emit,
    verb: str,
    raw: str,
    symbol_id: str,
    conf: Confidence,
    rel_path: str,
    line: int,
    content_type: str = "",
) -> None:
    normalized = normalize_provider_path(raw)
    if is_noise_path(normalized):
        return
    contract_id = http_contract_id(verb, normalized)
    if (contract_id, symbol_id) in emit.seen:
        return
    emit.seen.add((contract_id, symbol_id))
    emit.contracts.append(
        Contract(
            role=ContractRole.PROVIDER,
            contract_id=contract_id,
            symbol_id=symbol_id,
            confidence=conf,
            evidence=f"jaxrs {symbol_id.rsplit('::', 1)[-1] or 'locator'} {verb.upper()}",
            protocol="http",
            method=verb.upper(),
            normalized_path=normalized,
            raw_path=raw,
            framework="jaxrs",
            rel_path=rel_path,
            line=line,
            content_type=content_type,
        )
    )


def _emit_class_routes(
    rel_path: str,
    src: bytes,
    class_node: Node,
    prefix: str,
    conf: Confidence,
    depth: int,
    visited: frozenset[tuple[str, str]],
    r: _Resolver,
    emit: _Emit,
) -> None:
    """Emit verb-method routes for *class_node* under *prefix*, and recurse into its
    sub-resource locators (resolving each locator's return type to a resource class)."""
    body = next((c for c in class_node.children if c.type == "class_body"), None)
    if body is None:
        return
    name_node = class_node.child_by_field_name("name")
    class_name = _text(name_node, src) if name_node is not None else ""
    visited = visited | {(rel_path, class_name)}
    # DEC-073: class-level @Produces/@Consumes are the per-method defaults.
    class_modifiers = next((c for c in class_node.children if c.type == "modifiers"), None)
    class_ct = _media_annotations(class_modifiers, src)
    for member in body.children:
        if member.type != "method_declaration":
            continue
        route = _method_route(member, src, rel_path, class_ct)
        if route is not None:  # a verb method → leaf route
            for verb in route.verbs:
                _emit_route(
                    emit,
                    verb,
                    _join(prefix, route.raw_path),
                    route.symbol_id,
                    conf,
                    rel_path,
                    route.line,
                    route.content_type,
                )
            continue
        locator_path = _method_locator(member, src)
        if locator_path is None:
            continue
        return_name = _return_type_name(member, src)
        loc_prefix = _join(prefix, locator_path)
        targets, via = (
            _resolve_resource_class(return_name, rel_path, r) if return_name else ([], "none")
        )
        if not targets or depth >= _MAX_SUBRESOURCE_DEPTH:
            # Object / interface-with-no-single-impl / unresolvable return (or recursion
            # cap) → honest unmatched locator: surface the routing boundary as an Endpoint
            # with no handler, never a guess.
            _emit_route(
                emit, "*", loc_prefix, "", Confidence.AMBIGUOUS, rel_path, member.start_point[0]
            )
            continue
        # A single concrete class → EXTRACTED; a single interface implementer → INFERRED
        # (DEC-073); several same-named concrete candidates → AMBIGUOUS (emit each).
        if len(targets) > 1:
            resolution_conf = Confidence.AMBIGUOUS
        elif via == "implements":
            resolution_conf = Confidence.INFERRED
        else:
            resolution_conf = Confidence.EXTRACTED
        sub_conf = _min_conf(conf, resolution_conf)
        for tgt_rel, tgt_src, tgt_node in targets:
            tgt_name_node = tgt_node.child_by_field_name("name")
            tgt_name = _text(tgt_name_node, tgt_src) if tgt_name_node is not None else ""
            if (tgt_rel, tgt_name) in visited:
                continue
            _emit_class_routes(
                tgt_rel, tgt_src, tgt_node, loc_prefix, sub_conf, depth + 1, visited, r, emit
            )


def _implemented_interfaces(class_node: Node, src: bytes) -> list[str]:
    """The simple names of the interfaces a class ``implements`` (DEC-073)."""
    supers = next((c for c in class_node.children if c.type == "super_interfaces"), None)
    if supers is None:
        return []
    type_list = next((c for c in supers.children if c.type == "type_list"), None)
    if type_list is None:
        return []
    names: list[str] = []
    for t in type_list.children:
        if t.type == "type_identifier":
            names.append(_text(t, src))
        elif t.type == "generic_type":
            base = next((c for c in t.children if c.type == "type_identifier"), None)
            if base is not None:
                names.append(_text(base, src))
    return names


def extract_jaxrs_providers(ctx: ContractContext) -> list[Contract]:
    files = list(iter_candidate_files(ctx, languages=("java",), markers=_MARKERS))
    # Index every JAX-RS-candidate class by simple name (for sub-resource resolution), the
    # interface→implementers map (DEC-073 interface-return locators), and the one app-wide
    # @ApplicationPath prefix.
    class_index: dict[str, list[tuple[str, bytes, Node]]] = {}
    impl_index: dict[str, list[tuple[str, bytes, Node]]] = {}
    app_paths: set[str] = set()
    for rel_path, src, root in files:
        for node in _walk(root):
            if node.type != "class_declaration":
                continue
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                entry = (rel_path, src, node)
                class_index.setdefault(_text(name_node, src), []).append(entry)
                for iface in _implemented_interfaces(node, src):
                    impl_index.setdefault(iface, []).append(entry)
            app_path = _application_path(node, src)
            if app_path is not None:
                app_paths.add(app_path)
    # The servlet mount prefix: exactly one @ApplicationPath is the JAX-RS norm. None → no
    # prefix; several distinct → unattributable → no prefix (never a guess) — DEC-073.
    app_prefix = next(iter(app_paths)) if len(app_paths) == 1 else ""
    # Top-level def name indexes for the shared resolver (Java types).
    defs_top_by_file: dict[str, set[str]] = {}
    defs_top_by_lang: dict[str, dict[str, list[str]]] = {}
    for t in ctx.tags:
        if t.kind != "def" or t.parent:
            continue
        defs_top_by_file.setdefault(t.rel_path, set()).add(t.name)
        defs_top_by_lang.setdefault(t.language, {}).setdefault(t.name, []).append(t.rel_path)
    r = _Resolver(
        ctx.imports,
        defs_top_by_file,
        defs_top_by_lang,
        ctx.source_files_by_path,
        class_index,
        impl_index,
    )

    emit = _Emit([], set())
    for rel_path, src, root in files:
        for node in _walk(root):
            if node.type != "class_declaration":
                continue
            class_path = _class_path(node, src)
            if class_path is None:
                continue  # not a root JAX-RS resource — enclosing-class guard
            _emit_class_routes(
                rel_path,
                src,
                node,
                _join(app_prefix, class_path),
                Confidence.EXTRACTED,
                0,
                frozenset(),
                r,
                emit,
            )
    return emit.contracts
