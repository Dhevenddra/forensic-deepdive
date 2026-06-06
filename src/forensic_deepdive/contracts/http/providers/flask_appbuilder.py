"""Flask-AppBuilder route-provider extractor (DEC-056, v0.5 Step 1).

The other half of v0.4's Superset ``0 ROUTES_TO``: its backend is **Flask-
AppBuilder**, not bare Flask, so the ``@app.route`` provider located 1 of 276
endpoints. FAB is class-/convention-driven::

    class ChartRestApi(BaseSupersetModelRestApi):   # ModelRestApi/BaseApi lineage
        resource_name = "chart"                     # → base /api/v1/chart
        version = "v1"

        @expose("/<pk>/data/", methods=["GET"])
        def data(self, pk): ...

A FAB **API** route is ``/api/<version>/<base> + <@expose path>``. The class base
comes from an explicit ``route_base``/``base_route`` (used literally), else
``resource_name`` (→ ``/api/<version>/<resource_name>``), else the class name
(FAB convention — strip a trailing ``Api``/``RestApi``, lowercase). We model it
like the Spring provider (DEC-045): a class-level prefix joined with method-level
routes, the enclosing-class guard (an ``@expose`` route counts only inside a FAB
API class).

Confidence (DEC-046): an explicit ``route_base``/``resource_name`` prefix is a
syntactic fact → **EXTRACTED**; the class-name-derived prefix fallback is
**INFERRED**. A bare ``@expose`` (no ``methods=``) defaults to GET (the FAB
default). Computed paths/prefixes are dropped (DEC-037 posture).

Deferred (documented): the auto-generated CRUD routes a ``ModelRestApi`` serves
without an explicit ``@expose`` (``GET``/``POST`` ``/`` , ``GET``/``PUT``/
``DELETE`` ``/<pk>``) — synthesizing them is convention, not a syntactic fact,
and ``include_route_methods``/``exclude_route_methods`` can suppress them, so we
do not fabricate them; nested API namespaces beyond one prefix level.
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
    py_string_literal,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"ModelRestApi", b"BaseApi", b"@expose", b"flask_appbuilder")
_DEFAULT_VERSION = "v1"
# Class attributes that name the route base, in priority order.
_BASE_ATTRS = ("route_base", "base_route")


class _ApiClass(NamedTuple):
    prefix: str
    prefix_is_literal: bool  # explicit route_base/resource_name → EXTRACTED-grade


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _superclass_names(class_node: Node, src: bytes) -> list[str]:
    """The (rightmost) names of a class's bases: ``ModelRestApi`` from
    ``class X(ModelRestApi)`` or ``flask_appbuilder.api.ModelRestApi``."""
    supers = class_node.child_by_field_name("superclasses")
    if supers is None:
        return []
    names: list[str] = []
    for child in supers.children:
        if child.type == "identifier":
            names.append(_text(child, src))
        elif child.type == "attribute":
            attr = child.child_by_field_name("attribute")
            if attr is not None:
                names.append(_text(attr, src))
    return names


def _is_fab_api(super_names: list[str]) -> bool:
    """A FAB **API** base (gets the ``/api/<version>`` prefix): ``BaseApi`` /
    ``ModelRestApi`` or any intermediate ending ``Api``/``RestApi``
    (``BaseSupersetModelRestApi``). View bases (``BaseView``/``ModelView``) do
    not match — their HTML routes are not the SupersetClient join target."""
    return any(name.endswith("Api") or name.endswith("RestApi") for name in super_names)


def _class_string_attr(body: Node, name: str, src: bytes) -> str | None:
    """A class-level ``<name> = "literal"`` assignment value, or ``None``. The
    block child is the ``assignment`` directly (some grammars wrap it in an
    ``expression_statement`` — handle both)."""
    for stmt in body.children:
        if stmt.type == "assignment":
            assign: Node | None = stmt
        elif stmt.type == "expression_statement":
            assign = next((c for c in stmt.children if c.type == "assignment"), None)
        else:
            continue
        if assign is None:
            continue
        left = assign.child_by_field_name("left")
        right = assign.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier":
            continue
        if _text(left, src) == name and right.type == "string":
            return py_string_literal(right, src)
    return None


def _api_prefix(class_node: Node, body: Node, class_name: str, src: bytes) -> _ApiClass | None:
    """The FAB API route prefix for a class, or ``None`` when it isn't a FAB API.

    Priority: explicit ``route_base``/``base_route`` (literal, used as-is) →
    ``resource_name`` (→ ``/api/<version>/<resource_name>``) → class-name
    convention (INFERRED)."""
    if not _is_fab_api(_superclass_names(class_node, src)):
        return None
    version = _class_string_attr(body, "version", src) or _DEFAULT_VERSION
    for attr in _BASE_ATTRS:
        base = _class_string_attr(body, attr, src)
        if base is not None:
            return _ApiClass(base, True)
    resource = _class_string_attr(body, "resource_name", src)
    if resource is not None:
        return _ApiClass(f"/api/{version}/{resource}", True)
    # FAB convention: route base = class name minus a trailing Api/RestApi, lowered.
    derived = class_name
    for suffix in ("RestApi", "Api"):
        if derived.endswith(suffix):
            derived = derived[: -len(suffix)]
            break
    return _ApiClass(f"/api/{version}/{derived.lower()}", False)


def _string_seq_values(node: Node, src: bytes) -> list[str]:
    """Static string members of a ``list``/``tuple``/``set`` node
    (``["GET", "POST"]`` / ``("GET",)``), skipping computed members."""
    if node.type not in ("list", "tuple", "set"):
        return []
    out: list[str] = []
    for child in node.children:
        if child.type == "string":
            value = py_string_literal(child, src)
            if value is not None:
                out.append(value)
    return out


def _expose_verbs_path(call: Node, src: bytes) -> tuple[tuple[str, ...], str] | None:
    """``(verbs, path)`` for an ``@expose("/p", methods=[...])`` call, or ``None``
    when the path is absent/computed. No ``methods=`` → GET (the FAB default)."""
    args = call.child_by_field_name("arguments")
    if args is None:
        return None
    path = first_positional_string(args, src)
    if path is None:
        return None
    methods_node = keyword_arg_node(args, "methods", src)
    verbs = (
        tuple(v.lower() for v in _string_seq_values(methods_node, src) if v.lower() in HTTP_VERBS)
        if methods_node is not None
        else ()
    )
    return (verbs or ("get",)), path


def _expose_call(decorator: Node, src: bytes) -> Node | None:
    """The ``call`` node of an ``@expose(...)`` decorator, or ``None``."""
    call = next((c for c in decorator.children if c.type == "call"), None)
    if call is None:
        return None
    fn = call.child_by_field_name("function")
    if fn is None:
        return None
    name = fn if fn.type == "identifier" else fn.child_by_field_name("attribute")
    if name is not None and _text(name, src) == "expose":
        return call
    return None


def _method_symbol_id(definition: Node, src: bytes, rel_path: str) -> str | None:
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        return None
    parent = _parent_chain(name_node, "python")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return f"{rel_path}::{qn_local}"


def extract_flask_appbuilder_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=("python",), markers=_MARKERS):
        for node in _walk(root):
            if node.type != "class_definition":
                continue
            body = node.child_by_field_name("body")
            name_node = node.child_by_field_name("name")
            if body is None or name_node is None:
                continue
            api = _api_prefix(node, body, _text(name_node, src), src)
            if api is None:
                continue
            confidence = Confidence.EXTRACTED if api.prefix_is_literal else Confidence.INFERRED
            for member in body.children:
                if member.type != "decorated_definition":
                    continue
                definition = member.child_by_field_name("definition")
                if definition is None or definition.type != "function_definition":
                    continue
                symbol_id = _method_symbol_id(definition, src, rel_path)
                if symbol_id is None:
                    continue
                for child in member.children:
                    if child.type != "decorator":
                        continue
                    call = _expose_call(child, src)
                    if call is None:
                        continue
                    parsed = _expose_verbs_path(call, src)
                    if parsed is None:
                        continue
                    verbs, path = parsed
                    raw = api.prefix + path
                    normalized = normalize_provider_path(raw)
                    if is_noise_path(normalized):
                        continue
                    for verb in verbs:
                        contract_id = http_contract_id(verb, normalized)
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
                                evidence=f"fab @expose({path!r}) {verb.upper()}",
                                protocol="http",
                                method=verb.upper(),
                                normalized_path=normalized,
                                raw_path=raw,
                                framework="flask-appbuilder",
                                rel_path=rel_path,
                                line=definition.child_by_field_name("name").start_point[0],
                            )
                        )
    return contracts
