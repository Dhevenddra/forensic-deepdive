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
        *_change_hotspots(facts),
        *_churn_x_centrality(facts),
        footer(facts),
    ]
    return "\n".join(lines) + "\n"


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
