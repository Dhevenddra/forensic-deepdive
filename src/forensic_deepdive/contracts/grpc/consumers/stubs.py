"""gRPC stub-consumer extractor (DEC-060, v0.5 Step 5).

A Python gRPC client calls a remote method through a generated stub::

    stub = route_guide_pb2_grpc.RouteGuideStub(channel)   # bind: stub → RouteGuide
    feature = stub.GetFeature(point)                       # call → grpc::RouteGuide/GetFeature

Two passes per file: (1) collect ``<var> = <mod>.<Svc>Stub(...)`` bindings (var →
service, the ``Stub`` suffix stripped); (2) a ``<var>.<Method>(...)`` call on a bound
stub var → a consumer of ``grpc::<Svc>/<Method>`` (the ``CALLS_ENDPOINT`` side). The
literal both-sides join is EXTRACTED (and ``spec_backed`` if a ``.proto`` declares it).
Caller ``symbol_id`` via the reused ``_enclosing_symbol``.

Deferred (DEC-060): Go (``client.Method(ctx, req)`` on a ``NewXClient``) / Java stubs;
stubs bound as attributes (``self.stub = ...``) beyond the local-var shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.grpc.normalize import grpc_contract_id
from forensic_deepdive.contracts.http.consumers.py_requests import _enclosing_symbol, _walk
from forensic_deepdive.contracts.http.scan import iter_candidate_files, rightmost_name
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"Stub(", b"_pb2_grpc")
_LANGS = ("python",)
_SUFFIX = "Stub"


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _collect_stub_vars(root: Node, src: bytes) -> dict[str, str]:
    """Map ``<var> → <Service>`` for ``<var> = <mod>.<Svc>Stub(...)`` bindings."""
    stub_vars: dict[str, str] = {}
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier" or right.type != "call":
            continue
        fn = right.child_by_field_name("function")
        ctor = rightmost_name(fn, src) if fn is not None else None
        if ctor is not None and ctor.endswith(_SUFFIX) and len(ctor) > len(_SUFFIX):
            stub_vars[_text(left, src)] = ctor[: -len(_SUFFIX)]
    return stub_vars


def extract_stub_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        stub_vars = _collect_stub_vars(root, src)
        if not stub_vars:
            continue
        for node in _walk(root):
            if node.type != "call":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "attribute":
                continue
            obj = fn.child_by_field_name("object")
            attr = fn.child_by_field_name("attribute")
            if obj is None or attr is None or obj.type != "identifier":
                continue
            service = stub_vars.get(_text(obj, src))
            if service is None:
                continue
            method = _text(attr, src)
            contract_id = grpc_contract_id(service, method)
            symbol_id = _enclosing_symbol(node, src, rel_path)
            if (contract_id, symbol_id) in seen:
                continue
            seen.add((contract_id, symbol_id))
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=Confidence.EXTRACTED,
                    evidence=f"grpc stub {service}.{method}()",
                    protocol="grpc",
                    method=method,
                    normalized_path=f"{service}/{method}",
                    raw_path=f"{service}/{method}",
                    framework="grpc",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
