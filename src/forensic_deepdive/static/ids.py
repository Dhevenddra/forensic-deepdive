"""Stable node-ID authority (DEC-051, v0.4 Item A).

The single place node identity is minted. A node ID is deterministic,
**line-number-free** (so it survives an unrelated edit elsewhere in the file —
the v1.0 incremental/rename forward-compat seam, research §10), and
overload-disambiguated. ``qualified_name`` remains the human-facing display key
(schema.Symbol); the ID is the key.

Symbol ID format: ``<kind>:<rel_path>:<qn_local>`` plus a disambiguator when a
``(kind, rel_path, qn_local)`` triple collides:
  * ``#<n>`` by sorted-then-stable definition order, and
  * ``~<short-hash>`` (8 hex of sha256 over the signature) when a *content*
    collision is detectable — distinct signature/arity on the same triple — so
    the two overloads stay distinct even if their definition order shifts.

``make_module_id`` / ``make_endpoint_id`` are thin seams: the Module id reuses
the DEC-024 ``module_pk`` shape, and an Endpoint id *is* its contract_id
(DEC-043, v0.4 Item D). Both live here so identity minting has one home.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


def make_symbol_id(kind: str, rel_path: str, qn_local: str, *, disambiguator: str = "") -> str:
    """The canonical Symbol node ID. ``disambiguator`` (e.g. ``"#1"`` or
    ``"~ab12cd34"``) is appended verbatim; empty for the common unique case."""
    return f"{kind}:{rel_path}:{qn_local}{disambiguator}"


def make_module_id(language: str, raw_path: str) -> str:
    """Module node ID — reuses the DEC-024 ``"<language>:<raw_path>"`` shape so
    the cross-language same-string disambiguation (``python:os`` vs ``go:os``)
    holds. Kept here so all node identity is minted in one module."""
    return f"{language}:{raw_path}"


def make_endpoint_id(contract_id: str) -> str:
    """Endpoint node ID == its contract_id (DEC-043). A thin seam: the contract
    key-builders already produce a canonical string; identity is that string."""
    return contract_id


def _short_hash(signature: str) -> str:
    """8 hex chars of sha256 over a signature — the content-collision tag."""
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True, slots=True)
class SymbolDescriptor:
    """One symbol to mint an ID for. ``signature`` distinguishes overloads with
    the same ``(kind, rel_path, qn_local)`` triple; ``""`` when unknown (today
    ``Symbol.signature`` is empty — the ``~hash`` path is wired but dormant,
    mirroring DEC-041's reserved-signature note)."""

    kind: str
    rel_path: str
    qn_local: str
    signature: str = ""


def assign_disambiguators(descriptors: Sequence[SymbolDescriptor]) -> list[str]:
    """Mint one stable ID per descriptor, in input order.

    A ``(kind, rel_path, qn_local)`` triple seen once yields a bare
    ``<kind>:<rel_path>:<qn_local>`` (no disambiguator) — the common case, so
    non-overloaded symbols keep the clean id. When a triple collides:

    * if the colliding descriptors have **distinct** signatures, each gets a
      ``~<short-hash>`` of its signature — stable regardless of definition
      order;
    * otherwise (same/empty signature) each gets ``#<n>`` by the order in which
      that triple's members appear, after a stable sort — deterministic across
      input permutations of equal triples.

    Determinism: collisions are resolved per-triple over the descriptors sorted
    by ``(kind, rel_path, qn_local, signature, original_index)``, so two runs
    that present equal triples in different orders mint the same id set.
    """
    by_triple: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for i, d in enumerate(descriptors):
        by_triple[(d.kind, d.rel_path, d.qn_local)].append(i)

    ids: list[str] = [""] * len(descriptors)
    for triple, indices in by_triple.items():
        kind, rel_path, qn_local = triple
        if len(indices) == 1:
            ids[indices[0]] = make_symbol_id(kind, rel_path, qn_local)
            continue
        # Stable order for this triple's members.
        ordered = sorted(indices, key=lambda i: (descriptors[i].signature, i))
        sigs = {descriptors[i].signature for i in ordered}
        use_hash = len(sigs) == len(ordered) and all(descriptors[i].signature for i in ordered)
        for n, i in enumerate(ordered):
            disambiguator = f"~{_short_hash(descriptors[i].signature)}" if use_hash else f"#{n}"
            ids[i] = make_symbol_id(kind, rel_path, qn_local, disambiguator=disambiguator)
    return ids
