"""gRPC servicer-provider extractor (DEC-060, v0.5 Step 5).

A Python gRPC server implements a service by subclassing the generated
``<Svc>Servicer`` base and defining one method per rpc::

    class RouteGuideServicer(route_guide_pb2_grpc.RouteGuideServicer):
        def GetFeature(self, request, context):
            ...

Each such method is a *provider* of ``grpc::<Svc>/<Method>`` (the ``HANDLES`` side).
Service name = the base-class name minus the ``Servicer`` suffix; method = the
function name (skipping dunders/private). Handler ``symbol_id`` via ``_parent_chain``.
Both sides are literal facts → EXTRACTED-grade (and the ``.proto`` spec makes the
join EXTRACTED via ``spec_backed``).

Deferred (DEC-060): Go (``RegisterXServer``) / Java (``XGrpc.XImplBase``) servicers;
async servicers beyond the method-name shape.
"""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.grpc.normalize import (
    grpc_contract_id,
    grpc_module_alias_table,
    grpc_resolve_module,
)
from forensic_deepdive.contracts.http.scan import iter_candidate_files, rightmost_name
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"Servicer",)
_LANGS = ("python",)
_SUFFIX = "Servicer"


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _servicer_base(class_node: Node, src: bytes) -> tuple[str, str] | None:
    """``(module_ref, service)`` for a class whose base is a ``<Svc>Servicer``, else
    ``None``. ``module_ref`` is the attribute object (``route_guide_pb2_grpc`` in
    ``route_guide_pb2_grpc.RouteGuideServicer``) or — for a bare ``from``-imported base —
    the base name itself (resolved to its module via the alias table)."""
    for c in class_node.children:
        if c.type != "argument_list":
            continue
        for base in c.children:
            if base.type == "attribute":
                obj = base.child_by_field_name("object")
                attr = base.child_by_field_name("attribute")
                if obj is None or attr is None:
                    continue
                name = _text(attr, src)
                if name.endswith(_SUFFIX) and len(name) > len(_SUFFIX):
                    return (rightmost_name(obj, src) or "", name[: -len(_SUFFIX)])
            elif base.type == "identifier":
                name = _text(base, src)
                if name.endswith(_SUFFIX) and len(name) > len(_SUFFIX):
                    return (name, name[: -len(_SUFFIX)])
    return None


def _method_symbol_id(definition: Node, src: bytes, rel_path: str) -> str | None:
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        return None
    parent = _parent_chain(name_node, "python")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return f"{rel_path}::{qn_local}"


def extract_servicer_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        dir_prefix = posixpath.dirname(rel_path)
        alias_table = grpc_module_alias_table(
            [imp for imp in ctx.imports if imp.rel_path == rel_path], rel_path
        )
        for node in _walk(root):
            if node.type != "class_definition":
                continue
            base = _servicer_base(node, src)
            if base is None:
                continue
            module_ref, service = base
            module = grpc_resolve_module(module_ref, alias_table, dir_prefix)
            body = node.child_by_field_name("body")
            if body is None:
                continue
            for member in body.children:
                definition = (
                    member
                    if member.type == "function_definition"
                    else (
                        member.child_by_field_name("definition")
                        if member.type == "decorated_definition"
                        else None
                    )
                )
                if definition is None or definition.type != "function_definition":
                    continue
                name_node = definition.child_by_field_name("name")
                if name_node is None:
                    continue
                method = _text(name_node, src)
                if method.startswith("_"):  # skip dunders / private helpers
                    continue
                symbol_id = _method_symbol_id(definition, src, rel_path)
                if symbol_id is None:
                    continue
                contract_id = grpc_contract_id(module, service, method)
                if (contract_id, symbol_id) in seen:
                    continue
                seen.add((contract_id, symbol_id))
                contracts.append(
                    Contract(
                        role=ContractRole.PROVIDER,
                        contract_id=contract_id,
                        symbol_id=symbol_id,
                        confidence=Confidence.EXTRACTED,
                        evidence=f"grpc servicer {module}.{service}.{method}",
                        protocol="grpc",
                        method=method,
                        normalized_path=f"{service}/{method}",
                        raw_path=f"{service}/{method}",
                        framework="grpc",
                        rel_path=rel_path,
                        line=name_node.start_point[0],
                    )
                )
    return contracts
