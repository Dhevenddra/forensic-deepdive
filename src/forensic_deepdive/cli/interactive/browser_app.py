"""The Textual ``App`` behind ``forensic browse`` (DEC-100).

Imports textual at module top — only ever imported after ``run_browse`` (or a
test) has probed the ``[interactive]`` extra. Read-only in v0.9: browsing,
filtering, and jumping to the existing ``context``/``impact``/``flow`` tool
output; no graph mutation.

Desktop-serve-ready discipline (KICKOFF §11): all state lives on the App
instance (no module globals), no direct stdin/stdout access, no terminal-only
escape hatches — nothing here precludes ``textual serve``.

Glyph discipline (DEC-078/080): confidence is encoded as ASCII letter chips
(``E/I/A``) — never colour-alone, never a non-ASCII glyph.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static

from forensic_deepdive.cli.interactive.browser import (
    CONFIDENCE_LEVELS,
    EDGE_TYPE_FILTERS,
    GraphSnapshot,
    NodeRow,
)

if TYPE_CHECKING:
    from pathlib import Path

_KINDS = ("symbol", "file", "endpoint")
_KIND_LABELS = {"symbol": "Symbols", "file": "Files", "endpoint": "Endpoints"}


def _chips(confidences: frozenset[str]) -> str:
    """ASCII confidence chips in taxonomy order — e.g. ``E,I`` (never colour-alone)."""
    return ",".join(level[0] for level in CONFIDENCE_LEVELS if level in confidences)


class GraphBrowser(App[None]):
    """Full-screen, read-only graph browser (DEC-100)."""

    TITLE = "deepdive browse"
    CSS = """
    #sidebar { width: 55%; }
    #detailwrap { width: 45%; border-left: solid $accent; padding: 0 1; }
    #status { height: 2; color: $text-muted; }
    #needle { margin: 0 0 1 0; }
    """
    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("1", "set_kind('symbol')", "Symbols"),
        Binding("2", "set_kind('file')", "Files"),
        Binding("3", "set_kind('endpoint')", "Endpoints"),
        Binding("c", "cycle_confidence", "Conf filter"),
        Binding("e", "cycle_edge_type", "Edge filter"),
        Binding("l", "cycle_language", "Lang filter"),
        Binding("i", "impact", "Impact"),
        Binding("f", "flow", "Flow"),
    ]

    def __init__(self, snapshot: GraphSnapshot) -> None:
        super().__init__()
        self.snapshot = snapshot
        self.active_kind: str = "symbol"
        self.conf_filter: str | None = None
        self.edge_filter: str | None = None
        self.lang_filter: str | None = None
        self.needle: str = ""
        self.visible_nodes: list[NodeRow] = []

    # --- layout -----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(placeholder="type to filter by name/path …", id="needle")
                yield DataTable(id="nodes", cursor_type="row", zebra_stripes=True)
                yield Static("", id="status")
            yield VerticalScroll(
                Static("select a node (Enter) for its context.", id="detail"),
                id="detailwrap",
            )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("name", "kind", "where", "conf")
        self.refresh_rows()
        table.focus()

    # --- filtering --------------------------------------------------------

    def _pool(self) -> tuple[NodeRow, ...]:
        return {
            "symbol": self.snapshot.symbols,
            "file": self.snapshot.files,
            "endpoint": self.snapshot.endpoints,
        }[self.active_kind]

    def _passes(self, node: NodeRow) -> bool:
        if self.needle and self.needle.lower() not in f"{node.name} {node.location}".lower():
            return False
        if self.lang_filter and node.language and node.language != self.lang_filter:
            return False
        if self.lang_filter and not node.language and self.active_kind != "endpoint":
            return False
        if self.conf_filter and node.confidences and self.conf_filter not in node.confidences:
            return False
        if self.conf_filter and not node.confidences and self.active_kind == "symbol":
            return False
        if self.edge_filter and self.active_kind == "symbol":
            return self.edge_filter in node.edge_types
        return True

    def refresh_rows(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self.visible_nodes = [node for node in self._pool() if self._passes(node)]
        for node in self.visible_nodes:
            table.add_row(
                node.name, node.kind, node.location, _chips(node.confidences), key=node.key
            )
        self._update_status()

    def _update_status(self) -> None:
        total = self.snapshot.totals.get(self.active_kind, 0)
        label = _KIND_LABELS[self.active_kind]
        line = f"{label}: showing {len(self.visible_nodes)} of {total} in graph"
        if self.snapshot.truncated(self.active_kind):
            line += f" (loaded top {len(self._pool())}; raise --max-nodes to widen)"
        active = [
            f"conf={self.conf_filter}" if self.conf_filter else "",
            f"edge={self.edge_filter}" if self.edge_filter else "",
            f"lang={self.lang_filter}" if self.lang_filter else "",
        ]
        filters = "  ".join(part for part in active if part)
        self.query_one("#status", Static).update(
            line + ("\nfilters: " + filters if filters else "")
        )

    # --- events / actions ---------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        self.needle = event.value.strip()
        self.refresh_rows()

    def action_set_kind(self, kind: str) -> None:
        if kind in _KINDS:
            self.active_kind = kind
            self.refresh_rows()

    def _cycle(self, current: str | None, options: tuple[str, ...]) -> str | None:
        if current is None:
            return options[0] if options else None
        idx = options.index(current) + 1 if current in options else 0
        return None if idx >= len(options) else options[idx]

    def action_cycle_confidence(self) -> None:
        self.conf_filter = self._cycle(self.conf_filter, CONFIDENCE_LEVELS)
        self.refresh_rows()

    def action_cycle_edge_type(self) -> None:
        self.edge_filter = self._cycle(self.edge_filter, EDGE_TYPE_FILTERS)
        self.refresh_rows()

    def action_cycle_language(self) -> None:
        self.lang_filter = self._cycle(self.lang_filter, self.snapshot.languages)
        self.refresh_rows()

    def _selected(self) -> NodeRow | None:
        table = self.query_one(DataTable)
        if not self.visible_nodes or table.cursor_row is None:
            return None
        if 0 <= table.cursor_row < len(self.visible_nodes):
            return self.visible_nodes[table.cursor_row]
        return None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        node = self._selected()
        if node is not None:
            self.show_detail(self._node_detail(node))

    def action_impact(self) -> None:
        node = self._selected()
        if node is None or not node.key.startswith("sym:"):
            self.show_detail({"note": "impact targets a Symbol row — select one first."})
            return
        from forensic_deepdive.mcp_server import server as mcp  # noqa: PLC0415

        self.show_detail(mcp.impact(self._db(), node.key[4:]))

    def action_flow(self) -> None:
        node = self._selected()
        if node is None or not node.key.startswith("sym:"):
            self.show_detail({"note": "flow targets a Symbol row — select one first."})
            return
        from forensic_deepdive.mcp_server import server as mcp  # noqa: PLC0415

        self.show_detail(mcp.flow(self._db(), node.key[4:]))

    # --- detail pane --------------------------------------------------------

    def _db(self) -> Path:
        return self.snapshot.db_path

    def _node_detail(self, node: NodeRow) -> dict[str, Any]:
        """The click-a-node payload — reuses the serve-UI detail builder, which
        itself reuses the MCP tools (context/trace/archaeology). Opens the store
        per call; the browser never holds a live handle while running."""
        from forensic_deepdive.serve.graph_api import build_node_detail  # noqa: PLC0415

        try:
            return build_node_detail(self._db(), node.key)
        except Exception as exc:  # degrade honestly, never crash the App
            return {"error": str(exc), "node": node.key}

    def show_detail(self, payload: dict[str, Any]) -> None:
        text = json.dumps(payload, indent=2, ensure_ascii=True, default=str)
        self.query_one("#detail", Static).update(text)
