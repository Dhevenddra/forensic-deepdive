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
from collections.abc import Callable, Sequence
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


def _link_confidence(
    consumer: Contract, providers: list[Contract], *, is_fallback: bool
) -> Confidence:
    """The ROUTES_TO (join-node) confidence (DEC-047), independent of the
    per-edge CALLS_ENDPOINT/HANDLES confidence.

    Several candidate providers → ``AMBIGUOUS`` (surface all, never pick one).
    A *fallback* match (e.g. the HTTP method-wildcard) is capped at ``INFERRED``
    (path matched, verb undeclared). For a unique exact match, ``EXTRACTED`` iff
    the provider is spec-backed (Item I) **or** both sides are themselves
    ``EXTRACTED``-confidence (a literal path+method on each — no generalized
    ``{param}`` segment, no heuristic router mount); otherwise ``INFERRED``.
    """
    if len(providers) > 1:
        return Confidence.AMBIGUOUS
    if is_fallback:
        return Confidence.INFERRED
    provider = providers[0]
    both_literal = (
        consumer.confidence is Confidence.EXTRACTED and provider.confidence is Confidence.EXTRACTED
    )
    if provider.spec_backed or both_literal:
        return Confidence.EXTRACTED
    return Confidence.INFERRED


def join(
    providers: list[Contract],
    consumers: list[Contract],
    *,
    match_keys: Callable[[Contract], Sequence[str]] | None = None,
) -> list[CrossLink]:
    """Group by ``contract_id`` and link every consumer to every provider that
    shares it (DEC-043). Deterministic: providers/consumers are collection-
    sorted; the returned links are sorted by ``(consumer_symbol_id,
    provider_symbol_id)``.

    *match_keys* (DEC-047) is the protocol's ordered candidate-key builder for a
    consumer — the **first** key is the primary (exact) match, later keys are
    fallbacks tried only when no earlier key matched and **capped at INFERRED**
    (HTTP supplies ``(exact, http::*::path)`` so a Spring bare ``@RequestMapping``
    still joins). Default is exact-only: ``(c.contract_id,)``. Keeping ``join``
    key-agnostic is what lets gRPC/topic reuse it unchanged.

    Confidence is the join-node tier (:func:`_link_confidence`): unique +
    spec-backed-or-both-literal → ``EXTRACTED``; unique otherwise → ``INFERRED``;
    several providers → ``AMBIGUOUS`` for every candidate; fallback → INFERRED.
    A consumer matching no provider yields **no** CrossLink (it keeps its
    CALLS_ENDPOINT → Endpoint at persistence — the honest "endpoint we can't
    locate").
    """
    providers_by_id: dict[str, list[Contract]] = defaultdict(list)
    for p in _collection_sort(providers):
        providers_by_id[p.contract_id].append(p)

    links: list[CrossLink] = []
    for consumer in _collection_sort(consumers):
        keys = tuple(match_keys(consumer)) if match_keys is not None else (consumer.contract_id,)
        for index, key in enumerate(keys):
            matched = providers_by_id.get(key)
            if not matched:
                continue
            is_fallback = index > 0
            confidence = _link_confidence(consumer, matched, is_fallback=is_fallback)
            for provider in matched:
                links.append(
                    CrossLink(
                        consumer_symbol_id=consumer.symbol_id,
                        provider_symbol_id=provider.symbol_id,
                        contract_id=consumer.contract_id,
                        confidence=confidence,
                        via=consumer.protocol,
                        evidence="contract-join-wildcard" if is_fallback else "contract-join",
                    )
                )
            break  # first matching key wins (exact precedes any fallback)

    links.sort(key=lambda link: (link.consumer_symbol_id, link.provider_symbol_id))
    return links
