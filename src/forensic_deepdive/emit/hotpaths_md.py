"""HOTPATHS.md emitter — the code most other code depends on.

Combines static dependency centrality with git churn to surface the symbols,
edges, and files that matter most. One of the five contract artifacts.

DEC-030 (item 9 phase 2): when ``RepoFacts.graph_db_path`` is set, the
"Dependency hot spots" and "Cross-file dependencies" sections read from
the LadybugDB CALLS edges (symbol-level, post-resolver-DEC-025) instead
of the in-memory NetworkX file graph. The graph view is strictly richer:
symbols carry qualified names with parent chains (DEC-023), confidence
labels per edge (DEC-015), and false-edge-free resolution (DEC-012 +
DEC-025). The NetworkX fallback stays for callers that pass
``graph_db_path=None`` (e.g. golden-emit fixture construction).
"""

from __future__ import annotations

from forensic_deepdive.emit.common import (
    INFERRED,
    RepoFacts,
    confidence_banner,
    confidence_note,
    footer,
    humanize_int,
    md_table,
    ranked_files,
)


def render_hotpaths(facts: RepoFacts) -> str:
    """Render the full HOTPATHS.md document."""
    lines = [
        f"# HOTPATHS — {facts.repo_name}",
        "",
        "> The code most other code depends on, and the files that change most.",
        confidence_banner(),
        "",
        *_dependency_hotspots(facts),
        *_cross_file_deps(facts),
        *_co_change_clusters(facts),  # DEC-029 — graph-only addition
        *_change_hotspots(facts),
        *_churn_x_centrality(facts),
        footer(facts),
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Dependency hot spots — graph-mode (DEC-030) with NetworkX fallback
# ---------------------------------------------------------------------------


def _dependency_hotspots(facts: RepoFacts, limit: int = 15) -> list[str]:
    """Top callees ranked by inbound CALLS count in graph mode; falls
    back to v0.1 PageRank-on-name-graph definitions when no graph is
    available."""
    graph_rows = _graph_dependency_hotspots(facts, limit)
    if graph_rows is not None:
        return [
            "## Dependency hot spots",
            "",
            "Symbols with the most inbound `CALLS` edges (DEC-025 resolver). "
            "The load-bearing callees — signature changes touch every caller.",
            "",
            md_table(["Symbol", "Defined in", "Callers", "Confidence mix"], graph_rows),
            "",
        ]
    # Fallback: NetworkX-based v0.1 path.
    rows = [
        [f"`{d.name}`", f"`{d.rel_path}`", f"{d.rank:.4f}"]
        for d in facts.ranked.definitions[:limit]
    ]
    return [
        "## Dependency hot spots",
        "",
        confidence_note(INFERRED),
        "",
        "Definitions with the widest blast radius — the most depended-on "
        "symbols. Definitions are EXTRACTED; the PageRank ranking is the "
        "derivation.",
        "",
        md_table(["Symbol", "Defined in", "Rank"], rows),
        "",
    ]


def _graph_dependency_hotspots(facts: RepoFacts, limit: int) -> list[list[str]] | None:
    """Query the graph for top callees by inbound CALLS. Returns ``None``
    when no graph is available (caller falls back to v0.1)."""
    if facts.graph_db_path is None:
        return None
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            # Two queries: counts per callee, plus the confidence
            # breakdown so we can label honestly per DEC-015. Aggregating
            # both in one Cypher pass would need GROUP_CONCAT — keep
            # simple with two passes joined in Python.
            counts = list(
                store.query(
                    "MATCH (caller:Symbol)-[:CALLS]->(callee:Symbol) "
                    "RETURN callee.qualified_name, callee.file_path, "
                    "count(caller) AS inbound "
                    "ORDER BY inbound DESC, callee.qualified_name "
                    f"LIMIT {limit}"
                )
            )
            if not counts:
                return []
            top_qns = [row[0] for row in counts]
            # Confidence mix per callee.
            conf_rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                    "WHERE callee.qualified_name IN $qns "
                    "RETURN callee.qualified_name, r.confidence, count(r) "
                    "ORDER BY callee.qualified_name, r.confidence",
                    {"qns": top_qns},
                )
            )
    except Exception:  # pragma: no cover — degrade if the .lbug is malformed
        return None

    conf_by_qn: dict[str, dict[str, int]] = {}
    for qn, conf, n in conf_rows:
        conf_by_qn.setdefault(qn, {})[conf] = int(n)

    body: list[list[str]] = []
    for qn, fp, inbound in counts:
        bare = qn.rsplit("::", 1)[-1]
        confs = conf_by_qn.get(qn, {})
        # Render confidence mix in the standard order EXTRACTED / INFERRED
        # / AMBIGUOUS so readers can scan at a glance.
        bits = []
        for level in ("EXTRACTED", "INFERRED", "AMBIGUOUS"):
            if level in confs:
                bits.append(f"{confs[level]} `{level}`")
        body.append([f"`{bare}`", f"`{fp}`", str(int(inbound)), ", ".join(bits)])
    return body


# ---------------------------------------------------------------------------
# Cross-file dependencies — graph-mode (DEC-030) with NetworkX fallback
# ---------------------------------------------------------------------------


