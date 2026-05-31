"""Reciprocal Rank Fusion + output shaping (DEC-038).

Pure functions — no I/O, no graph. RRF (Cormack, Clarke & Büttcher, SIGIR 2009)
fuses the per-retriever ranked lists; shaping then boosts implementation symbols
and demotes test/vendored/generated ones (the Entire ``pgr`` lesson, research
§2/§5.3: *ranking beats speed*).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

# SIGIR-2009 default. Used verbatim — tuning would be premature (DEC-038).
RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]], *, k: int = RRF_K
) -> dict[str, float]:
    """Fuse ranked lists of document ids into ``{doc_id: score}``.

    ``score(d) = Σ_r 1/(k + rank_r(d))`` over the lists that contain ``d``,
    where ``rank`` is 1-based. Only the retrievers that actually ran should be
    passed — a degraded (2-retriever) run simply fuses two lists.
    """
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return dict(scores)


def fused_order(scores: dict[str, float]) -> list[str]:
    """Doc ids sorted by fused score (desc), ties broken by id (deterministic)."""
    return sorted(scores, key=lambda d: (-scores[d], d))


# ---------------------------------------------------------------------------
# Output shaping
# ---------------------------------------------------------------------------

# Role multipliers: boost implementation, demote everything else. Source is the
# neutral baseline; the others are pulled below an equal-base-rank impl hit.
_ROLE_FACTOR: dict[str, float] = {
    "source": 1.0,
    "test": 0.5,
    "fixture": 0.5,
    "vendored": 0.4,
    "generated": 0.4,
    "example": 0.4,  # DEC-049 — tutorial/example code: retrievable but demoted
}

# Kind multipliers: a slight nudge toward the symbols an agent usually wants
# (callable implementation) over containers / synthetic module scopes.
_KIND_FACTOR: dict[str, float] = {
    "function": 1.05,
    "method": 1.05,
    "module": 0.8,
}


def shape_factor(role: str, kind: str) -> float:
    """The multiplicative shaping factor for a (role, kind) pair."""
    return _ROLE_FACTOR.get(role, 1.0) * _KIND_FACTOR.get(kind, 1.0)


def shape(hits: Sequence[dict], *, score_key: str = "score") -> list[dict]:
    """Re-rank *hits* by ``score * shape_factor(role, kind)`` (desc).

    Each hit is a dict carrying at least ``score``, ``role``, ``kind`` and
    ``symbol`` (used as the deterministic tie-breaker). The shaped score is
    written back under ``shaped_score`` and the list is returned re-sorted; the
    input is not mutated in place beyond that annotation.

    At equal base score an implementation (source) hit therefore sorts above a
    ``test``/``vendored``/``generated`` hit — the DEC-038 shaping contract.
    """
    annotated: list[dict] = []
    for hit in hits:
        factor = shape_factor(hit.get("role", "source"), hit.get("kind", ""))
        out = dict(hit)
        out["shaped_score"] = hit.get(score_key, 0.0) * factor
        annotated.append(out)
    annotated.sort(key=lambda h: (-h["shaped_score"], h.get("symbol", "")))
    return annotated
