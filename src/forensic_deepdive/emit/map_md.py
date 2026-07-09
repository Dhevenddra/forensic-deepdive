"""MAP.md emitter — the structural map of the codebase.

Files and symbols ranked by dependency centrality (PageRank over the symbol
graph). One of the five contract artifacts.
"""

from __future__ import annotations

from forensic_deepdive.emit.common import (
    INFERRED,
    RepoFacts,
    confidence_banner,
    confidence_note,
    footer,
    humanize_int,
    language_label,
    md_table,
    ranked_files,
)


def render_map(facts: RepoFacts) -> str:
    """Render the full MAP.md document."""
    lines = [
        f"# MAP — {facts.repo_name}",
        "",
        "> Structural map: files and symbols ranked by dependency centrality "
        "(PageRank over the symbol graph).",
        confidence_banner(),
        "",
        *_overview(facts),
        *_central_files(facts),
        *_key_definitions(facts),
        footer(facts),
    ]
    return "\n".join(lines) + "\n"


def _overview(facts: RepoFacts) -> list[str]:
    defs = sum(1 for tag in facts.tags if tag.kind == "def")
    refs = sum(1 for tag in facts.tags if tag.kind == "ref")
    graph = facts.symbol_graph.graph
    langs = (
        ", ".join(
            f"{language_label(name)} ({count})"
            for name, count in sorted(
                facts.language_breakdown.items(), key=lambda kv: (-kv[1], kv[0])
            )
        )
        or "none detected"
    )
    # DEC-103: on an examples-heavy repo the bare production count is misreadable
    # ("3 source files" vs a 117-file graph) — annotate with the demoted-but-in-graph
    # total. Zero demotions → the line is unchanged.
    source_line = f"- **Source files:** {humanize_int(facts.file_count)}"
    if facts.example_file_count:
        source_line += (
            f" (+{humanize_int(facts.example_file_count)} in graph, demoted as examples/)"
        )
    out = [
        "## Overview",
        "",
        source_line,
        f"- **Languages:** {langs}",
        f"- **Symbols:** {humanize_int(defs)} definitions, {humanize_int(refs)} references",
        f"- **Symbol graph:** {graph.number_of_nodes()} files, "
        f"{graph.number_of_edges()} dependency edges",
    ]
    if facts.test_file_count or facts.fixture_file_count:
        out.append(
            f"- **Test surface:** {humanize_int(facts.test_file_count)} test file(s), "
            f"{humanize_int(facts.fixture_file_count)} fixture file(s) "
            "(inventoried, excluded from the dependency graph)"
        )
    if facts.vendored_file_count or facts.generated_file_count:
        out.append(
            f"- **Non-authored:** {humanize_int(facts.vendored_file_count)} vendored, "
            f"{humanize_int(facts.generated_file_count)} generated "
            "(inventoried, excluded from the dependency graph)"
        )
    if facts.example_file_count:
        out.append(
            f"- **Example/tutorial:** {humanize_int(facts.example_file_count)} file(s) "
            "(in the dependency graph but demoted in ranking + query)"
        )
    if facts.flatten is not None:
        flat = facts.flatten
        tokens = (
            f", ~{humanize_int(flat.token_count)} tokens" if flat.token_count is not None else ""
        )
        out.append(
            f"- **Flattened pack:** `{flat.output_path.name}` "
            f"({humanize_int(flat.char_count)} chars{tokens})"
        )
    out.append("")
    return out


def _defs_by_file(facts: RepoFacts) -> dict[str, list[str]]:
    """Map each file to its defined symbol names, highest-ranked first."""
    by_file: dict[str, list[str]] = {}
    for definition in facts.ranked.definitions:
        names = by_file.setdefault(definition.rel_path, [])
        if definition.name not in names:
            names.append(definition.name)
    return by_file


def _central_files(facts: RepoFacts, limit: int = 15) -> list[str]:
    defs_by_file = _defs_by_file(facts)
    rows: list[list[str]] = []
    for rank, (path, score) in enumerate(ranked_files(facts)[:limit], start=1):
        names = defs_by_file.get(path, [])
        preview = ", ".join(names[:4]) + ("…" if len(names) > 4 else "")
        rows.append([str(rank), f"`{path}`", f"{score:.4f}", preview or "—"])
    return [
        "## Most central files",
        "",
        confidence_note(INFERRED),
        "",
        "Files ranked by PageRank — edits here ripple widest.",
        "",
        md_table(["#", "File", "Score", "Key definitions"], rows),
        "",
    ]


def _key_definitions(facts: RepoFacts, limit: int = 20) -> list[str]:
    """Top symbols. Graph mode (DEC-030) ranks by inbound CALLS edge
    count with full qualified names (parent chain) and SymbolKind;
    NetworkX fallback uses v0.1 PageRank-on-name."""
    graph_rows = _graph_key_definitions(facts, limit)
    if graph_rows is not None:
        return [
            "## Key definitions",
            "",
            confidence_note(INFERRED),
            "",
            "Symbols ranked by inbound `CALLS` count (the call-graph resolver). "
            "Definitions are EXTRACTED; the ranking is the derivation.",
            "",
            md_table(["Symbol", "Kind", "Defined in", "Callers"], graph_rows),
            "",
        ]
    rows: list[list[str]] = []
    for definition in facts.ranked.definitions[:limit]:
        category = definition.tags[0].category if definition.tags else "—"
        rows.append(
            [
                f"`{definition.name}`",
                category,
                f"`{definition.rel_path}`",
                f"{definition.rank:.4f}",
            ]
        )
    return [
        "## Key definitions",
        "",
        confidence_note(INFERRED),
        "",
        "Symbols ranked by inbound dependency mass. Definitions are "
        "EXTRACTED; the ranking is the derivation.",
        "",
        md_table(["Symbol", "Kind", "Defined in", "Rank"], rows),
        "",
    ]


def _graph_key_definitions(facts: RepoFacts, limit: int) -> list[list[str]] | None:
    """DEC-030 graph-mode: top symbols by inbound CALLS. Each row carries
    the full qualified name (parent chain via DEC-023) and the
    SymbolKind from the graph (more accurate than the v0.1 first-tag
    category guess)."""
    if facts.graph_db_path is None:
        return None
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[:CALLS]->(callee:Symbol) "
                    "RETURN callee.qualified_name, callee.kind, "
                    "callee.file_path, count(caller) AS inbound "
                    "ORDER BY inbound DESC, callee.qualified_name "
                    f"LIMIT {limit}"
                )
            )
    except Exception:  # pragma: no cover
        return None
    if not rows:
        return []
    body: list[list[str]] = []
    for qn, kind, fp, inbound in rows:
        # Show the qn_local (everything after ``<file>::``) so the
        # parent chain stays readable.
        local = qn.split("::", 1)[-1]
        body.append([f"`{local}`", kind, f"`{fp}`", str(int(inbound))])
    return body
