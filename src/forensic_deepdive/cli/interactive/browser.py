"""Textual TUI graph browser — ``forensic browse`` (DEC-100, v0.9 Track A step 2).

The loopback-free terminal sibling of ``serve --ui``: a full-screen, read-only
browser over Symbol / File / Endpoint nodes with filters (substring, language,
confidence, edge type), a context detail pane, and impact/flow jumps — no
browser, no server, works over SSH.

This module is **textual-free** on purpose: it holds the snapshot loader and
the ``run_browse`` entry so it imports cleanly without the ``[interactive]``
extra. The Textual ``App`` itself lives in ``browser_app.py`` (which imports
textual at module top) and is only imported once the probe succeeds.

Store lifecycle: the snapshot is loaded through ONE store open/close *before*
the App starts; per-selection detail (``context``/``impact``/``flow``) reuses
the existing MCP tool functions, which open per call — so the browser never
holds a live handle while the UI runs (no second-handle locking, and the tools
stay untouched per the frozen contract).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forensic_deepdive.cli.interactive import INSTALL_HINT
from forensic_deepdive.cli.style import get_console
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.static.resolver import module_display_name

# DEC-039 node-cap carried over: bound what the widget loads, never silent-drop
# ("showing N of M" is rendered in the status line).
DEFAULT_NODE_CAP = 500

# Edge types a Symbol row can be filtered by (presence of >=1 such edge).
EDGE_TYPE_FILTERS = ("CALLS", "ROUTES_TO", "HANDLES", "CALLS_ENDPOINT", "INJECTS")
CONFIDENCE_LEVELS = ("EXTRACTED", "INFERRED", "AMBIGUOUS")


@dataclass(frozen=True, slots=True)
class NodeRow:
    """One browsable node, pre-shaped for the table."""

    key: str  # "sym:<qn>" | "file:<path>" | "ep:<contract_id>" (build_node_detail keys)
    name: str  # display name (DEC-104 module dotted-path for module scopes)
    kind: str  # symbol kind / file role / endpoint protocol
    location: str  # file path / language / METHOD path
    language: str  # "" when not applicable
    confidences: frozenset[str]  # confidence tiers present on this node's edges
    edge_types: frozenset[str]  # edge types touching this node (symbols only)


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    """Everything the App renders, loaded in one store open/close."""

    db_path: Path
    symbols: tuple[NodeRow, ...]
    files: tuple[NodeRow, ...]
    endpoints: tuple[NodeRow, ...]
    totals: dict[str, int]  # {"symbol": M, "file": M, "endpoint": M} — full graph counts
    languages: tuple[str, ...]
    node_cap: int

    def truncated(self, kind: str) -> bool:
        shown = {"symbol": self.symbols, "file": self.files, "endpoint": self.endpoints}[kind]
        return self.totals.get(kind, 0) > len(shown)


def _count(store: LadybugStore, cypher: str) -> int:
    rows = list(store.query(cypher))
    return int(rows[0][0]) if rows else 0


def load_snapshot(db_path: Path, max_nodes: int = DEFAULT_NODE_CAP) -> GraphSnapshot:
    """Load the bounded, read-only node snapshot (one store open/close)."""
    cap = max(1, int(max_nodes))
    with LadybugStore(db_path) as store:
        totals = {
            "symbol": _count(store, "MATCH (s:Symbol) RETURN count(s)"),
            "file": _count(store, "MATCH (f:File) RETURN count(f)"),
            "endpoint": _count(store, "MATCH (e:Endpoint) RETURN count(e)"),
        }
        lang_by_file = {
            path: (lang or "")
            for path, lang in store.query("MATCH (f:File) RETURN f.path, f.language")
        }

        # Symbols: inbound-CALLS-ranked first (the interesting ones on a huge
        # repo), then alphabetical fill to the cap — deterministic either way.
        chosen: list[str] = [
            qn
            for qn, _ in store.query(
                "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) "
                "RETURN s.qualified_name, count(DISTINCT c) AS inbound "
                f"ORDER BY inbound DESC, s.qualified_name LIMIT {cap}"
            )
        ]
        if len(chosen) < cap:
            seen = set(chosen)
            for (qn,) in store.query(
                f"MATCH (s:Symbol) RETURN s.qualified_name ORDER BY s.qualified_name "
                f"LIMIT {cap * 2}"
            ):
                if qn not in seen:
                    seen.add(qn)
                    chosen.append(qn)
                    if len(chosen) >= cap:
                        break

        meta: dict[str, tuple[str, str]] = {}  # qn -> (kind, file_path)
        if chosen:
            for qn, kind, fp in store.query(
                "MATCH (s:Symbol) WHERE s.qualified_name IN $qns "
                "RETURN s.qualified_name, s.kind, s.file_path",
                {"qns": chosen},
            ):
                meta[qn] = (kind or "", fp or "")

        confs: dict[str, set[str]] = {}
        edge_types: dict[str, set[str]] = {}
        if chosen:
            for cypher in (
                "MATCH ()-[r:CALLS]->(s:Symbol) WHERE s.qualified_name IN $qns "
                "RETURN s.qualified_name, r.confidence",
                "MATCH (s:Symbol)-[r:HANDLES]->() WHERE s.qualified_name IN $qns "
                "RETURN s.qualified_name, r.confidence",
            ):
                for qn, conf in store.query(cypher, {"qns": chosen}):
                    if conf:
                        confs.setdefault(qn, set()).add(str(conf))
            for etype in EDGE_TYPE_FILTERS:
                for (qn,) in store.query(
                    f"MATCH (s:Symbol)-[:{etype}]-() WHERE s.qualified_name IN $qns "
                    "RETURN DISTINCT s.qualified_name",
                    {"qns": chosen},
                ):
                    edge_types.setdefault(qn, set()).add(etype)

        symbols = tuple(
            NodeRow(
                key=f"sym:{qn}",
                name=module_display_name(qn) or qn.split("::", 1)[-1],
                kind=meta.get(qn, ("", ""))[0],
                location=meta.get(qn, ("", ""))[1],
                language=lang_by_file.get(meta.get(qn, ("", ""))[1], ""),
                confidences=frozenset(confs.get(qn, set())),
                edge_types=frozenset(edge_types.get(qn, set())),
            )
            for qn in chosen
        )

        files = tuple(
            NodeRow(
                key=f"file:{path}",
                name=path,
                kind=role or "",
                location=lang or "",
                language=lang or "",
                confidences=frozenset(),
                edge_types=frozenset(),
            )
            for path, lang, role in store.query(
                f"MATCH (f:File) RETURN f.path, f.language, f.role ORDER BY f.path LIMIT {cap}"
            )
        )

        ep_confs: dict[str, set[str]] = {}
        for cid, conf in store.query(
            "MATCH ()-[r:HANDLES]->(e:Endpoint) RETURN e.contract_id, r.confidence"
        ):
            if conf:
                ep_confs.setdefault(cid, set()).add(str(conf))
        endpoints = tuple(
            NodeRow(
                key=f"ep:{cid}",
                name=f"{method or '*'} {npath or cid}",
                kind=proto or "",
                location=cid,
                language="",
                confidences=frozenset(ep_confs.get(cid, set())),
                edge_types=frozenset(),
            )
            for cid, proto, method, npath in store.query(
                "MATCH (e:Endpoint) RETURN e.contract_id, e.protocol, e.method, "
                f"e.normalized_path ORDER BY e.contract_id LIMIT {cap}"
            )
        )

        languages = tuple(sorted({lang for lang in lang_by_file.values() if lang}))

    return GraphSnapshot(
        db_path=Path(db_path),
        symbols=symbols,
        files=files,
        endpoints=endpoints,
        totals=totals,
        languages=languages,
        node_cap=cap,
    )


def run_browse(db_path: Path, *, max_nodes: int = DEFAULT_NODE_CAP) -> int:
    """Load the snapshot and run the full-screen browser. Returns an exit code."""
    try:
        import textual  # noqa: F401, PLC0415 — [interactive] extra probe
    except ImportError:
        get_console().print(INSTALL_HINT, markup=False, highlight=False)
        return 1
    console = get_console()
    with console.status("[brand]forensic browse[/brand] — loading the graph …"):
        snapshot = load_snapshot(db_path, max_nodes)
    from forensic_deepdive.cli.interactive.browser_app import GraphBrowser  # noqa: PLC0415

    GraphBrowser(snapshot).run()  # blocking; reclaims the terminal on exit
    return 0
