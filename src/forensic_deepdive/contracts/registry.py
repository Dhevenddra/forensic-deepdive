"""Protocol registry for cross-boundary contracts (DEC-043).

Maps a protocol to its ``key_builder`` plus the provider/consumer extractors
that mine :class:`~forensic_deepdive.contracts.base.Contract` records from the
parsed repo. HTTP is registered in v0.4 (its extractors land in Items F/G, so
its lists start empty); gRPC and topic key-builders are **stubbed
``NotImplementedError``** so the v0.5 seam is a visible, typed contract rather
than a future guess (KICKOFF §5.1: one abstraction, not three).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from forensic_deepdive.contracts.base import Contract
from forensic_deepdive.contracts.http.normalize import http_contract_id
from forensic_deepdive.contracts.mcp.normalize import mcp_contract_id
from forensic_deepdive.static.imports import Import
from forensic_deepdive.static.method_calls import MethodCall
from forensic_deepdive.static.tags import Tag


@dataclass(frozen=True, slots=True)
class ContractContext:
    """Everything an extractor sees. Additive: Items F/G read the subset they
    need (providers walk tags for route decorators; consumers walk method_calls
    + tags for fetch/axios sites)."""

    tags: list[Tag]
    imports: list[Import]
    method_calls: list[MethodCall]
    source_files_by_path: dict[str, str]  # rel_path -> language (graph corpus)
    repo_path: Path


# An extractor maps the parsed repo to a flat list of one role's Contracts.
Extractor = Callable[[ContractContext], list[Contract]]


class KeyBuilder(Protocol):
    """Builds the canonical ``contract_id`` for a protocol. Signature varies per
    protocol (HTTP takes method+path; gRPC takes service+method); callers use
    the concrete builder for the protocol they're in."""

    def __call__(self, *args: object, **kwargs: object) -> str: ...


def grpc_key_builder(*args: object, **kwargs: object) -> str:
    raise NotImplementedError(
        "gRPC contract keys (grpc::<pkg>.<Service>/<Method>) are a v0.5 seam (DEC-043)."
    )


def topic_key_builder(*args: object, **kwargs: object) -> str:
    raise NotImplementedError("Topic/queue/event contract keys are a v0.5 seam (DEC-043).")


@dataclass
class ProtocolEntry:
    """One protocol's registration. ``provider_extractors`` / ``consumer_extractors``
    are appended to by Items F/G (they start empty in Item D — the skeleton)."""

    protocol: str
    key_builder: KeyBuilder
    provider_extractors: list[Extractor] = field(default_factory=list)
    consumer_extractors: list[Extractor] = field(default_factory=list)


# The live registry. HTTP is real (extractors fill in Items F/G); gRPC/topic are
# stubbed so the federation seam is explicit.
REGISTRY: dict[str, ProtocolEntry] = {
    # HTTP key_builder is now the real normalizer-backed contractId (DEC-044).
    "http": ProtocolEntry("http", http_contract_id),
    # MCP is the second live instance (DEC-057, v0.5 Step 2): bare-tool keying
    # ``mcp::<tool>`` over the same Endpoint/base.join spine — the keystone proof
    # is that only this entry + the contracts/mcp extractors change.
    "mcp": ProtocolEntry("mcp", mcp_contract_id),
    "grpc": ProtocolEntry("grpc", grpc_key_builder),
    "topic": ProtocolEntry("topic", topic_key_builder),
}


def register_provider(protocol: str, extractor: Extractor) -> None:
    """Items F (and v0.5 protocols) register provider extractors here."""
    REGISTRY[protocol].provider_extractors.append(extractor)


def register_consumer(protocol: str, extractor: Extractor) -> None:
    """Item G (and v0.5 protocols) register consumer extractors here."""
    REGISTRY[protocol].consumer_extractors.append(extractor)
