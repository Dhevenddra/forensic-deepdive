"""``.proto`` spec scan (DEC-060/061, v0.5 Step 5).

The gRPC analog of the OpenAPI spec pass (DEC-048): a ``.proto`` ``service X { rpc M
(Req) returns (Resp); }`` is the **contract**. We parse it with the **tree-sitter-proto
grammar already bundled in ``tree-sitter-language-pack``** (zero new runtime dep,
DEC-061 — the antlr4-backed ``proto-schema-parser`` is deferred behind a future
``[proto]`` extra) and emit one **spec-backed provider** ``Contract`` per rpc, with a
synthetic ``symbol_id`` (the ``.proto`` is not a code Symbol, so the HANDLES edge is
filtered out — but the Endpoint is emitted ``spec_backed=True``, upgrading any
servicer/stub join to EXTRACTED, exactly as an OpenAPI op does).

``.proto`` files aren't in the graph corpus (not a parsed source language), so this
walks ``repo_path`` directly — a deterministic sorted walk pruning the inventory
ignore-dirs, mirroring ``detect_spec_files``.
"""

from __future__ import annotations

import os
import posixpath
from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.grpc.normalize import grpc_contract_id, grpc_flat_module_id
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.inventory import DEFAULT_IGNORE_DIRS
from forensic_deepdive.static.parse import parse_source

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _detect_proto_files(repo_path: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in DEFAULT_IGNORE_DIRS
        ]
        for fn in filenames:
            if fn.endswith(".proto"):
                found.append(Path(dirpath) / fn)
    return sorted(found)


def _ident_child(node: Node, src: bytes) -> str | None:
    """The first ``identifier`` descendant's text (a ``service_name``/``rpc_name``
    wraps its identifier)."""
    for c in node.children:
        if c.type == "identifier":
            return _text(c, src)
    return None


def extract_proto_providers(ctx: ContractContext) -> list[Contract]:
    contracts: list[Contract] = []
    seen: set[str] = set()
    for path in _detect_proto_files(ctx.repo_path):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        try:
            rel_path = str(path.relative_to(ctx.repo_path)).replace(os.sep, "/")
        except ValueError:
            rel_path = path.name
        # DEC-068: protoc emits ``<protofile>_pb2_grpc`` next to the .proto — the module
        # identity both the servicer base and the stub ctor reference. Directory-qualified
        # (the generated module is a sibling), matching the flat-import resolution. (NOT a
        # .proto parse of ``package`` — the wire-path equivalence stays deferred.)
        module = grpc_flat_module_id(path.stem + "_pb2_grpc", posixpath.dirname(rel_path))
        root = parse_source(data, "proto").root_node
        for node in _walk(root):
            if node.type != "service":
                continue
            service = None
            for c in node.children:
                if c.type == "service_name":
                    service = _ident_child(c, data)
                    break
            if service is None:
                continue
            for c in node.children:
                if c.type != "rpc":
                    continue
                method = None
                for rc in c.children:
                    if rc.type == "rpc_name":
                        method = _ident_child(rc, data)
                        break
                if method is None:
                    continue
                contract_id = grpc_contract_id(module, service, method)
                if contract_id in seen:
                    continue
                seen.add(contract_id)
                contracts.append(
                    Contract(
                        role=ContractRole.PROVIDER,
                        contract_id=contract_id,
                        # Synthetic symbol — a .proto rpc is not a code Symbol, so
                        # the HANDLES edge filters out (spec-only), like OpenAPI.
                        symbol_id=f"{rel_path}::{service}.{method}",
                        confidence=Confidence.EXTRACTED,
                        evidence=f"proto rpc {service}.{method}",
                        protocol="grpc",
                        method=method,
                        normalized_path=f"{service}/{method}",
                        raw_path=f"{service}/{method}",
                        framework="grpc",
                        spec_backed=True,
                        rel_path=rel_path,
                        line=node.start_point[0],
                    )
                )
    return contracts


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))
