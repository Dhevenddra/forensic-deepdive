"""Hybrid NL query orchestrator (DEC-038).

Runs the three retrievers, fuses them by RRF (k=60), shapes the output, and
returns the MCP ``query`` NL-branch payload: shaped, confidence-tagged hits with
per-hit provenance, plus ``retrievers_active`` + ``degraded`` (honesty about
which tiers ran).

The structural tier lives here (it's small and graph-bound): the lexical
exact-name hits seed *anchors*; they expand one hop via CALLS/MEMBER_OF and the
anchor+neighbor set is ranked by CALLS in-degree — graph proximity + a degree
centrality proxy, computed at query time (DEC-038 divergence: no persisted
PageRank column).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from forensic_deepdive.inventory import ROLE_SOURCE, classify_role
from forensic_deepdive.query.fuse import reciprocal_rank_fusion, shape
from forensic_deepdive.query.lexical import (
    LexicalIndex,
    build_lexical_index_from_store,
    lexical_index_path_for_db,
)

if TYPE_CHECKING:
    from pathlib import Path

    from forensic_deepdive.graph import LadybugStore

# Generous per-retriever candidate pool; RRF + shaping cut it down to ``limit``.
_POOL = 200


def hybrid_query(
    db_path: Path,
    query: str,
    *,
    semantic: bool = False,
    limit: int = 25,
) -> dict[str, Any]:
    """Answer *query* against the graph at *db_path*. See module docstring."""
    from forensic_deepdive.graph import LadybugStore  # noqa: PLC0415 — avoid import cycle

    index_path = lexical_index_path_for_db(db_path)
    with LadybugStore(db_path) as store:
        # Lexical (always on). Lazily (re)build the sidecar from the graph if
        # it's missing — so a graph built before Item E still answers NL queries.
        idx = LexicalIndex(index_path)
        if not idx.exists():
            build_lexical_index_from_store(store, index_path)
        lex_hits = idx.search(query, limit=_POOL)

        meta: dict[str, dict[str, Any]] = {}
        for h in lex_hits:
            meta[h.qualified_name] = {
                "file": h.file_path,
                "line": h.line_start,
                "kind": h.kind,
                "role": _effective_role(h.role, h.file_path),
            }
        lexical_ranked = [h.qualified_name for h in lex_hits]
        exact_names = {h.qualified_name for h in lex_hits if h.exact}
        # DEC-084: symbols whose NAME carries a query stem. These (and exact hits)
        # get an additive ranking boost below so a literal name match outranks
        # unrelated symbols that only co-occur structurally or via BM25 noise.
        name_match_names = {h.qualified_name for h in lex_hits if h.name_match}

        # Structural (always on). Anchors = exact lexical matches.
        structural_ranked, struct_meta = _structural(store, list(exact_names))
        for qn, m in struct_meta.items():
            meta.setdefault(qn, m)

        retriever_members: dict[str, set[str]] = {
            "lexical": set(lexical_ranked),
            "structural": set(structural_ranked),
        }
        ranked_lists: list[list[str]] = [lexical_ranked, structural_ranked]
        retrievers_active = ["lexical", "structural"]

        # Semantic (opt-in, offline). Off / unavailable ⇒ two-retriever, said-so.
        if semantic:
            semantic_ranked = _semantic(store, index_path, query, meta)
            if semantic_ranked is not None:
                retriever_members["semantic"] = set(semantic_ranked)
                ranked_lists.append(semantic_ranked)
                retrievers_active.append("semantic")

        fused = reciprocal_rank_fusion(ranked_lists)

        results: list[dict[str, Any]] = []
        for qn, fscore in fused.items():
            m = meta.get(qn)
            if m is None:
                continue
            # DEC-084 name-match boost: float exact/name hits above unrelated
            # symbols. The bonus is large relative to RRF scores (~0.01–0.03) so it
            # survives the role/kind shaping multiply (0.4–1.05) — a name hit never
            # sinks below a non-name hit on shaping alone, while exact > name_match
            # and ordinary RRF still orders everything within each tier.
            boost = 2.0 if qn in exact_names else (1.0 if qn in name_match_names else 0.0)
            results.append(
                {
                    "symbol": qn,
                    "qualified_name": qn,
                    "file": m["file"],
                    "line": m["line"],
                    "kind": m["kind"],
                    "role": m["role"],
                    "score": fscore + boost,
                    "retrievers": sorted(
                        r for r, members in retriever_members.items() if qn in members
                    ),
                    "confidence": "EXTRACTED" if qn in exact_names else "INFERRED",
                }
            )
        shaped = shape(results)[:limit]

        degraded = "semantic" not in retrievers_active
        return {
            "natural_language": query,
            "retrievers_active": retrievers_active,
            "degraded": degraded,
            # DEC-084: state the degraded condition at the point of use, not just as
            # a boolean flag, so a caller reading the results knows when to distrust
            # a thin answer and how to upgrade it.
            "note": (
                "semantic tier not installed — results are lexical + structural only "
                "(no concept-level matching). Install the [semantic] extra for "
                "embedding search."
                if degraded
                else "all retrievers active (lexical + structural + semantic)."
            ),
            "results": shaped,
        }


# ---------------------------------------------------------------------------
# Structural tier
# ---------------------------------------------------------------------------


def _structural(
    store: LadybugStore, anchors: list[str]
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Expand *anchors* one hop (CALLS/MEMBER_OF) and rank the anchor+neighbor
    set by CALLS in-degree. Anchors always sort above pure neighbors."""
    if not anchors:
        return [], {}
    anchor_set = set(anchors)
    candidates: list[str] = list(anchors)
    seen = set(anchors)
    for qn in anchors:
        for nb in _neighbors(store, qn):
            if nb not in seen:
                seen.add(nb)
                candidates.append(nb)

    meta: dict[str, dict[str, Any]] = {}
    scored: list[tuple[bool, int, str]] = []
    for qn in candidates:
        info = _symbol_info(store, qn)
        if info is None:
            continue
        meta[qn] = info
        scored.append((qn in anchor_set, _in_degree(store, qn), qn))
    # anchors first, then in-degree desc, then qn (deterministic total order).
    scored.sort(key=lambda t: (not t[0], -t[1], t[2]))
    return [qn for _, _, qn in scored], meta


