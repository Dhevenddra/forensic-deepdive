"""The CrossBoundaryEdge abstraction (DEC-043, v0.4 keystone).

One generalizable model: a *cross-boundary contract* is a
``(role, contract_id, symbol_id, confidence, ...)`` record. The :func:`join`
pass groups records by ``contract_id`` and emits a :class:`CrossLink` between
every consumer and every provider sharing it. HTTP is the first instance
(Items E–I); gRPC and messaging topics reuse this in v0.5 as new key-builders —
**no new join machinery**.

This module is the pure abstraction: dataclasses + the deterministic join. It
imports only the ``Confidence`` taxonomy — no graph, no I/O, no tree-sitter.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from forensic_deepdive.graph.schema import Confidence


class ContractRole(StrEnum):
    PROVIDER = "provider"  # exposes the contract (a route handler)
    CONSUMER = "consumer"  # hits the contract (a frontend/service call site)


@dataclass(frozen=True, slots=True)
class Contract:
    """One side of a cross-boundary contract, emitted by a provider/consumer
    extractor. ``symbol_id`` is the handler/caller Symbol's ``qualified_name``
    (edges connect on that property — DEC-051). The endpoint-display fields
    (``method``…``spec_backed``) populate the :class:`Endpoint` join node.
    ``rel_path``/``line`` are the deterministic collection-sort key."""

    role: ContractRole
    contract_id: str
    symbol_id: str
    confidence: Confidence
    evidence: str = ""
    # endpoint metadata (providers always set these; consumers set what they know)
    protocol: str = "http"
    method: str = ""
    normalized_path: str = ""
    raw_path: str = ""
    framework: str = ""
    spec_backed: bool = False
    # deterministic collection sort key (DEC-043 — line stands in for start_byte,
    # consistent with the DEC-035 sort-key adaptation since our Tags carry line).
    rel_path: str = ""
    line: int = 0


@dataclass(frozen=True, slots=True)
class CrossLink:
    """A materialized consumer→provider link on a shared ``contract_id`` — the
    raw material for a ROUTES_TO edge. ``via`` is the protocol."""

    consumer_symbol_id: str
    provider_symbol_id: str
    contract_id: str
    confidence: Confidence
    via: str
    evidence: str = ""


def _collection_sort(contracts: list[Contract]) -> list[Contract]:
    return sorted(contracts, key=lambda c: (c.rel_path, c.line, c.symbol_id))


def join(providers: list[Contract], consumers: list[Contract]) -> list[CrossLink]:
    """Group by ``contract_id`` and link every consumer to every provider that
    shares it (DEC-043). Deterministic: providers/consumers are collection-
    sorted; ``contract_id``s are iterated in sorted order; the returned links
    are sorted by ``(consumer_symbol_id, provider_symbol_id)``.

    Confidence (Item D baseline — **DEC-047/Item H refines** to add the
    EXTRACTED tier for spec-backed or unique-literal-both-resolved joins):
    a contract with exactly one provider → ``INFERRED``; with several →
    ``AMBIGUOUS`` for *every* candidate link (surface all, never pick one —
    DEC-025/037 philosophy). A consumer whose ``contract_id`` matches no
    provider yields **no** CrossLink (it keeps its CALLS_ENDPOINT → Endpoint at
    persistence — the honest "endpoint we can't locate").
    """
    providers_by_id: dict[str, list[Contract]] = defaultdict(list)
    for p in _collection_sort(providers):
        providers_by_id[p.contract_id].append(p)

    links: list[CrossLink] = []
    for consumer in _collection_sort(consumers):
        matched = providers_by_id.get(consumer.contract_id)
        if not matched:
            continue
        confidence = Confidence.INFERRED if len(matched) == 1 else Confidence.AMBIGUOUS
        for provider in matched:
            links.append(
                CrossLink(
                    consumer_symbol_id=consumer.symbol_id,
                    provider_symbol_id=provider.symbol_id,
                    contract_id=consumer.contract_id,
                    confidence=confidence,
                    via=consumer.protocol,
                    evidence="contract-join",
                )
            )

    links.sort(key=lambda link: (link.consumer_symbol_id, link.provider_symbol_id))
    return links
