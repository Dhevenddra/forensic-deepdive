"""MCP server with 5 composite tools (DEC-016).

Built on FastMCP. The tools are deliberately *composite* — each one
fires multiple Cypher queries internally and returns a synthesized
payload. Anthropic / Harness / Klavis all converge on "fewer, richer
tools beat many narrow ones" for agent ergonomics; this module is
where DEC-016 lands.

Tool descriptions are kept under PRD's ≤200-token budget per tool so
the context-window overhead on Claude Code / Cursor / Codex stays
small.

The server is stateless beyond the graph — each tool call opens its
own LadybugStore, queries, and returns. That keeps thread-safety
trivial and matches the "graph IS the source of truth" semantics
(DEC-013 / DEC-030).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.insights import Insight, JsonlInsightStore

DEFAULT_DEPTH = 3
DEFAULT_MAX_DEPTH = 10
DEFAULT_MIN_CONFIDENCE = "INFERRED"

# DEC-019 — insight store lives at ``<repo>/.deepdive/insights.jsonl``
# next to the graph DB. Resolved from the graph_db_path by walking up to
# the ``.deepdive`` parent.
_INSIGHT_SUBPATH = "insights.jsonl"


def _insight_store_path(graph_db_path: Path) -> Path:
    """Resolve the insight store path from the graph DB path. The graph
    lives at ``<repo>/.deepdive/graph.lbug``; insights live alongside at
    ``<repo>/.deepdive/insights.jsonl``."""
    return Path(graph_db_path).parent / _INSIGHT_SUBPATH


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_CONFIDENCE_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}


def _conf_rank(level: str) -> int:
    return _CONFIDENCE_RANK.get(level, 0)


def _passes_min_confidence(level: str, minimum: str) -> bool:
    return _conf_rank(level) >= _conf_rank(minimum)


def _resolve_symbol_query(store: LadybugStore, query: str) -> list[dict[str, Any]]:
    """Find Symbols matching *query*. Tries exact qualified_name match
    first, then exact bare-name match, then substring."""
    # Exact qualified name.
    rows = list(
        store.query(
            "MATCH (s:Symbol {qualified_name: $q}) "
            "RETURN s.qualified_name, s.kind, s.file_path, "
            "s.line_start, s.line_end LIMIT 25",
            {"q": query},
        )
    )
    if rows:
        return [_symbol_row(r) for r in rows]
    # Exact bare name (everything after the last ``::``).
    rows = list(
        store.query(
            "MATCH (s:Symbol) WHERE s.qualified_name ENDS WITH $bare "
            "RETURN s.qualified_name, s.kind, s.file_path, "
            "s.line_start, s.line_end LIMIT 25",
            {"bare": f"::{query}"},
        )
    )
    if rows:
        return [_symbol_row(r) for r in rows]
    # Substring match.
    rows = list(
        store.query(
            "MATCH (s:Symbol) WHERE s.qualified_name CONTAINS $q "
            "RETURN s.qualified_name, s.kind, s.file_path, "
            "s.line_start, s.line_end LIMIT 25",
            {"q": query},
        )
    )
    return [_symbol_row(r) for r in rows]


def _symbol_row(row: list) -> dict[str, Any]:
    qn, kind, fp, ls, le = row
    return {
        "qualified_name": qn,
        "kind": kind,
        "file_path": fp,
        "line_start": int(ls),
        "line_end": int(le),
    }


# ---------------------------------------------------------------------------
# Tool 1: impact(symbol, depth, direction, min_confidence)
# ---------------------------------------------------------------------------


def impact(
    db_path: Path,
    symbol: str,
    *,
    depth: int = DEFAULT_DEPTH,
    direction: str = "upstream",
    min_confidence: str = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Blast-radius analysis for *symbol*. PRD §4.5 tool 1 (DEC-016).

    * ``direction="upstream"`` walks INCOMING CALLS (who calls this?).
    * ``direction="downstream"`` walks OUTGOING CALLS (what does this
      call?).

    Returns ``{matches, depth_buckets, summary}`` where ``depth_buckets``
    is a list of lists — bucket ``i`` is the set of symbols ``i+1`` hops
    away. Each entry carries the resolved confidence.
    """
    if direction not in ("upstream", "downstream"):
        return {"error": f"direction must be 'upstream' or 'downstream', got {direction!r}"}
    with LadybugStore(db_path) as store:
        matches = _resolve_symbol_query(store, symbol)
        if not matches:
            return {"matches": [], "depth_buckets": [], "summary": {"unresolved": True}}
        # BFS from each match. Aggregate buckets across all matches.
        buckets: list[set[tuple[str, str, str]]] = [set() for _ in range(depth)]
        visited: set[str] = {m["qualified_name"] for m in matches}
        frontier: set[str] = set(visited)
        for hop in range(depth):
            if not frontier:
                break
            cypher = (
                "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                "WHERE caller.qualified_name IN $qns RETURN "
                "callee.qualified_name, callee.kind, r.confidence"
                if direction == "downstream"
                else "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                "WHERE callee.qualified_name IN $qns RETURN "
                "caller.qualified_name, caller.kind, r.confidence"
            )
            rows = list(store.query(cypher, {"qns": list(frontier)}))
            next_frontier: set[str] = set()
            for qn, kind, conf in rows:
                if not _passes_min_confidence(conf, min_confidence):
                    continue
                if qn in visited:
                    continue
                buckets[hop].add((qn, kind, conf))
                next_frontier.add(qn)
            visited.update(next_frontier)
            frontier = next_frontier
        depth_buckets = [
            sorted(
                [{"qualified_name": qn, "kind": k, "confidence": c} for qn, k, c in b],
                key=lambda r: r["qualified_name"],
            )
            for b in buckets
        ]
        total = sum(len(b) for b in depth_buckets)
        return {
            "matches": matches,
            "direction": direction,
            "depth": depth,
            "min_confidence": min_confidence,
            "depth_buckets": depth_buckets,
            "summary": {
                "total_reached": total,
                "by_confidence": dict(Counter(c for b in buckets for _, _, c in b)),
            },
        }


