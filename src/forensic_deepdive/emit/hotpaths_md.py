"""HOTPATHS.md emitter — the code most other code depends on.

Combines static dependency centrality with git churn to surface the symbols,
edges, and files that matter most. One of the five contract artifacts.
"""

from __future__ import annotations

from forensic_deepdive.emit.common import (
    RepoFacts,
    confidence_banner,
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
        *_call_graph_hotspots(facts),  # DEC-029
        *_co_change_clusters(facts),  # DEC-029
        *_change_hotspots(facts),
        *_churn_x_centrality(facts),
        footer(facts),
    ]
    return "\n".join(lines) + "\n"


def _call_graph_hotspots(facts: RepoFacts, limit: int = 10) -> list[str]:
    """DEC-029 graph-driven section: symbols with the most incoming
    CALLS edges — the load-bearing callees. Only rendered when the
    LadybugDB graph is available (BuildGraphPhase ran)."""
    if facts.graph_db_path is None:
        return []
    # Local import to keep emit's import-graph free of LadybugStore when
    # the graph isn't being used (e.g. unit-testing pure emitters).
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                    "RETURN callee.qualified_name, callee.file_path, "
                    "count(r) AS inbound "
                    "ORDER BY inbound DESC, callee.qualified_name "
                    f"LIMIT {limit}"
                )
            )
    except Exception:  # pragma: no cover — graph may be malformed; degrade
        return []
    if not rows:
        return []
    body_rows = [[f"`{qn.rsplit('::', 1)[-1]}`", f"`{fp}`", str(int(n))] for qn, fp, n in rows]
    return [
        "## Call-graph hot spots",
        "",
        "Symbols with the most inbound CALLS edges (DEC-025 resolver). "
        "These are the symbols most other symbols depend on.",
        "",
        md_table(["Callee", "Defined in", "Callers"], body_rows),
        "",
    ]


def _co_change_clusters(facts: RepoFacts, limit: int = 10) -> list[str]:
    """DEC-029 graph-driven section: file pairs that change together
    most often (DEC-027 CO_CHANGES_WITH). The "if you touch X, also
    touch Y" signal."""
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
        "Files most frequently committed together (DEC-027). "
        "Editing one and not the other is a likely-incomplete change.",
        "",
        md_table(["File A", "File B", "Shared commits"], body_rows),
        "",
    ]


def _dependency_hotspots(facts: RepoFacts, limit: int = 15) -> list[str]:
    rows = [
        [f"`{d.name}`", f"`{d.rel_path}`", f"{d.rank:.4f}"]
        for d in facts.ranked.definitions[:limit]
    ]
    return [
        "## Dependency hot spots",
        "",
        "Definitions with the widest blast radius — the most depended-on symbols.",
        "",
        md_table(["Symbol", "Defined in", "Rank"], rows),
        "",
    ]


def _cross_file_deps(facts: RepoFacts, limit: int = 15) -> list[str]:
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
        "Files that are **both** highly depended-on and frequently changed — "
        "the riskiest edits in the repo.",
        "",
        md_table(["File", "Centrality", "Commits"], rows),
        "",
    ]
