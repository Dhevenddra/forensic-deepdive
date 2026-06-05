"""Bounded, filtered, deterministic graph payloads for the served UI (DEC-053).

This is the **pure, unit-testable core** of `forensic serve --ui`. It reads the
LadybugStore (DEC-013) and returns a graphology-serialized graph that is
*always* bounded — never the whole graph. The 348k-`CO_CHANGES_WITH`-edge
Superset lesson (research §8) is enforced *structurally* here: node/edge caps
live in the builder, so no filter combination can ask the browser to render
everything.

Three entry points, all deterministic (collect-then-sort → byte-identical JSON
for identical inputs):

* :func:`build_graph_payload` — the bounded/filtered graphology graph.
* :func:`build_node_detail`   — a node's `context`/`trace` panel (reuses the MCP tools).
* :func:`build_meta`          — filter-UI metadata (languages, dirs, edge counts).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forensic_deepdive.graph import LadybugStore

if TYPE_CHECKING:
    from collections.abc import Sequence

# Symbol→Symbol structural edges + Symbol→Endpoint cross-stack edges. ROUTES_TO
# is first by intent: it is the cross-stack headline and gets selection priority.
DEFAULT_EDGE_TYPES: tuple[str, ...] = (
    "ROUTES_TO",
    "CALLS",
    "EXTENDS",
    "IMPLEMENTS",
    "HANDLES",
    "CALLS_ENDPOINT",
)
# CO_CHANGES_WITH (File→File) is the 348k monster — opt-in only, hard-capped by
# frequency when requested.
ALL_EDGE_TYPES: tuple[str, ...] = (*DEFAULT_EDGE_TYPES, "CO_CHANGES_WITH")

_SYMBOL_SYMBOL = frozenset({"CALLS", "EXTENDS", "IMPLEMENTS", "ROUTES_TO"})
_SYMBOL_ENDPOINT = frozenset({"HANDLES", "CALLS_ENDPOINT"})

_CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}

# Default bounds. Generous enough to be useful, small enough that Sigma's WebGL
# force layout stays comfortable (research §8: layout "falls beyond 50k edges").
DEFAULT_MAX_NODES = 300
DEFAULT_MAX_EDGES = 1500
_COCHANGE_CAP = 200  # hard cap on the File-co-change view when opted in

# --- encoding (DEC-053 §4) -------------------------------------------------
# Node base colour by type; Symbol nodes are re-coloured client-side by Louvain
# community. Endpoint/File keep their distinct base colour.
_NTYPE_COLOR = {"symbol": "#4c6ef5", "endpoint": "#ae3ec9", "file": "#868e96"}
# Edge colour: ROUTES_TO is the distinct cross-stack headline colour/weight; the
# rest are shaded by confidence (the DEC-015 taxonomy). WebGL has no edge
# transparency, so weights stay small (research §8).
_ROUTES_TO_COLOR = "#e8590c"
_CONF_COLOR = {"EXTRACTED": "#2f9e44", "INFERRED": "#f08c00", "AMBIGUOUS": "#e03131"}
_CONF_DASHED = {"EXTRACTED": False, "INFERRED": True, "AMBIGUOUS": True}


def _conf_rank(level: str) -> int:
    return _CONF_RANK.get(level, 0)


# ---------------------------------------------------------------------------
# Public: the bounded graph
# ---------------------------------------------------------------------------


def build_graph_payload(
    db_path: Path | str,
    *,
    edge_types: Sequence[str] | None = None,
    min_confidence: str = "AMBIGUOUS",
    language: str | None = None,
    directory: str | None = None,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_edges: int = DEFAULT_MAX_EDGES,
    focus: str | None = None,
) -> dict[str, Any]:
    """Return a bounded, filtered graphology-serialized graph.

    Guarantees (asserted by the test suite):

    * ``len(payload["nodes"]) <= max_nodes`` and ``len(payload["edges"]) <= max_edges``.
    * every edge's ``etype`` is in *edge_types* and confidence rank ``>= min_confidence``.
    * identical inputs → byte-identical JSON (nodes sorted by key; edges by
      ``(etype, source, target)``).

    Default view = the top-``max_nodes`` symbols by CALLS in-degree centrality
    plus their neighbourhood; ROUTES_TO joins and their Endpoints are always
    prioritised (the cross-stack headline). *focus* (a qualified_name) seeds the
    selection with that symbol.
    """
    requested = _validate_edge_types(edge_types)
    max_nodes = max(int(max_nodes), 1)
    max_edges = max(int(max_edges), 0)
    min_rank = _conf_rank(min_confidence) or 1

    with LadybugStore(db_path) as store:
        file_lang = _file_language_map(store)
        centrality = _centrality(store)

        # 1. central seed: top symbols by in-degree, plus an optional focus + its
        #    direct CALLS neighbourhood.
        seed = _seed_symbols(store, centrality, max_nodes, focus)

        # 2. collect candidate edges per requested type.
        cand_edges: list[_Edge] = []
        endpoint_meta: dict[str, dict[str, Any]] = {}
        for etype in ALL_EDGE_TYPES:  # deterministic order
            if etype not in requested:
                continue
            if etype in _SYMBOL_SYMBOL:
                cand_edges.extend(_symbol_symbol_edges(store, etype, seed, min_rank))
            elif etype in _SYMBOL_ENDPOINT:
                cand_edges.extend(
                    _symbol_endpoint_edges(store, etype, seed, min_rank, endpoint_meta)
                )
            elif etype == "CO_CHANGES_WITH":
                cand_edges.extend(_cochange_edges(store, min_rank))

    # 3. assemble nodes from candidate edges, then enforce the caps (this is
    #    where "never render all edges" is structurally guaranteed).
    nodes = _collect_nodes(cand_edges, centrality, file_lang, endpoint_meta)
    nodes = _apply_node_filters(nodes, language, directory)
    kept_keys = _cap_nodes(nodes, max_nodes)
    edges = _cap_edges(cand_edges, kept_keys, max_edges)

    truncated = len(kept_keys) < len(nodes) or _edge_total(cand_edges, kept_keys) > len(edges)
    serial_nodes = _serialize_nodes({k: nodes[k] for k in kept_keys})
    serial_edges = _serialize_edges(edges)
    return {
        "attributes": {"name": Path(db_path).parent.name or "graph"},
        "options": {"type": "directed", "multi": True, "allowSelfLoops": True},
        "nodes": serial_nodes,
        "edges": serial_edges,
        "meta": {
            "node_count": len(serial_nodes),
            "edge_count": len(serial_edges),
            "truncated": truncated,
            "filters": {
                "edge_types": sorted(requested),
                "min_confidence": min_confidence,
                "language": language,
                "directory": directory,
                "focus": focus,
            },
            "caps": {"max_nodes": max_nodes, "max_edges": max_edges},
            "edge_type_counts": dict(sorted(Counter(e.etype for e in edges).items())),
        },
    }


# ---------------------------------------------------------------------------
# Edge collection (internal)
# ---------------------------------------------------------------------------


class _Edge:
    """A candidate edge in the unified node space (keys are type-prefixed)."""

    __slots__ = ("etype", "source", "target", "confidence", "extra")

    def __init__(
        self, etype: str, source: str, target: str, confidence: str, extra: dict[str, Any]
    ) -> None:
        self.etype = etype
        self.source = source
        self.target = target
        self.confidence = confidence
        self.extra = extra


def _sym_key(qn: str) -> str:
    return f"sym:{qn}"


def _ep_key(contract_id: str) -> str:
    return f"ep:{contract_id}"


def _file_key(path: str) -> str:
    return f"file:{path}"


_SS_QUERY = {
    "CALLS": (
        "MATCH (a:Symbol)-[r:CALLS]->(b:Symbol) WHERE a.qualified_name IN $seed "
        "AND b.qualified_name IN $seed "
        "RETURN a.qualified_name, b.qualified_name, r.confidence ORDER BY a.qualified_name, "
        "b.qualified_name"
    ),
    "EXTENDS": (
        "MATCH (a:Symbol)-[r:EXTENDS]->(b:Symbol) WHERE a.qualified_name IN $seed "
        "AND b.qualified_name IN $seed "
        "RETURN a.qualified_name, b.qualified_name, r.confidence ORDER BY a.qualified_name, "
        "b.qualified_name"
    ),
    "IMPLEMENTS": (
        "MATCH (a:Symbol)-[r:IMPLEMENTS]->(b:Symbol) WHERE a.qualified_name IN $seed "
        "AND b.qualified_name IN $seed "
        "RETURN a.qualified_name, b.qualified_name, r.confidence ORDER BY a.qualified_name, "
        "b.qualified_name"
    ),
    # ROUTES_TO is the headline: never restricted to the seed — every route is a
    # candidate (routes are few; the cap handles pathological repos).
    "ROUTES_TO": (
        "MATCH (a:Symbol)-[r:ROUTES_TO]->(b:Symbol) "
        "RETURN a.qualified_name, b.qualified_name, r.confidence ORDER BY a.qualified_name, "
        "b.qualified_name"
    ),
}


def _symbol_symbol_edges(
    store: LadybugStore, etype: str, seed: set[str], min_rank: int
) -> list[_Edge]:
    out: list[_Edge] = []
    for a, b, conf in store.query(_SS_QUERY[etype], {"seed": list(seed)}):
        if _conf_rank(conf) < min_rank:
            continue
        out.append(_Edge(etype, _sym_key(a), _sym_key(b), conf, {}))
    return out


def _symbol_endpoint_edges(
    store: LadybugStore,
    etype: str,
    seed: set[str],
    min_rank: int,
    endpoint_meta: dict[str, dict[str, Any]],
) -> list[_Edge]:
    # The Endpoint is the join node; include the edge when its consumer/handler
    # symbol is in the seed (HANDLES/CALLS_ENDPOINT are few relative to CALLS).
    rel = "HANDLES" if etype == "HANDLES" else "CALLS_ENDPOINT"
    rows = store.query(
        f"MATCH (s:Symbol)-[r:{rel}]->(e:Endpoint) WHERE s.qualified_name IN $seed "
        "RETURN s.qualified_name, e.contract_id, e.method, e.normalized_path, "
        "e.spec_backed, r.confidence ORDER BY s.qualified_name, e.contract_id",
        {"seed": list(seed)},
    )
    out: list[_Edge] = []
    for sqn, cid, method, npath, spec_backed, conf in rows:
        if _conf_rank(conf) < min_rank:
            continue
        endpoint_meta[_ep_key(cid)] = {
            "contract_id": cid,
            "method": method,
            "normalized_path": npath,
            "spec_backed": bool(spec_backed),
        }
        out.append(_Edge(etype, _sym_key(sqn), _ep_key(cid), conf, {}))
    return out


def _cochange_edges(store: LadybugStore, min_rank: int) -> list[_Edge]:
    # The 348k monster — opt-in, hard-capped by frequency. Undirected in the
    # store; we canonicalise (a < b) so each pair appears once, deterministically.
    rows = store.query(
        "MATCH (a:File)-[r:CO_CHANGES_WITH]->(b:File) "
        "RETURN a.path, b.path, r.frequency, r.confidence "
        f"ORDER BY r.frequency DESC, a.path, b.path LIMIT {_COCHANGE_CAP * 2}"
    )
    seen: set[tuple[str, str]] = set()
    out: list[_Edge] = []
    for a, b, freq, conf in rows:
        if _conf_rank(conf) < min_rank:
            continue
        lo, hi = (a, b) if a <= b else (b, a)
        if (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        out.append(
            _Edge("CO_CHANGES_WITH", _file_key(lo), _file_key(hi), conf, {"frequency": float(freq)})
        )
        if len(out) >= _COCHANGE_CAP:
            break
    return out


# ---------------------------------------------------------------------------
# Node assembly + caps (internal)
# ---------------------------------------------------------------------------


def _collect_nodes(
    edges: list[_Edge],
    centrality: dict[str, int],
    file_lang: dict[str, str],
    endpoint_meta: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    routes_participants: set[str] = set()
    for e in edges:
        if e.etype == "ROUTES_TO":
            routes_participants.add(e.source)
            routes_participants.add(e.target)
    for e in edges:
        for key in (e.source, e.target):
            if key in nodes:
                continue
            nodes[key] = _make_node(key, centrality, file_lang, endpoint_meta, routes_participants)
    # priority is recomputed once all nodes exist so endpoints of a kept route
    # are also flagged headline.
    for key in nodes:
        if key in routes_participants:
            nodes[key]["headline"] = True
    return nodes


def _make_node(
    key: str,
    centrality: dict[str, int],
    file_lang: dict[str, str],
    endpoint_meta: dict[str, dict[str, Any]],
    routes_participants: set[str],
) -> dict[str, Any]:
    if key.startswith("sym:"):
        qn = key[4:]
        fpath = qn.split("::", 1)[0]
        cent = centrality.get(qn, 0)
        return {
            "key": key,
            "ntype": "symbol",
            "label": _leaf(qn),
            "qualified_name": qn,
            "language": file_lang.get(fpath, ""),
            "directory": _directory(fpath),
            "centrality": cent,
            "headline": key in routes_participants,
        }
    if key.startswith("ep:"):
        meta = endpoint_meta.get(key, {})
        cid = key[3:]
        label = f"{meta.get('method', '')} {meta.get('normalized_path', '')}".strip() or cid
        return {
            "key": key,
            "ntype": "endpoint",
            "label": label,
            "contract_id": cid,
            "spec_backed": meta.get("spec_backed", False),
            "language": "",
            "directory": "",
            "centrality": 0,
            "headline": True,  # the cross-stack join node is always headline
        }
    # file:
    fpath = key[5:]
    return {
        "key": key,
        "ntype": "file",
        "label": fpath.split("/")[-1],
        "path": fpath,
        "language": file_lang.get(fpath, ""),
        "directory": _directory(fpath),
        "centrality": 0,
        "headline": False,
    }


def _apply_node_filters(
    nodes: dict[str, dict[str, Any]], language: str | None, directory: str | None
) -> dict[str, dict[str, Any]]:
    if not language and not directory:
        return nodes
    out: dict[str, dict[str, Any]] = {}
    for key, n in nodes.items():
        # Endpoint nodes are cross-cutting (no language/dir) — exempt so the
        # cross-stack join is never filtered away.
        if n["ntype"] == "endpoint":
            out[key] = n
            continue
        if language and n.get("language") != language:
            continue
        if directory and not _dir_match(n.get("directory", ""), directory):
            continue
        out[key] = n
    return out


def _cap_nodes(nodes: dict[str, dict[str, Any]], max_nodes: int) -> list[str]:
    """Keep the top-*max_nodes* nodes. Headline (ROUTES_TO/Endpoint) first, then
    by centrality desc, then key — deterministic."""
    ranked = sorted(
        nodes.values(),
        key=lambda n: (0 if n["headline"] else 1, -n["centrality"], n["key"]),
    )
    return sorted(n["key"] for n in ranked[:max_nodes])


# edge-cap priority: the cross-stack/structural story first, the CALLS backbone
# next, the co-change cloud last.
_EDGE_PRIORITY = {
    "ROUTES_TO": 0,
    "HANDLES": 1,
    "CALLS_ENDPOINT": 1,
    "EXTENDS": 2,
    "IMPLEMENTS": 2,
    "CALLS": 3,
    "CO_CHANGES_WITH": 4,
}


def _cap_edges(edges: list[_Edge], kept_keys: list[str], max_edges: int) -> list[_Edge]:
    keptset = set(kept_keys)
    eligible = [e for e in edges if e.source in keptset and e.target in keptset]
    eligible.sort(key=lambda e: (_EDGE_PRIORITY.get(e.etype, 9), e.etype, e.source, e.target))
    # de-dup identical (etype, source, target) — multigraph keeps them distinct
    # only when confidence differs, which the store does not produce.
    seen: set[tuple[str, str, str]] = set()
    deduped: list[_Edge] = []
    for e in eligible:
        sig = (e.etype, e.source, e.target)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(e)
    return deduped[:max_edges]


def _edge_total(edges: list[_Edge], kept_keys: list[str]) -> int:
    keptset = set(kept_keys)
    seen: set[tuple[str, str, str]] = set()
    for e in edges:
        if e.source in keptset and e.target in keptset:
            seen.add((e.etype, e.source, e.target))
    return len(seen)


# ---------------------------------------------------------------------------
# Serialization (internal) — deterministic graphology import format
# ---------------------------------------------------------------------------


def _serialize_nodes(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    import math

    keys = sorted(nodes)
    n = max(len(keys), 1)
    out: list[dict[str, Any]] = []
    for i, key in enumerate(keys):
        node = nodes[key]
        # deterministic circular initial layout; the client runs ForceAtlas2.
        angle = 2.0 * math.pi * i / n
        attrs: dict[str, Any] = {
            "label": node["label"],
            "ntype": node["ntype"],
            "language": node.get("language", ""),
            "directory": node.get("directory", ""),
            "size": _node_size(node),
            "color": _NTYPE_COLOR.get(node["ntype"], "#868e96"),
            "x": round(math.cos(angle), 6),
            "y": round(math.sin(angle), 6),
        }
        if node["ntype"] == "endpoint":
            attrs["spec_backed"] = node.get("spec_backed", False)
            attrs["contract_id"] = node.get("contract_id", "")
        if node["ntype"] == "symbol":
            attrs["qualified_name"] = node.get("qualified_name", "")
        out.append({"key": key, "attributes": attrs})
    return out


def _serialize_edges(edges: list[_Edge]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in sorted(edges, key=lambda e: (e.etype, e.source, e.target)):
        routes = e.etype == "ROUTES_TO"
        attrs: dict[str, Any] = {
            "etype": e.etype,
            "confidence": e.confidence,
            "color": _ROUTES_TO_COLOR if routes else _CONF_COLOR.get(e.confidence, "#adb5bd"),
            "size": 3.0 if routes else 1.0,
            "dashed": False if routes else _CONF_DASHED.get(e.confidence, True),
            "type": "arrow",
        }
        if "frequency" in e.extra:
            attrs["frequency"] = e.extra["frequency"]
        out.append(
            {
                "key": f"{e.etype}|{e.source}|{e.target}",
                "source": e.source,
                "target": e.target,
                "attributes": attrs,
            }
        )
    return out


def _node_size(node: dict[str, Any]) -> float:
    if node["ntype"] == "endpoint":
        return 6.0
    # centrality → a gentle size ramp (sqrt to compress the long tail).
    import math

    return round(3.0 + math.sqrt(max(node.get("centrality", 0), 0)) * 1.5, 3)


# ---------------------------------------------------------------------------
# Store helpers (internal)
# ---------------------------------------------------------------------------


def _centrality(store: LadybugStore) -> dict[str, int]:
    """CALLS in-degree per Symbol qualified_name — the node-importance signal."""
    return {
        qn: int(n)
        for qn, n in store.query(
            "MATCH (a:Symbol)-[:CALLS]->(b:Symbol) RETURN b.qualified_name, count(a) AS n"
        )
    }


def _seed_symbols(
    store: LadybugStore, centrality: dict[str, int], max_nodes: int, focus: str | None
) -> set[str]:
    # top symbols by centrality, then qn (deterministic)
    ranked = sorted(centrality.items(), key=lambda kv: (-kv[1], kv[0]))
    seed = {qn for qn, _ in ranked[:max_nodes]}
    # symbols with no incoming CALLS never appear in `centrality`; pull a
    # deterministic alphabetical fill so isolated/leaf nodes are still reachable.
    if len(seed) < max_nodes:
        fill = [
            r[0]
            for r in store.query(
                "MATCH (s:Symbol) RETURN s.qualified_name ORDER BY s.qualified_name "
                f"LIMIT {max_nodes * 2}"
            )
        ]
        for qn in fill:
            if len(seed) >= max_nodes:
                break
            seed.add(qn)
    if focus:
        seed.add(focus)
        for r in store.query(
            "MATCH (s:Symbol {qualified_name: $q})-[:CALLS]-(o:Symbol) "
            "RETURN o.qualified_name ORDER BY o.qualified_name LIMIT 50",
            {"q": focus},
        ):
            seed.add(r[0])
    return seed


def _file_language_map(store: LadybugStore) -> dict[str, str]:
    return {path: lang for path, lang in store.query("MATCH (f:File) RETURN f.path, f.language")}


# ---------------------------------------------------------------------------
# Public: node detail + meta
# ---------------------------------------------------------------------------


def build_node_detail(db_path: Path | str, key: str) -> dict[str, Any]:
    """The click-a-node side panel: reuse the MCP `context` + `trace` tools.

    *key* is a serialized node key (``sym:<qn>`` / ``ep:<cid>`` / ``file:<path>``)
    or a bare qualified_name. Endpoint/File keys return a lighter payload."""
    from forensic_deepdive.mcp_server import server as mcp

    path = Path(db_path)
    if key.startswith("ep:"):
        return _endpoint_detail(path, key[3:])
    if key.startswith("file:"):
        return mcp.archaeology(path, key[5:])
    qn = key[4:] if key.startswith("sym:") else key
    detail: dict[str, Any] = {"context": mcp.context(path, qn)}
    # attach the cross-stack trace only when it actually yields a chain — `trace`
    # returns empty chains for an ordinary (non-route) symbol, so this stays cheap
    # and the panel only shows a cross-stack section when there is one.
    down = mcp.trace(path, qn, direction="downstream")
    if down.get("chains"):
        detail["trace_downstream"] = down
    up = mcp.trace(path, qn, direction="upstream")
    if up.get("chains"):
        detail["trace_upstream"] = up
    return detail


def _endpoint_detail(db_path: Path, contract_id: str) -> dict[str, Any]:
    with LadybugStore(db_path) as store:
        ep = list(
            store.query(
                "MATCH (e:Endpoint {contract_id: $c}) RETURN e.contract_id, e.protocol, "
                "e.method, e.normalized_path, e.framework, e.spec_backed",
                {"c": contract_id},
            )
        )
        handlers = [
            {"qualified_name": q, "confidence": c}
            for q, c in store.query(
                "MATCH (h:Symbol)-[r:HANDLES]->(:Endpoint {contract_id: $c}) "
                "RETURN h.qualified_name, r.confidence ORDER BY h.qualified_name",
                {"c": contract_id},
            )
        ]
        consumers = [
            {"qualified_name": q, "confidence": c}
            for q, c in store.query(
                "MATCH (s:Symbol)-[r:CALLS_ENDPOINT]->(:Endpoint {contract_id: $c}) "
                "RETURN s.qualified_name, r.confidence ORDER BY s.qualified_name",
                {"c": contract_id},
            )
        ]
    if not ep:
        return {"endpoint": None, "unresolved": True, "contract_id": contract_id}
    cid, proto, method, npath, framework, spec_backed = ep[0]
    return {
        "endpoint": {
            "contract_id": cid,
            "protocol": proto,
            "method": method,
            "normalized_path": npath,
            "framework": framework,
            "spec_backed": bool(spec_backed),
        },
        "handlers": handlers,
        "consumers": consumers,
        "unlocated": not handlers,
    }


def build_meta(db_path: Path | str) -> dict[str, Any]:
    """Filter-UI metadata: languages, top-level directories, per-edge-type counts."""
    with LadybugStore(db_path) as store:
        languages = sorted(
            {
                lang
                for (lang,) in store.query(
                    "MATCH (f:File) WHERE f.role = 'source' OR f.role = 'example' "
                    "RETURN DISTINCT f.language"
                )
                if lang
            }
        )
        directories = sorted(
            {
                _directory(path)
                for (path,) in store.query("MATCH (f:File) RETURN f.path")
                if _directory(path)
            }
        )
        edge_type_counts: dict[str, int] = {}
        for etype in ALL_EDGE_TYPES:
            rows = list(store.query(f"MATCH ()-[r:{etype}]->() RETURN count(r)"))
            edge_type_counts[etype] = int(rows[0][0]) if rows else 0
        sym_rows = list(store.query("MATCH (s:Symbol) RETURN count(s)"))
        ep_rows = list(store.query("MATCH (e:Endpoint) RETURN count(e)"))
    return {
        "name": Path(db_path).parent.name or "graph",
        "languages": languages,
        "directories": directories,
        "edge_types": list(ALL_EDGE_TYPES),
        "default_edge_types": list(DEFAULT_EDGE_TYPES),
        "edge_type_counts": edge_type_counts,
        "symbol_count": int(sym_rows[0][0]) if sym_rows else 0,
        "endpoint_count": int(ep_rows[0][0]) if ep_rows else 0,
        "confidence_levels": ["EXTRACTED", "INFERRED", "AMBIGUOUS"],
    }


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------


def _validate_edge_types(edge_types: Sequence[str] | None) -> frozenset[str]:
    if edge_types is None:
        return frozenset(DEFAULT_EDGE_TYPES)
    chosen = {e.strip().upper() for e in edge_types if e and e.strip()}
    valid = chosen & set(ALL_EDGE_TYPES)
    return frozenset(valid) if valid else frozenset(DEFAULT_EDGE_TYPES)


def _leaf(qn: str) -> str:
    return qn.split("::")[-1].split(".")[-1] or qn


def _directory(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _dir_match(node_dir: str, wanted: str) -> bool:
    wanted = wanted.rstrip("/")
    return node_dir == wanted or node_dir.startswith(wanted + "/")