# ---------------------------------------------------------------------------
# Tool 2: context(symbol) — Glass-style kitchen-sink
# ---------------------------------------------------------------------------


def context(db_path: Path, symbol: str) -> dict[str, Any]:
    """One-tool-call 360° view of a symbol. PRD §4.5 tool 3 (DEC-016).

    Returns the symbol's definition + callers + callees + members +
    siblings + recent commits + dominant author. Single composite call
    replaces the typical 5-6 narrower queries an agent would otherwise
    chain.
    """
    with LadybugStore(db_path) as store:
        matches = _resolve_symbol_query(store, symbol)
        if not matches:
            return {"matches": [], "unresolved": True}
        target = matches[0]
        qn = target["qualified_name"]
        # Callers (incoming CALLS).
        callers = [
            {
                "qualified_name": qn_,
                "kind": kind,
                "file_path": fp,
                "confidence": conf,
            }
            for qn_, kind, fp, conf in store.query(
                "MATCH (caller:Symbol)-[r:CALLS]->(:Symbol {qualified_name: $q}) "
                "RETURN caller.qualified_name, caller.kind, caller.file_path, r.confidence "
                "ORDER BY caller.qualified_name LIMIT 50",
                {"q": qn},
            )
        ]
        # Callees (outgoing CALLS).
        callees = [
            {
                "qualified_name": qn_,
                "kind": kind,
                "file_path": fp,
                "confidence": conf,
            }
            for qn_, kind, fp, conf in store.query(
                "MATCH (:Symbol {qualified_name: $q})-[r:CALLS]->(callee:Symbol) "
                "RETURN callee.qualified_name, callee.kind, callee.file_path, r.confidence "
                "ORDER BY callee.qualified_name LIMIT 50",
                {"q": qn},
            )
        ]
        # Parent (MEMBER_OF) + siblings.
        parent_row = list(
            store.query(
                "MATCH (:Symbol {qualified_name: $q})-[:MEMBER_OF]->(p:Symbol) "
                "RETURN p.qualified_name LIMIT 1",
                {"q": qn},
            )
        )
        parent = parent_row[0][0] if parent_row else None
        siblings: list[str] = []
        if parent is not None:
            siblings = [
                row[0]
                for row in store.query(
                    "MATCH (sib:Symbol)-[:MEMBER_OF]->"
                    "(:Symbol {qualified_name: $p}) "
                    "WHERE sib.qualified_name <> $q "
                    "RETURN sib.qualified_name ORDER BY sib.qualified_name LIMIT 20",
                    {"p": parent, "q": qn},
                )
            ]
        # Members (if target is a class/interface — outgoing MEMBER_OF
        # from members points to target).
        members = [
            row[0]
            for row in store.query(
                "MATCH (m:Symbol)-[:MEMBER_OF]->(:Symbol {qualified_name: $q}) "
                "RETURN m.qualified_name ORDER BY m.qualified_name LIMIT 50",
                {"q": qn},
            )
        ]
        # EXTENDS / IMPLEMENTS for class context.
        extends = [
            row[0]
            for row in store.query(
                "MATCH (:Symbol {qualified_name: $q})-[:EXTENDS]->(p:Symbol) "
                "RETURN p.qualified_name ORDER BY p.qualified_name",
                {"q": qn},
            )
        ]
        implements = [
            row[0]
            for row in store.query(
                "MATCH (:Symbol {qualified_name: $q})-[:IMPLEMENTS]->(i:Symbol) "
                "RETURN i.qualified_name ORDER BY i.qualified_name",
                {"q": qn},
            )
        ]
        # Recent commits touching the symbol's file.
        recent_commits = [
            {"sha": sha, "date": date, "author": author, "message": msg}
            for sha, date, author, msg in store.query(
                "MATCH (f:File {path: $fp})-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "MATCH (c)-[:AUTHORED_BY]->(a:Author) "
                "RETURN c.sha, c.date, a.name, c.message "
                "ORDER BY c.date DESC LIMIT 5",
                {"fp": target["file_path"]},
            )
        ]
        # Dominant author of the symbol's file.
        author_rows = list(
            store.query(
                "MATCH (f:File {path: $fp})-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "MATCH (c)-[:AUTHORED_BY]->(a:Author) "
                "RETURN a.name, count(c) AS n ORDER BY n DESC LIMIT 1",
                {"fp": target["file_path"]},
            )
        )
        dominant_author = (
            {"name": author_rows[0][0], "commits": int(author_rows[0][1])} if author_rows else None
        )
        # DEC-019: surface up-to-3 most-recent insights for this symbol.
        # Always present (even when empty) — the field is part of the
        # agent-facing contract; surprising agents with a sometimes-
        # absent field destroys trust.
        insight_store = JsonlInsightStore(_insight_store_path(db_path))
        recent_insights = [i.to_dict() for i in insight_store.recall(qn, limit=3)]
        return {
            "symbol": target,
            "all_matches": matches,
            "parent": parent,
            "members": members,
            "siblings": siblings,
            "callers": callers,
            "callees": callees,
            "extends": extends,
            "implements": implements,
            "recent_commits": recent_commits,
            "dominant_author": dominant_author,
            "recent_insights": recent_insights,
        }


