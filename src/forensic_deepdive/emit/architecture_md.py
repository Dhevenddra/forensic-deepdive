"""ARCHITECTURE.md — a system-level cross-boundary view (DEC-090).

A **separate on-demand surface**, NOT one of the five contract artifacts — exactly
as ``forensic visualize`` (DEC-039) and ``serve --ui`` (DEC-053) are. It renders the
cross-boundary graph (the DEC-043/055 ``Endpoint`` join surfaced as ``ROUTES_TO``,
plus ``INJECTS`` DI and ``PERSISTS_TO`` ORM edges, with ``DbTable`` stores) as a
bounded, confidence-styled Mermaid flowchart so a human can *validate* the graph —
a wrong edge here is a wrong edge everywhere. It reuses the DEC-039 confidence→dash
mapping (``_DASH``) and leaf-label helper; it adds no node type and does not touch
``base.join``/``trace``/``serve``/the five emitters. The five goldens stay
byte-identical; this file has its own golden.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.emit.common import RepoFacts, confidence_banner, footer
from forensic_deepdive.emit.mermaid import _DASH, _label

ARCHITECTURE_FILENAME = "ARCHITECTURE.md"
DEFAULT_MAX_NODES = 40
_CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}

_HEAD_NOTE = (
    "> System-level **cross-boundary** view: client/handler routes, dependency "
    "injection, and data stores.\n"
    "> **Not one of the five contract artifacts** — a regenerated human-validation "
    "surface (DEC-090), like `forensic visualize` / `serve --ui`. Use it to sanity-check "
    "the graph: a wrong edge here is a wrong edge everywhere."
)

_LEGEND = (
    "**Legend.** Edge style encodes confidence (DEC-015): solid = `EXTRACTED`, "
    "dashed = `INFERRED`, dotted = `AMBIGUOUS`. `[(cylinder)]` nodes are database "
    "tables. Edge kinds: `ROUTES_TO` (labelled with the endpoint — a frontend/client "
    "call joined to its backend handler), `injects` (DI binding), `persists` (ORM "
    "model → table)."
)


def render_architecture(facts: RepoFacts, *, max_nodes: int = DEFAULT_MAX_NODES) -> str:
    """Render the full ARCHITECTURE.md document (deterministic)."""
    head = [
        f"# ARCHITECTURE — {facts.repo_name}",
        "",
        _HEAD_NOTE,
        confidence_banner(),
        "",
    ]
    if facts.graph_db_path is None:
        body = ["_No graph database — run `forensic extract` to build the architecture view._", ""]
        return "\n".join([*head, *body, footer(facts)]) + "\n"

    edges = _collect(facts.graph_db_path)
    if not edges:
        body = [
            "## No cross-boundary architecture detected",
            "",
            "No HTTP/MCP/gRPC/messaging routes, dependency-injection bindings, or ORM "
            "persistence were found — this repository's structure is intra-process. See "
            "`MAP.md` and `HOTPATHS.md` for its call graph and central modules.",
            "",
        ]
        return "\n".join([*head, *body, footer(facts)]) + "\n"

    body = ["## Cross-boundary architecture", "", *_render(edges, max_nodes), "", _LEGEND, ""]
    return "\n".join([*head, *body, footer(facts)]) + "\n"


def architecture_for_db(
    db_path: Path,
    repo_name: str,
    *,
    generated_at: datetime | None = None,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> str:
    """Render ARCHITECTURE.md from a graph DB alone — the standalone ``forensic
    diagram`` path. The emitter only needs ``repo_name`` + ``graph_db_path`` +
    ``generated_at``, so a minimal RepoFacts (empty graph/history) is built rather
    than re-running the whole pipeline."""
    from forensic_deepdive.history.git_archaeology import GitHistory
    from forensic_deepdive.static.graph import build_symbol_graph
    from forensic_deepdive.static.pagerank import rank_files

    sg = build_symbol_graph([])
    facts = RepoFacts(
        repo_path=Path(db_path).parent,
        repo_name=repo_name,
        generated_at=generated_at or datetime.now(UTC),
        file_count=0,
        language_breakdown={},
        tags=[],
        symbol_graph=sg,
        ranked=rank_files(sg),
        history=GitHistory(
            repo_path=Path(db_path).parent,
            is_git_repo=False,
            total_commits=0,
            first_commit=None,
            last_commit=None,
            contributors=[],
            churn=[],
        ),
        graph_db_path=Path(db_path),
    )
    return render_architecture(facts, max_nodes=max_nodes)


# ---------------------------------------------------------------------------
# Edge collection
# ---------------------------------------------------------------------------


def _collect(db_path) -> list[tuple[str, str, str, str, str, str, str, bool]]:
    """Cross-boundary edges as
    ``(src_key, src_label, dst_key, dst_label, etype, edge_label, confidence, dst_is_store)``.
    Sorted EXTRACTED-first, then etype/src/dst — deterministic."""
    from forensic_deepdive.graph import LadybugStore

    out: list[tuple[str, str, str, str, str, str, str, bool]] = []
    try:
        with LadybugStore(db_path) as store:
            for c, p, endpoint, conf in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            ):
                out.append(
                    (
                        c,
                        _label(c),
                        p,
                        _label(p),
                        "ROUTES_TO",
                        _endpoint_label(endpoint),
                        conf,
                        False,
                    )
                )
            for a, b, conf in store.query(
                "MATCH (a:Symbol)-[r:INJECTS]->(b:Symbol) "
                "RETURN a.qualified_name, b.qualified_name, r.confidence"
            ):
                out.append((a, _label(a), b, _label(b), "INJECTS", "injects", conf, False))
            for m, name, conf in store.query(
                "MATCH (m:Symbol)-[r:PERSISTS_TO]->(t:DbTable) "
                "RETURN m.qualified_name, t.name, r.confidence"
            ):
                out.append(
                    (m, _label(m), f"table::{name}", name, "PERSISTS_TO", "persists", conf, True)
                )
    except Exception:  # pragma: no cover — degrade if the .lbug is malformed
        return []
    out.sort(key=lambda e: (-_CONF_RANK.get(e[6], 0), e[4], e[0], e[2], e[5]))
    return out


def _endpoint_label(endpoint: str) -> str:
    """A clean edge label from a normalized endpoint key (``http::GET::/path`` →
    ``http GET /path``). Confidence is carried by the dash style, not the text."""
    return (endpoint or "ROUTES_TO").replace("::", " ").strip()


# ---------------------------------------------------------------------------
# Diagram rendering
# ---------------------------------------------------------------------------


def _render(
    edges: list[tuple[str, str, str, str, str, str, str, bool]], max_nodes: int
) -> list[str]:
    """Bounded Mermaid flowchart. Admits nodes greedily in confidence order until
    the node cap, keeping edges whose endpoints both fit (summarize-and-truncate,
    never silent-drop)."""
    cap = max(int(max_nodes), 2)
    admitted: dict[str, tuple[str, bool]] = {}  # key -> (label, is_store)
    kept: list[tuple[str, str, str, str]] = []  # (src, dst, edge_label, conf)
    dropped = 0
    for src, slabel, dst, dlabel, _etype, elabel, conf, store_dst in edges:
        new = [k for k in (src, dst) if k not in admitted]
        if len(admitted) + len(new) > cap:
            dropped += 1
            continue
        admitted.setdefault(src, (slabel, False))
        admitted.setdefault(dst, (dlabel, store_dst))
        kept.append((src, dst, elabel, conf))

    ids = {k: f"n{i}" for i, k in enumerate(sorted(admitted))}
    lines = ["```mermaid", "flowchart LR"]
    for k in sorted(admitted):
        label, is_store = admitted[k]
        safe = label.replace('"', "'")
        lines.append(f'    {ids[k]}[("{safe}")]' if is_store else f'    {ids[k]}["{safe}"]')
    if dropped:
        lines.append(f'    nMore["… (+{dropped} more edges beyond the {cap}-node cap)"]')

    dash_lines: list[str] = []
    for i, (src, dst, elabel, conf) in enumerate(kept):
        lines.append(f'    {ids[src]} -->|"{elabel}"| {ids[dst]}')
        if conf in _DASH:
            dash_lines.append(f"    linkStyle {i} stroke-dasharray: {_DASH[conf]}")
    lines.extend(dash_lines)
    lines.append("```")
    return lines
