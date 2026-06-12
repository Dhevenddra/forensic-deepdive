"""NestJS route-provider extractor (DEC-062, v0.5 Step 6 — framework breadth).

NestJS controllers carry a class-level ``@Controller('prefix')`` and method-level
HTTP-verb decorators::

    @Controller('cats')
    export class CatsController {
      @Get(':id')   findOne() {}
      @Post()       create() {}
    }

Route = controller-prefix + method-path → ``http::<VERB>::<path>``. **Enclosing-class
guard** (the Spring/JAX-RS precedent): a verb decorator counts as a route only inside
a ``@Controller`` class — so a stray ``@Get`` elsewhere isn't a route. Both literals →
EXTRACTED (DEC-046). A computed path is dropped (DEC-037). Caller ``symbol_id`` via
``_parent_chain``.

Deferred (DEC-062): ``RouterModule.register([{path, module}])`` module-prefix nesting;
verb decorators with a non-literal path; non-controller route shapes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_provider_path,
)
from forensic_deepdive.contracts.http.scan import iter_candidate_files, js_string_literal
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"@Controller",)
_LANGS = ("typescript", "tsx")
_VERB_DECORATORS = {
    "Get": "get",
    "Post": "post",
    "Put": "put",
    "Delete": "delete",
    "Patch": "patch",
}


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _join(prefix: str, path: str) -> str:
    """Join a controller prefix + method path into a leading-slash route
    (``cats`` + ``:id`` → ``/cats/:id``; ``cats`` + ``""`` → ``/cats``)."""
    parts = [p.strip("/") for p in (prefix, path) if p.strip("/")]
    return "/" + "/".join(parts) if parts else "/"


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _decorator_call(decorator: Node) -> Node | None:
    return next((c for c in decorator.children if c.type == "call_expression"), None)


def _decorator_name_and_path(decorator: Node, src: bytes) -> tuple[str, str] | None:
    """``(name, path)`` for a ``@Name('path')`` decorator (path ``""`` when absent),
    or ``None`` if it isn't a call decorator."""
    call = _decorator_call(decorator)
    if call is None:
        return None
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "identifier":
        return None
    args = call.child_by_field_name("arguments")
    path = ""
    if args is not None:
        first = next((c for c in args.children if c.is_named), None)
        if first is not None and first.type in ("string", "template_string"):
            path = js_string_literal(first, src) or ""
    return _text(fn, src), path


def _preceding_decorators(node: Node, src: bytes) -> list[Node]:
    """Decorator siblings immediately preceding *node* among its parent's children."""
    parent = node.parent
    if parent is None:
        return []
    siblings = parent.children
    try:
        idx = next(i for i, c in enumerate(siblings) if c.id == node.id)
    except StopIteration:
        return []
    out: list[Node] = []
    for i in range(idx - 1, -1, -1):
        if siblings[i].type == "decorator":
            out.append(siblings[i])
        elif siblings[i].type in ("comment", "export"):
            continue
        else:
            break
    return out


def _controller_prefix(class_node: Node, src: bytes) -> str | None:
    """The ``@Controller('prefix')`` prefix (``""`` for a bare ``@Controller()``), or
    ``None`` when the class has no ``@Controller`` (the enclosing-class guard)."""
    for deco in _preceding_decorators(class_node, src):
        parsed = _decorator_name_and_path(deco, src)
        if parsed is not None and parsed[0] == "Controller":
            return parsed[1]
    return None


def extract_nestjs_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "class_declaration":
                continue
            prefix = _controller_prefix(node, src)
            if prefix is None:
                continue  # not a controller — enclosing-class guard
            body = next((c for c in node.children if c.type == "class_body"), None)
            if body is None:
                continue
            for member in body.children:
                if member.type != "method_definition":
                    continue
                name_node = member.child_by_field_name("name")
                if name_node is None:
                    continue
                for deco in _preceding_decorators(member, src):
                    parsed = _decorator_name_and_path(deco, src)
                    if parsed is None or parsed[0] not in _VERB_DECORATORS:
                        continue
                    verb = _VERB_DECORATORS[parsed[0]]
                    raw = _join(prefix, parsed[1])
                    normalized = normalize_provider_path(raw)
                    if is_noise_path(normalized):
                        continue
                    chain = _parent_chain(name_node, "typescript")
                    handler = _text(name_node, src)
                    symbol_id = (
                        f"{rel_path}::{chain}.{handler}" if chain else f"{rel_path}::{handler}"
                    )
                    contract_id = http_contract_id(verb, normalized)
                    if (contract_id, symbol_id) in seen:
                        continue
                    seen.add((contract_id, symbol_id))
                    contracts.append(
                        Contract(
                            role=ContractRole.PROVIDER,
                            contract_id=contract_id,
                            symbol_id=symbol_id,
                            confidence=Confidence.EXTRACTED,
                            evidence=f"nestjs {handler} {verb.upper()}",
                            protocol="http",
                            method=verb.upper(),
                            normalized_path=normalized,
                            raw_path=raw,
                            framework="nestjs",
                            rel_path=rel_path,
                            line=name_node.start_point[0],
                        )
                    )
    return contracts