# ---------------------------------------------------------------------------
# Tool 3: archaeology(file_or_symbol)
# ---------------------------------------------------------------------------


def archaeology(db_path: Path, file_or_symbol: str) -> dict[str, Any]:
    """Git-history view of a file (or a symbol's enclosing file).
    PRD §4.5 tool 5 (DEC-016) — the wedge GitNexus structurally
    cannot match.

    Returns churn, top authors with %, co-change cluster, defect
    proximity, bus factor, recent commits."""
    with LadybugStore(db_path) as store:
        # Resolve input: try file directly, then look up as symbol.
        target_files = [
            row[0]
            for row in store.query(
                "MATCH (f:File {path: $p}) RETURN f.path",
                {"p": file_or_symbol},
            )
        ]
        if not target_files:
            sym = _resolve_symbol_query(store, file_or_symbol)
            if not sym:
                return {"unresolved": True, "query": file_or_symbol}
            target_files = [sym[0]["file_path"]]
        target_file = target_files[0]

        # Churn count.
        churn_rows = list(
            store.query(
                "MATCH (:File {path: $p})-[:TOUCHED_BY_COMMIT]->(c:Commit) RETURN count(c)",
                {"p": target_file},
            )
        )
        total_commits = int(churn_rows[0][0]) if churn_rows else 0

        # Top authors by commit count.
        author_rows = list(
            store.query(
                "MATCH (:File {path: $p})-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "MATCH (c)-[:AUTHORED_BY]->(a:Author) "
                "RETURN a.name, a.email_canonical, count(c) AS n "
                "ORDER BY n DESC, a.name LIMIT 10",
                {"p": target_file},
            )
        )
        authors = [
            {
                "name": name,
                "email": email,
                "commits": int(n),
                "share_pct": round(100.0 * int(n) / max(total_commits, 1), 1),
            }
            for name, email, n in author_rows
        ]

        # Co-change cluster.
        co_changes = [
            {"file": other, "shared_commits": float(freq)}
            for other, freq in store.query(
                "MATCH (:File {path: $p})-[r:CO_CHANGES_WITH]-(b:File) "
                "RETURN b.path, r.frequency ORDER BY r.frequency DESC, b.path LIMIT 10",
                {"p": target_file},
            )
        ]

        # Defect proximity: commits whose message contains fix / bug
        # markers. real-ladybug supports CONTAINS for STRING.
        defect_rows = list(
            store.query(
                "MATCH (:File {path: $p})-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "WHERE c.message CONTAINS 'fix' OR c.message CONTAINS 'bug' "
                "OR c.message CONTAINS 'regression' OR c.message CONTAINS 'patch' "
                "RETURN count(c)",
                {"p": target_file},
            )
        )
        defect_count = int(defect_rows[0][0]) if defect_rows else 0
        defect_proximity = round(defect_count / max(total_commits, 1), 3) if total_commits else 0.0

        # Bus factor: number of authors who collectively account for
        # > 80% of commits.
        bus_factor = _bus_factor(authors)

        # Recent commits.
        recent = [
            {"sha": sha, "date": date, "author": author, "message": msg}
            for sha, date, author, msg in store.query(
                "MATCH (:File {path: $p})-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "MATCH (c)-[:AUTHORED_BY]->(a:Author) "
                "RETURN c.sha, c.date, a.name, c.message "
                "ORDER BY c.date DESC LIMIT 5",
                {"p": target_file},
            )
        ]
        return {
            "file": target_file,
            "total_commits": total_commits,
            "authors": authors,
            "bus_factor": bus_factor,
            "co_change_cluster": co_changes,
            "defect_proximity": defect_proximity,
            "defect_commits": defect_count,
            "recent_commits": recent,
        }