def _cross_file_deps(facts: RepoFacts, limit: int = 15) -> list[str]:
    """File-to-file dependency edges. Graph mode aggregates CALLS by
    (caller.file, callee.file); NetworkX fallback uses the v0.1 file-
    level symbol graph."""
    graph_rows = _graph_cross_file_deps(facts, limit)
    if graph_rows is not None:
        return [
            "## Cross-file dependencies",
            "",
            "File-to-file dependencies aggregated from symbol-level `CALLS` "
            "edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.",
            "",
            md_table(["From", "To", "Calls", "Top callee"], graph_rows),
            "",
        ]
    pair_idents: dict[tuple[str, str], set[str]] = {}
    for src, dst, data in facts.symbol_graph.graph.edges(data=True):
        if src == dst:
            continue  # self-edges are not cross-file dependencies
        pair_idents.setdefault((src, dst), set()).add(data.get("ident", "?"))
    ranked = sorted(pair_idents.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rows: list[list[str]] = []
    for (src, dst), idents in ranked[:limit]:
        shown = ", ".join(sorted(idents)[:5]) + ("…" if len(idents) > 5 else "")
        rows.append([f"`{src}`", f"`{dst}`", shown])
    return [
        "## Cross-file dependencies",
        "",
        "Which file leans on which (referencer → definer), by shared symbols.",
        "",
        md_table(["From", "To", "Shared symbols"], rows),
        "",
    ]


def _graph_cross_file_deps(facts: RepoFacts, limit: int) -> list[list[str]] | None:
    """Query the graph for cross-file dependency pairs, ranked by total
    CALLS edges between them. Returns the most-called symbol per pair as
    a quick "what's the dependency about" hint."""
    if facts.graph_db_path is None:
        return None
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[:CALLS]->(callee:Symbol) "
                    "WHERE caller.file_path <> callee.file_path "
                    "RETURN caller.file_path, callee.file_path, "
                    "count(callee) AS calls "
                    "ORDER BY calls DESC, caller.file_path, callee.file_path "
                    f"LIMIT {limit}"
                )
            )
            if not rows:
                return []
            # For each (from, to) pair, get the most-called callee as
            # the "top callee" hint. One small Cypher per pair is fine
            # at limit=15.
            body: list[list[str]] = []
            for from_file, to_file, calls in rows:
                top = list(
                    store.query(
                        "MATCH (caller:Symbol {file_path: $f})-[:CALLS]->"
                        "(callee:Symbol {file_path: $t}) "
                        "RETURN callee.qualified_name, count(callee) AS n "
                        "ORDER BY n DESC, callee.qualified_name LIMIT 1",
                        {"f": from_file, "t": to_file},
                    )
                )
                top_label = top[0][0].rsplit("::", 1)[-1] if top else "?"
                body.append(
                    [
                        f"`{from_file}`",
                        f"`{to_file}`",
                        str(int(calls)),
                        f"`{top_label}`",
                    ]
                )
    except Exception:  # pragma: no cover
        return None
    return body


# ---------------------------------------------------------------------------
# Co-change clusters — graph-only (no NetworkX equivalent)
# ---------------------------------------------------------------------------


def _co_change_clusters(facts: RepoFacts, limit: int = 10) -> list[str]:
    """Graph-driven section (DEC-029): file pairs that change together
    most often (DEC-027 CO_CHANGES_WITH). The "if you touch X, also
    touch Y" signal. No NetworkX equivalent — section disappears when
    graph mode is off."""
    if facts.graph_db_path is None:
        return []
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (a:File)-[r:CO_CHANGES_WITH]->(b:File) "
                    "RETURN a.path, b.path, r.frequency "
                    "ORDER BY r.frequency DESC, a.path, b.path "
                    f"LIMIT {limit}"
                )
            )
    except Exception:  # pragma: no cover
        return []
    if not rows:
        return []
    body_rows = [[f"`{a}`", f"`{b}`", humanize_int(int(freq))] for a, b, freq in rows]
    return [
        "## Co-change clusters",
        "",
        confidence_note(INFERRED),
        "",
        "Files most frequently committed together (DEC-027). The shared-"
        "commit count is EXTRACTED from git; the implication 'these should "
        "change together' is the derivation.",
        "",
        md_table(["File A", "File B", "Shared commits"], body_rows),
        "",
    ]


# ---------------------------------------------------------------------------
# Git-history sections (unchanged from v0.1)
# ---------------------------------------------------------------------------


def _change_hotspots(facts: RepoFacts, limit: int = 15) -> list[str]:
    if not facts.history.is_git_repo:
        return ["## Change hot spots", "", "_No git history available._", ""]
    rows = [
        [f"`{churn.path}`", humanize_int(churn.commits)] for churn in facts.history.churn[:limit]
    ]
    return [
        "## Change hot spots",
        "",
        "Files touched by the most commits (git churn).",
        "",
        md_table(["File", "Commits"], rows),
        "",
    ]


def _churn_x_centrality(facts: RepoFacts, limit: int = 10) -> list[str]:
    if not facts.history.is_git_repo:
        return []
    churn_by_path = {churn.path: churn.commits for churn in facts.history.churn}
    rows: list[list[str]] = []
    for path, score in ranked_files(facts):
        if path in churn_by_path:
            rows.append([f"`{path}`", f"{score:.4f}", humanize_int(churn_by_path[path])])
        if len(rows) >= limit:
            break
    return [
        "## Churn × centrality",
        "",
        confidence_note(INFERRED),
        "",
        "Files that are **both** highly depended-on and frequently changed — "
        "the riskiest edits in the repo. Commit counts are EXTRACTED; the "
        "centrality column and the risk framing are the derivation.",
        "",
        md_table(["File", "Centrality", "Commits"], rows),
        "",
    ]
