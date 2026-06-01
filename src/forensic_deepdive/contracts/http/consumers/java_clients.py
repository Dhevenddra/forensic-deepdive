"""Java HTTP-client consumer extractors (DEC-046, v0.4 Item G — Java).

Three Java consumer shapes in one extractor (they share the Java re-parse and the
``RestTemplate``/``WebClient``/``FeignClient`` marker set):

1. **RestTemplate** — ``restTemplate.getForObject(url, …)`` / ``postForObject`` /
   ``exchange(url, HttpMethod.DELETE, …)`` (verb from the ``HttpMethod`` arg) — a
   method call on an HTTP-ish receiver, URL = first arg.
2. **WebClient / RestClient (fluent)** — ``webClient.get().uri(url)…`` — the verb
   is the ``.get()``/``.post()`` call, the URL is the ``.uri(url)`` argument.
3. **OpenFeign** — ``@FeignClient`` interface methods annotated ``@GetMapping("/x")``
   (Spring-Cloud style, reusing the Spring annotation reader) or
   ``@RequestLine("POST /x")`` (raw Feign). The interface method *is* the call site
   (``UserFeign.get``). This pre-stages v0.5 service-to-service joins — a Feign
   client usually has no in-repo provider, so it emits CALLS_ENDPOINT alone.

A computed URL (string concatenation, bare variable) is dropped. Confidence:
literal URL = EXTRACTED, template/param/numeric-normalized = INFERRED. Caller
``symbol_id`` is the enclosing Java method (``_parent_chain`` → ``Class.method`` /
``Interface.method``), or the file ``<module>``.
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
from forensic_deepdive.contracts.http.providers.spring import (
    _VERB_ANNOTATIONS,
    _anno_name,
    _anno_path,
    _annotations,
)
from forensic_deepdive.contracts.http.scan import (
    HTTP_VERBS,
    iter_candidate_files,
    java_string_literal,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"RestTemplate", b"WebClient", b"RestClient", b"FeignClient", b"RequestLine")
_LANGS = ("java",)
_MODULE = "<module>"

# RestTemplate method → verb (URL is the first positional argument).
_RESTTEMPLATE_METHODS = {
    "getforobject": "get",
    "getforentity": "get",
    "postforobject": "post",
    "postforentity": "post",
    "postforlocation": "post",
    "put": "put",
    "delete": "delete",
    "patchforobject": "patch",
}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _httpish(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in ("rest", "template", "client", "http", "webclient"))


def _positional(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    return [c for c in args.children if c.is_named] if args is not None else []


def _enclosing_symbol(node: Node, src: bytes, rel_path: str) -> str:
    """Nearest enclosing Java method's qualified id, or the file ``<module>``."""
    cur = node.parent
    while cur is not None:
        if cur.type == "method_declaration":
            name_node = cur.child_by_field_name("name")
            if name_node is not None:
                parent = _parent_chain(name_node, "java")
                name = _text(name_node, src)
                qn_local = f"{parent}.{name}" if parent else name
                return f"{rel_path}::{qn_local}"
        cur = cur.parent
    return f"{rel_path}::{_MODULE}"


def _method_call_url_verb(node: Node, src: bytes) -> tuple[str, Node] | None:
    """``(verb, url_node)`` for a RestTemplate or fluent WebClient/RestClient call,
    or ``None``. ``node`` is a ``method_invocation``."""
    obj = node.child_by_field_name("object")
    name_node = node.child_by_field_name("name")
    if obj is None or name_node is None:
        return None
    method = _text(name_node, src).lower()
    pos = _positional(node)

    # --- fluent: <receiver>.<verb>().uri(url) ------------------------------
    if method == "uri" and obj.type == "method_invocation" and pos:
        verb_node = obj.child_by_field_name("name")
        recv = obj.child_by_field_name("object")
        if verb_node is None or recv is None or recv.type != "identifier":
            return None
        verb = _text(verb_node, src).lower()
        if verb in HTTP_VERBS and _httpish(_text(recv, src)):
            return verb, pos[0]
        return None

    # --- RestTemplate: <receiver>.getForObject(url, …) ---------------------
    if obj.type != "identifier" or not _httpish(_text(obj, src)) or not pos:
        return None
    if method == "exchange":
        # exchange(url, HttpMethod.DELETE, …) — verb from the 2nd arg
        if len(pos) < 2:
            return None
        verb_arg = pos[1]
        if verb_arg.type != "field_access":
            return None
        verb = _text(verb_arg, src).rsplit(".", 1)[-1].lower()
        if verb not in HTTP_VERBS:
            return None
        return verb, pos[0]
    if method in _RESTTEMPLATE_METHODS:
        return _RESTTEMPLATE_METHODS[method], pos[0]
    return None