def _bus_factor(authors: list[dict[str, Any]], threshold: float = 80.0) -> int:
    """Smallest set of authors covering >= threshold% of commits."""
    cumulative = 0.0
    for i, a in enumerate(authors, start=1):
        cumulative += a["share_pct"]
        if cumulative >= threshold:
            return i
    return len(authors)


# ---------------------------------------------------------------------------
# Tool 4: flow(entry_point, max_depth)
# ---------------------------------------------------------------------------


def flow(
    db_path: Path,
    entry_point: str,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> dict[str, Any]:
    """DFS over CALLS edges from any symbol matching *entry_point*.
    PRD §4.5 tool 4 (DEC-016).

    Returns a list of execution-path traces (each a list of
    ``{symbol, file, depth, confidence}`` entries). Stops at
    ``max_depth`` or when a cycle is hit (the same callee revisits
    via a different path).
    """
    with LadybugStore(db_path) as store:
        entries = _resolve_symbol_query(store, entry_point)
        if not entries:
            return {"entry_points": [], "paths": [], "unresolved": True}
        paths: list[list[dict[str, Any]]] = []
        for entry in entries:
            for path in _walk_flow(store, entry, max_depth):
                paths.append(path)
                if len(paths) >= 25:  # cap total path count
                    break
            if len(paths) >= 25:
                break
        return {"entry_points": entries, "max_depth": max_depth, "paths": paths}


def _walk_flow(
    store: LadybugStore, entry: dict[str, Any], max_depth: int
) -> list[list[dict[str, Any]]]:
    """Recursive DFS yielding one entry per leaf or max-depth path."""
    results: list[list[dict[str, Any]]] = []
    initial = {
        "symbol": entry["qualified_name"],
        "file": entry["file_path"],
        "depth": 0,
        "confidence": "EXTRACTED",
    }
    stack: list[tuple[list[dict[str, Any]], set[str]]] = [([initial], {entry["qualified_name"]})]
    while stack:
        path, visited = stack.pop()
        if path[-1]["depth"] >= max_depth:
            results.append(path)
            continue
        last_qn = path[-1]["symbol"]
        callees = list(
            store.query(
                "MATCH (:Symbol {qualified_name: $q})-[r:CALLS]->(c:Symbol) "
                "RETURN c.qualified_name, c.file_path, r.confidence "
                "ORDER BY c.qualified_name LIMIT 5",
                {"q": last_qn},
            )
        )
        if not callees:
            results.append(path)
            continue
        for qn, fp, conf in callees:
            if qn in visited:
                # Cycle — terminate this branch with a marker.
                results.append(
                    path
                    + [
                        {
                            "symbol": qn,
                            "file": fp,
                            "depth": path[-1]["depth"] + 1,
                            "confidence": conf,
                            "cycle": True,
                        }
                    ]
                )
                continue
            new_path = path + [
                {
                    "symbol": qn,
                    "file": fp,
                    "depth": path[-1]["depth"] + 1,
                    "confidence": conf,
                }
            ]
            stack.append((new_path, visited | {qn}))
    return results


# ---------------------------------------------------------------------------
# Tool 5: query(natural_language | cypher)
# ---------------------------------------------------------------------------


def query(
    db_path: Path,
    *,
    cypher: str | None = None,
    natural_language: str | None = None,
    semantic: bool = False,
) -> dict[str, Any]:
    """Run a raw Cypher query, OR a hybrid NL search. PRD §4.5 tool 2 / Item E
    (DEC-016 / DEC-038).

    The natural-language path fuses three retrievers — always-on lexical
    (SQLite FTS5/BM25) + always-on structural (graph proximity + CALLS
    in-degree) + opt-in offline semantic (ONNX, ``semantic=True`` and the
    ``[semantic]`` extra) — by RRF (k=60), then shapes the output (boost
    implementation, demote test/vendored/generated). Results are
    confidence-tagged with per-hit provenance; ``retrievers_active`` +
    ``degraded`` say which tiers actually ran (honest degraded mode).
    """
    if cypher is None and natural_language is None:
        return {"error": "pass cypher= or natural_language="}
    if cypher is not None and natural_language is not None:
        return {"error": "pass one of cypher= or natural_language=, not both"}
    if cypher is not None:
        with LadybugStore(db_path) as store:
            try:
                rows = list(store.query(cypher))
            except Exception as exc:
                return {"error": str(exc), "cypher": cypher}
            return {"cypher": cypher, "rows": rows, "row_count": len(rows)}
    # natural_language path — hybrid retrieval (DEC-038).
    from forensic_deepdive.query import hybrid_query

    return hybrid_query(db_path, natural_language, semantic=semantic)


# ---------------------------------------------------------------------------
# Tool 6: record_insight(symbol, claim, evidence, verified_by) — DEC-019
# ---------------------------------------------------------------------------


def record_insight(
    graph_db_path: Path,
    symbol: str,
    claim: str,
    evidence: str,
    verified_by: str = "ai",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Persist one durable agent learning about this codebase
    (DEC-019).

    Appends to the JSONL insight store at ``.deepdive/insights.jsonl``.
    Returns the persisted insight as a dict so the agent can verify
    what was stored. ``verified_by`` must be one of the four allowed
    values; an invalid value returns an error payload rather than
    raising (matches the ``query()`` error-as-payload pattern from
    DEC-016)."""
    try:
        insight = Insight.now(
            symbol=symbol,
            claim=claim,
            evidence=evidence,
            verified_by=verified_by,
            session_id=session_id,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    path = _insight_store_path(graph_db_path)
    store = JsonlInsightStore(path)
    store.record(insight)
    return {"recorded": insight.to_dict(), "path": str(path)}


# ---------------------------------------------------------------------------
# Tool 7: recall_insights(symbol, since=, limit=) — DEC-019
# ---------------------------------------------------------------------------


def recall_insights(
    graph_db_path: Path,
    symbol: str,
    since: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return prior agent learnings matching *symbol* (DEC-019).

    Substring match on the stored insight's ``symbol`` field. Newest
    first, capped at *limit*. ``since`` is an ISO timestamp — when
    provided, only insights recorded at or after that timestamp are
    returned."""
    path = _insight_store_path(graph_db_path)
    store = JsonlInsightStore(path)
    matches = store.recall(symbol, since=since, limit=limit)
    return {
        "symbol": symbol,
        "insights": [m.to_dict() for m in matches],
        "count": len(matches),
    }


# ---------------------------------------------------------------------------
# Server factory + stdio entry point
# ---------------------------------------------------------------------------


def make_server(graph_db_path: Path) -> FastMCP:
    """Build a FastMCP server with the 5 composite tools registered."""
    server = FastMCP(
        "forensic-deepdive",
        instructions=(
            "Query a forensic-deepdive code knowledge graph for a "
            "repository. Five composite tools: impact (blast radius), "
            "context (one-call symbol overview), archaeology (git history), "
            "flow (execution trace), query (Cypher / substring search)."
        ),
    )

    @server.tool()
    def impact_tool(
        symbol: str,
        depth: int = DEFAULT_DEPTH,
        direction: str = "upstream",
        min_confidence: str = DEFAULT_MIN_CONFIDENCE,
    ) -> dict[str, Any]:
        """Blast-radius analysis for a symbol. Walks CALLS edges in the
        given direction (upstream=callers, downstream=callees) up to
        ``depth`` hops. Returns depth-bucketed lists with confidence
        labels. Use to answer "what breaks if I change X?"."""
        return impact(
            graph_db_path,
            symbol,
            depth=depth,
            direction=direction,
            min_confidence=min_confidence,
        )

    @server.tool()
    def context_tool(symbol: str) -> dict[str, Any]:
        """One-call 360° view of a symbol: definition + callers + callees
        + members + siblings + extends/implements + recent commits +
        dominant author. Use to answer "what does X do and who owns it?"."""
        return context(graph_db_path, symbol)

    @server.tool()
    def archaeology_tool(file_or_symbol: str) -> dict[str, Any]:
        """Git-history view of a file (or a symbol's enclosing file):
        churn, top authors with share, co-change cluster, defect
        proximity, bus factor, recent commits. Use to answer "who owns
        this and how risky is it?"."""
        return archaeology(graph_db_path, file_or_symbol)

    @server.tool()
    def flow_tool(entry_point: str, max_depth: int = DEFAULT_MAX_DEPTH) -> dict[str, Any]:
        """DFS over CALLS edges from any symbol matching ``entry_point``
        up to ``max_depth`` hops. Returns execution-path traces. Use
        to answer "trace what happens when X is invoked"."""
        return flow(graph_db_path, entry_point, max_depth=max_depth)

    @server.tool()
    def query_tool(
        cypher: str | None = None,
        natural_language: str | None = None,
        semantic: bool = False,
    ) -> dict[str, Any]:
        """Run a raw Cypher query against the LadybugDB graph, OR pass
        ``natural_language`` for a hybrid search (lexical BM25 + structural
        graph signal + opt-in offline semantic, fused by RRF and shaped to
        rank implementations above tests). Results carry provenance +
        confidence; ``retrievers_active``/``degraded`` report which tiers ran.
        Set ``semantic=True`` to add the ONNX tier (needs the ``[semantic]``
        extra). Use Cypher for precise queries; natural_language for
        discovery."""
        return query(
            graph_db_path,
            cypher=cypher,
            natural_language=natural_language,
            semantic=semantic,
        )

    @server.tool()
    def record_insight_tool(
        symbol: str,
        claim: str,
        evidence: str,
        verified_by: str = "ai",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist one durable learning about this codebase (DEC-019).
        Use after verifying a hypothesis, fixing a bug, or noticing a
        cross-session pattern. ``verified_by`` must be one of: "human",
        "static", "test", "ai". Surfaces back via context() and
        recall_insights() on future sessions."""
        return record_insight(
            graph_db_path,
            symbol,
            claim,
            evidence,
            verified_by=verified_by,
            session_id=session_id,
        )

    @server.tool()
    def recall_insights_tool(
        symbol: str,
        since: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return prior learnings about *symbol* recorded via
        record_insight (DEC-019). Newest first, capped at ``limit``.
        ``since`` (ISO timestamp) filters to insights at or after that
        time. Use when starting work on a symbol to surface what past
        sessions learned."""
        return recall_insights(graph_db_path, symbol, since=since, limit=limit)

    return server


async def serve_stdio(graph_db_path: Path) -> None:
    """Run the MCP server over stdio. Entry point for
    ``forensic serve --transport=stdio``."""
    server = make_server(graph_db_path)
    await server.run_stdio_async()


def run_stdio(graph_db_path: Path) -> None:
    """Sync wrapper for callers that don't have an event loop."""
    asyncio.run(serve_stdio(graph_db_path))
