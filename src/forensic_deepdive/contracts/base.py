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
from dataclasses import dataclass, replace
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
    # DEC-067: AMQP topic-exchange match metadata — a publisher's routing_key / a
    # subscriber's binding_pattern. Empty for every other contract shape; read only by
    # reconcile_amqp (the exchange is the join key, this refines the match within it).
    match_key: str = ""
    # DEC-073: JAX-RS content negotiation — the @Produces/@Consumes media type(s)
    # (e.g. "produces=application/json; consumes=application/json"). A non-key display
    # property carried on the contract (the DEC-057 version-property precedent: never part
    # of contract_id, so two methods differing only by media type collapse to one
    # Endpoint). Empty for every other contract shape.
    content_type: str = ""


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


def reconcile_spec_backed(providers: list[Contract]) -> list[Contract]:
    """Collapse a *spec* provider into the in-code provider it describes (DEC-060,
    generalizing DEC-048's OpenAPI reconcile to any protocol).

    A ``.proto`` rpc (or any spec source) emits a ``spec_backed`` provider with a
    *synthetic* ``symbol_id``. When a real in-code provider (a servicer method) for
    the same ``contract_id`` also exists, the spec is the **same** logical endpoint,
    not a second one — so we drop the synthetic spec provider and mark the real
    provider ``spec_backed=True`` (its unique join then upgrades to EXTRACTED via
    :func:`_link_confidence`, instead of being miscounted as AMBIGUOUS). A spec with
    **no** in-code provider stays as the honest spec-only endpoint. Deterministic:
    groups are walked in sorted ``contract_id`` order."""
    by_id: dict[str, list[Contract]] = defaultdict(list)
    for p in providers:
        by_id[p.contract_id].append(p)
    out: list[Contract] = []
    for contract_id in sorted(by_id):
        members = by_id[contract_id]
        real = [m for m in members if not m.spec_backed]
        spec = [m for m in members if m.spec_backed]
        if real and spec:
            out.extend(replace(m, spec_backed=True) for m in real)
        else:
            out.extend(members)
    return out


def reconcile_amqp(
    cross_links: list[CrossLink],
    providers: list[Contract],
    consumers: list[Contract],
) -> list[CrossLink]:
    """Prune + re-confidence AMQP topic-exchange cross-links (DEC-067, generalizing the
    DEC-060 ``reconcile_spec_backed`` precedent to a per-pair refinement).

    :func:`join` links every publisher to every subscriber sharing an ``amqp::<exchange>``
    key (the cartesian over the shared-literal exchange — ``join`` stays unchanged). This
    refines those links by the AMQP topic match between the publisher's ``routing_key`` and
    each subscriber's ``binding_pattern`` (both carried in :attr:`Contract.match_key`):
    **exact → EXTRACTED**, **wildcard → INFERRED**, **provable non-match → DROP**. A
    publisher with several matching subscribers → all **AMBIGUOUS** (emit every match,
    never pick one). Non-AMQP links pass through untouched. Deterministic: re-sorted by
    ``(consumer_symbol_id, provider_symbol_id)``."""
    from forensic_deepdive.contracts.messaging.normalize import AMQP, amqp_match_kind

    prefix = AMQP + "::"
    pub_rk = {(c.symbol_id, c.contract_id): c.match_key for c in consumers if c.protocol == AMQP}
    sub_bp = {(p.symbol_id, p.contract_id): p.match_key for p in providers if p.protocol == AMQP}

    passthrough = [cl for cl in cross_links if not cl.contract_id.startswith(prefix)]
    by_pub: dict[tuple[str, str], list[CrossLink]] = defaultdict(list)
    for cl in cross_links:
        if cl.contract_id.startswith(prefix):
            by_pub[(cl.consumer_symbol_id, cl.contract_id)].append(cl)

    reconciled: list[CrossLink] = []
    for (pub_sym, contract_id), links in by_pub.items():
        routing_key = pub_rk.get((pub_sym, contract_id))
        if routing_key is None:
            continue
        matched: list[tuple[CrossLink, str, str]] = []
        for cl in links:
            binding = sub_bp.get((cl.provider_symbol_id, contract_id))
            if binding is None:
                continue
            if routing_key and binding:
                kind = amqp_match_kind(binding, routing_key)  # exact | wildcard | None(drop)
            else:
                # At least one side's key is dynamic/non-literal: the exchange is the only
                # proven shared literal, so the routing match is indeterminate → INFERRED
                # (never EXTRACTED — we can't prove it; never DROP — they share the exchange).
                kind = "indeterminate"
            if kind is not None:
                matched.append((cl, kind, binding or "*"))
        if not matched:
            continue  # provable non-match → drop every candidate for this publisher
        ambiguous = len(matched) > 1
        for cl, kind, binding in matched:
            confidence = (
                Confidence.AMBIGUOUS
                if ambiguous
                else (Confidence.EXTRACTED if kind == "exact" else Confidence.INFERRED)
            )
            reconciled.append(
                replace(cl, confidence=confidence, evidence=f"amqp {routing_key}~{binding} {kind}")
            )

    out = passthrough + reconciled
    out.sort(key=lambda cl: (cl.consumer_symbol_id, cl.provider_symbol_id))
    return out


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