def _neighbors(store: LadybugStore, qn: str) -> list[str]:
    out: list[str] = []
    for rel in ("CALLS", "MEMBER_OF"):
        out.extend(
            row[0]
            for row in store.query(
                f"MATCH (s:Symbol {{qualified_name: $q}})-[:{rel}]-(n:Symbol) "
                "RETURN n.qualified_name",
                {"q": qn},
            )
        )
    return out


def _in_degree(store: LadybugStore, qn: str) -> int:
    rows = list(
        store.query(
            "MATCH (c:Symbol)-[:CALLS]->(:Symbol {qualified_name: $q}) RETURN count(c)",
            {"q": qn},
        )
    )
    return int(rows[0][0]) if rows else 0


def _symbol_info(store: LadybugStore, qn: str) -> dict[str, Any] | None:
    rows = list(
        store.query(
            "MATCH (f:File)-[:DEFINES]->(s:Symbol {qualified_name: $q}) "
            "RETURN s.file_path, s.line_start, s.kind, f.role LIMIT 1",
            {"q": qn},
        )
    )
    if not rows:
        return None
    fp, ls, kind, role = rows[0]
    return {
        "file": fp,
        "line": int(ls),
        "kind": kind,
        "role": _effective_role(role or ROLE_SOURCE, fp),
    }


# ---------------------------------------------------------------------------
# Semantic tier
# ---------------------------------------------------------------------------


def _semantic(
    store: LadybugStore,
    index_path: Path,
    query: str,
    meta: dict[str, dict[str, Any]],
) -> list[str] | None:
    """Run the semantic tier if available; fill metadata for its hits. Returns
    the ranked qn list, or ``None`` when the extra/model/vectors are absent."""
    from forensic_deepdive.query.semantic import SemanticIndex, semantic_available

    index_dir = index_path.parent
    if not semantic_available(index_dir):
        return None
    hits = SemanticIndex(index_dir).search(query, limit=_POOL)
    ranked: list[str] = []
    for h in hits:
        ranked.append(h.qualified_name)
        if h.qualified_name not in meta:
            info = _symbol_info(store, h.qualified_name)
            if info is not None:
                meta[h.qualified_name] = info
    return ranked


# ---------------------------------------------------------------------------
# Shaping input
# ---------------------------------------------------------------------------


def _effective_role(stored_role: str, file_path: str) -> str:
    """DEC-038: trust an authoritative non-source role; otherwise re-derive the
    role from the path so a test/vendored/generated-shaped path is demoted even
    if the graph stored it as ``source``."""
    if stored_role and stored_role != ROLE_SOURCE:
        return stored_role
    return classify_role(file_path)