def _feign_route(method_decl: Node, src: bytes, prefix: str) -> tuple[str, str] | None:
    """``(verb, raw_path)`` for an OpenFeign interface method, or ``None``.

    Reads a Spring ``@GetMapping("/x")``-family annotation, or a raw Feign
    ``@RequestLine("POST /x")``. ``prefix`` is the interface-level
    ``@RequestMapping`` path."""
    modifiers = next((c for c in method_decl.children if c.type == "modifiers"), None)
    for anno in _annotations(modifiers):
        anno_name = _anno_name(anno, src)
        if anno_name in _VERB_ANNOTATIONS:
            return _VERB_ANNOTATIONS[anno_name], prefix + _anno_path(anno, src)
        if anno_name == "RequestLine":
            line = _anno_path(anno, src)  # "POST /api/users"
            head, _, tail = line.partition(" ")
            if head.lower() in HTTP_VERBS and tail:
                return head.lower(), prefix + tail
    return None


def _interface_prefix(iface: Node, src: bytes) -> str:
    modifiers = next((c for c in iface.children if c.type == "modifiers"), None)
    for anno in _annotations(modifiers):
        if _anno_name(anno, src) == "RequestMapping":
            return _anno_path(anno, src)
    return ""


def _confidence(normalized: str) -> Confidence:
    """EXTRACTED for a fully-literal path; INFERRED once a param/numeric segment
    was generalized to ``{param}``."""
    return Confidence.EXTRACTED if "{param}" not in normalized else Confidence.INFERRED


def extract_java_client_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type == "method_invocation":
                resolved = _method_call_url_verb(node, src)
                if resolved is None:
                    continue
                verb, url_node = resolved
                raw_url = java_string_literal(url_node, src)
                framework = "java-http-client"
                line = node.start_point[0]
                symbol_id = _enclosing_symbol(node, src, rel_path)
            elif node.type == "interface_declaration":
                # OpenFeign: handled below per-method (not as a single node)
                _feign_interface(node, src, rel_path, seen, contracts)
                continue
            else:
                continue
            if raw_url is None:
                continue
            normalized = normalize_consumer_path(raw_url)
            if is_noise_path(normalized):
                continue
            contract_id = http_contract_id(verb, normalized)
            key = (contract_id, symbol_id)
            if key in seen:
                continue
            seen.add(key)
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=_confidence(normalized),
                    evidence=f"{framework} {verb}({raw_url!r})",
                    protocol="http",
                    method=verb.upper(),
                    normalized_path=normalized,
                    raw_path=raw_url,
                    framework=framework,
                    rel_path=rel_path,
                    line=line,
                )
            )
    return contracts


def _feign_interface(
    iface: Node,
    src: bytes,
    rel_path: str,
    seen: set[tuple[str, str]],
    contracts: list[Contract],
) -> None:
    prefix = _interface_prefix(iface, src)
    body = next((c for c in iface.children if c.type == "interface_body"), None)
    if body is None:
        return
    for member in body.children:
        if member.type != "method_declaration":
            continue
        route = _feign_route(member, src, prefix)
        if route is None:
            continue
        verb, raw_path = route
        normalized = normalize_consumer_path(raw_path)
        if is_noise_path(normalized):
            continue
        name_node = member.child_by_field_name("name")
        if name_node is None:
            continue
        parent = _parent_chain(name_node, "java")
        name = _text(name_node, src)
        qn_local = f"{parent}.{name}" if parent else name
        symbol_id = f"{rel_path}::{qn_local}"
        contract_id = http_contract_id(verb, normalized)
        key = (contract_id, symbol_id)
        if key in seen:
            continue
        seen.add(key)
        contracts.append(
            Contract(
                role=ContractRole.CONSUMER,
                contract_id=contract_id,
                symbol_id=symbol_id,
                confidence=_confidence(normalized),
                evidence=f"feign {qn_local} {verb.upper()}",
                protocol="http",
                method=verb.upper(),
                normalized_path=normalized,
                raw_path=raw_path,
                framework="openfeign",
                rel_path=rel_path,
                line=name_node.start_point[0],
            )
        )
