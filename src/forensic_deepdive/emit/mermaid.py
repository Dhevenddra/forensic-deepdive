"""Mermaid visual export (DEC-039, v0.3 Item F).

Renders a **bounded** subgraph of the LadybugDB code graph as a fenced
```mermaid block — inline-renderable in Claude Code, GitHub PRs, and Notion.
The confidence taxonomy (DEC-015) is made *visible*: in ``flowchart`` mode each
edge's dash style encodes its confidence (solid=EXTRACTED, dashed=INFERRED,
dotted=AMBIGUOUS). ``classDiagram`` mode lacks per-edge styling in Mermaid, so
there confidence rides in the relationship label (documented divergence).

Determinism: node ids ``n0,n1,…`` are assigned in sorted-``qualified_name``
order; edges are sorted; ``linkStyle`` lines follow edge declaration order.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from forensic_deepdive.graph import LadybugStore

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_DEPTH = 2
DEFAULT_MAX_NODES = 40

FLOWCHART = "flowchart"
CLASS_DIAGRAM = "classDiagram"

# Kinds that auto-pick the class diagram (structure view) over the call flow.
_TYPE_KINDS = frozenset({"class", "interface", "struct", "enum", "trait"})

# Confidence -> Mermaid flowchart dash pattern. EXTRACTED is omitted == solid.
_DASH = {"INFERRED": "6 4", "AMBIGUOUS": "2 3"}

_ID_SAFE = re.compile(r"[^0-9A-Za-z_]")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_mermaid(
    db_path: Path,
    target: str | None = None,
    *,
    diagram: str | None = None,
    depth: int = DEFAULT_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    direction: str = "both",
    central: bool = False,
) -> dict[str, Any]:
    """Render a bounded Mermaid subgraph around *target*.

    Returns ``{mermaid, target, diagram, node_count, truncated}`` where
    ``mermaid`` is the fenced block, or ``{unresolved: True, target}`` when the
    target can't be found. ``central=True`` ignores *target* and shows the
    top-``max_nodes`` symbols by CALLS in-degree.
    """
    if direction not in ("in", "out", "both"):
        return {"error": f"direction must be in|out|both, got {direction!r}"}
    if diagram is not None and diagram not in (FLOWCHART, CLASS_DIAGRAM):
        return {"error": f"diagram must be {FLOWCHART}|{CLASS_DIAGRAM}, got {diagram!r}"}

    with LadybugStore(db_path) as store:
        if central:
            body, count, trunc = _render_central(store, max_nodes)
            return _payload(body, "<central>", FLOWCHART, count, trunc)

        if not target:
            return {"error": "pass a target symbol/file or central=True"}
        resolved = _resolve_target(store, target)
        if resolved is None:
            return {"unresolved": True, "target": target}
        kind, key, sym_kind = resolved

        if kind == "file":
            body, count, trunc = _render_file_flow(store, key, max_nodes)
            return _payload(body, key, FLOWCHART, count, trunc)

        mode = diagram or (CLASS_DIAGRAM if (sym_kind in _TYPE_KINDS) else FLOWCHART)
        if mode == CLASS_DIAGRAM:
            body, count, trunc = _render_class(store, key, max_nodes)
        else:
            body, count, trunc = _render_flowchart(store, key, depth, direction, max_nodes)
        return _payload(body, key, mode, count, trunc)


def _payload(body: str, target: str, diagram: str, count: int, trunc: bool) -> dict[str, Any]:
    return {
        "mermaid": f"```mermaid\n{body}\n```",
        "target": target,
        "diagram": diagram,
        "node_count": count,
        "truncated": trunc,
    }


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def _resolve_target(store: LadybugStore, target: str) -> tuple[str, str, str] | None:
    for clause, param in (
        ("s.qualified_name = $q", target),
        ("s.qualified_name ENDS WITH $q", f"::{target}"),
        ("s.qualified_name ENDS WITH $q", f".{target}"),
    ):
        rows = list(
            store.query(
                f"MATCH (s:Symbol) WHERE {clause} "
                "RETURN s.qualified_name, s.kind ORDER BY s.qualified_name LIMIT 1",
                {"q": param},
            )
        )
        if rows:
            return ("symbol", rows[0][0], rows[0][1])
    rows = list(store.query("MATCH (f:File {path: $p}) RETURN f.path LIMIT 1", {"p": target}))
    if rows:
        return ("file", rows[0][0], "")
    return None


# ---------------------------------------------------------------------------
# Subgraph collection
# ---------------------------------------------------------------------------


def _calls_edges(store: LadybugStore, qn: str, direction: str) -> list[tuple[str, str, str]]:
    """CALLS edges incident on *qn* in *direction*, as (caller, callee, conf)."""
    out: list[tuple[str, str, str]] = []
    if direction in ("out", "both"):
        out.extend(
            (qn, b, conf)
            for b, conf in store.query(
                "MATCH (:Symbol {qualified_name: $q})-[r:CALLS]->(c:Symbol) "
                "RETURN c.qualified_name, r.confidence",
                {"q": qn},
            )
        )
    if direction in ("in", "both"):
        out.extend(
            (a, qn, conf)
            for a, conf in store.query(
                "MATCH (c:Symbol)-[r:CALLS]->(:Symbol {qualified_name: $q}) "
                "RETURN c.qualified_name, r.confidence",
                {"q": qn},
            )
        )
    return out


def _bfs(
    store: LadybugStore, root: str, depth: int, direction: str, max_nodes: int
) -> tuple[list[str], list[tuple[str, str, str]], bool, int]:
    """BFS over CALLS to *depth*. Returns (kept_nodes, edges, truncated, total).

    Discovery order is root, then each level sorted alphabetically — so the
    truncation that keeps the first ``max_nodes`` nodes is deterministic.
    """
    discovered = [root]
    seen = {root}
    edges: list[tuple[str, str, str]] = []
    frontier = [root]
    for _ in range(max(depth, 0)):
        nxt: set[str] = set()
        for qn in frontier:
            for a, b, conf in _calls_edges(store, qn, direction):
                edges.append((a, b, conf))
                other = b if a == qn else a
                if other not in seen:
                    seen.add(other)
                    nxt.add(other)
        if not nxt:
            break
        for n in sorted(nxt):
            discovered.append(n)
        frontier = sorted(nxt)

    truncated = len(discovered) > max_nodes
    kept = discovered[: max_nodes - 1] if truncated else discovered
    keptset = set(kept)
    kept_edges = sorted({(a, b, c) for (a, b, c) in edges if a in keptset and b in keptset})
    return kept, kept_edges, truncated, len(discovered)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _label(qn: str) -> str:
    """Short, Mermaid-safe node label: the leaf identifier. DEC-104: a
    module-scope symbol labels as its file stem (via the dotted-path display),
    never the literal ``<module>`` (whose angle brackets also fight Mermaid's
    HTML-ish label parsing)."""
    from forensic_deepdive.static.resolver import module_display_name

    display = module_display_name(qn) or qn
    leaf = display.split("::")[-1].split(".")[-1]
    return leaf.replace('"', "'")


def _flowchart_lines(
    kept: list[str], edges: list[tuple[str, str, str]], *, truncated: bool, dropped: int, etype: str
) -> str:
    ids = {qn: f"n{i}" for i, qn in enumerate(sorted(kept))}
    lines = ["flowchart LR"]
    for qn in sorted(kept):
        lines.append(f'    {ids[qn]}["{_label(qn)}"]')
    if truncated:
        lines.append(f'    nMore["… (+{dropped} more)"]')

    dash_lines: list[str] = []
    for link_index, (a, b, conf) in enumerate(edges):
        lines.append(f"    {ids[a]} -->|{etype}| {ids[b]}")
        if conf in _DASH:
            dash_lines.append(f"    linkStyle {link_index} stroke-dasharray: {_DASH[conf]}")
    if truncated and kept:
        # Anchor the summary node so it isn't an orphan; left unstyled (solid).
        root_id = ids[sorted(kept)[0]]
        lines.append(f"    {root_id} -.-> nMore")
    lines.extend(dash_lines)
    return "\n".join(lines)


def _render_flowchart(
    store: LadybugStore, root: str, depth: int, direction: str, max_nodes: int
) -> tuple[str, int, bool]:
    kept, edges, truncated, total = _bfs(store, root, depth, direction, max_nodes)
    body = _flowchart_lines(
        kept, edges, truncated=truncated, dropped=total - len(kept), etype="CALLS"
    )
    return body, len(kept) + (1 if truncated else 0), truncated


def _render_central(store: LadybugStore, max_nodes: int) -> tuple[str, int, bool]:
    cap = max(int(max_nodes), 1)
    rows = list(
        store.query(
            "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) "
            "RETURN s.qualified_name, count(c) AS n "
            f"ORDER BY n DESC, s.qualified_name LIMIT {cap}"
        )
    )
    kept = [r[0] for r in rows]
    keptset = set(kept)
    edges: list[tuple[str, str, str]] = []
    for qn in kept:
        edges.extend((a, b, c) for (a, b, c) in _calls_edges(store, qn, "out") if b in keptset)
    edges = sorted(set(edges))
    body = _flowchart_lines(kept, edges, truncated=False, dropped=0, etype="CALLS")
    return body, len(kept), False


def _render_file_flow(store: LadybugStore, path: str, max_nodes: int) -> tuple[str, int, bool]:
    """A file's IMPORTS neighborhood: File -> Module edges (all EXTRACTED)."""
    rows = list(
        store.query(
            "MATCH (:File {path: $p})-[r:IMPORTS]->(m:Module) "
            "RETURN m.path, r.confidence ORDER BY m.path",
            {"p": path},
        )
    )
    truncated = len(rows) > max_nodes - 1
    kept_rows = rows[: max_nodes - 2] if truncated else rows
    ids = {path: "n0"}
    lines = ["flowchart LR", f'    n0["{path.split("/")[-1]}"]']
    edge_lines: list[str] = []
    dash_lines: list[str] = []
    for i, (mod, conf) in enumerate(kept_rows, start=1):
        ids[mod] = f"n{i}"
        lines.append(f'    n{i}["{mod.split(":")[-1]}"]')
        edge_lines.append(f"    n0 -->|IMPORTS| n{i}")
        if conf in _DASH:
            dash_lines.append(f"    linkStyle {i - 1} stroke-dasharray: {_DASH[conf]}")
    if truncated:
        lines.append(f'    nMore["… (+{len(rows) - len(kept_rows)} more)"]')
        edge_lines.append("    n0 -.-> nMore")
    lines.extend(edge_lines)
    lines.extend(dash_lines)
    return "\n".join(lines), len(kept_rows) + 1 + (1 if truncated else 0), truncated


def _class_id(name: str) -> str:
    return _ID_SAFE.sub("_", name) or "_"


def _render_class(store: LadybugStore, qn: str, max_nodes: int) -> tuple[str, int, bool]:
    target = _label(qn)
    tid = _class_id(target)

    members = [
        _label(r[0])
        for r in store.query(
            "MATCH (m:Symbol)-[:MEMBER_OF]->(:Symbol {qualified_name: $q}) "
            "RETURN m.qualified_name ORDER BY m.qualified_name",
            {"q": qn},
        )
    ]
    truncated = len(members) > max_nodes
    shown = members[: max_nodes - 1] if truncated else members

    lines = [CLASS_DIAGRAM, f"    class {tid} {{"]
    for m in shown:
        lines.append(f"        +{m}()")
    if truncated:
        lines.append(f"        +… (+{len(members) - len(shown)} more)")
    lines.append("    }")

    rels: list[str] = []
    for parent, conf in store.query(
        "MATCH (:Symbol {qualified_name: $q})-[r:EXTENDS]->(p:Symbol) "
        "RETURN p.qualified_name, r.confidence ORDER BY p.qualified_name",
        {"q": qn},
    ):
        rels.append(f"    {_class_id(_label(parent))} <|-- {tid} : {_rel_label('EXTENDS', conf)}")
    for iface, conf in store.query(
        "MATCH (:Symbol {qualified_name: $q})-[r:IMPLEMENTS]->(i:Symbol) "
        "RETURN i.qualified_name, r.confidence ORDER BY i.qualified_name",
        {"q": qn},
    ):
        rels.append(f"    {_class_id(_label(iface))} <|.. {tid} : {_rel_label('IMPLEMENTS', conf)}")
    lines.extend(sorted(rels))
    return "\n".join(lines), 1 + len(shown), truncated


def _rel_label(etype: str, conf: str) -> str:
    """classDiagram confidence rides in the label (no per-edge style in Mermaid)."""
    return etype if conf == "EXTRACTED" else f"{etype} · {conf}"
