"""The static ASCII wordmark + the data-driven capability panel (DEC-078, v0.7 Track B).

The banner is a **static embedded ASCII string** (no ``pyfiglet`` — DEC-071 §8.12). The
capability panel is **data-driven from the registries** (the protocol REGISTRY, the artifact
filename contract, and the live MCP tool list) so it can **never drift** from the frozen
contract — never a hardcoded list. Everything renders to the Console only; on a non-TTY /
``--plain`` the block wordmark degrades to a plain text title.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.box import SQUARE
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from forensic_deepdive import __version__

if TYPE_CHECKING:
    from rich.console import Console

# Static block wordmark (DEC-078) — "DEEPDIVE", 5 rows, hand-set so line widths align.
_WORDMARK = r"""
████  █████ █████ █████ ████  █████ █   █ █████
█   █ █     █     █   █ █   █   █   █   █ █
█   █ ████  ████  █████ █   █   █   █   █ ████
█   █ █     █     █     █   █   █    █ █  █
████  █████ █████ █     ████  █████   █   █████
""".strip("\n")

_TAGLINE = "forensic understanding of any codebase"


def _can_render_blocks(console: Console) -> bool:
    """Block glyphs only on an interactive, colour-capable, UTF-8 console; otherwise the
    plain title (keeps pipes / cp1252 terminals clean — the degrade contract)."""
    enc = (console.encoding or "").lower()
    return console.is_terminal and not console.no_color and ("utf" in enc)


def render_banner(console: Console) -> None:
    """Print the wordmark + right-aligned version + tagline (or a plain title when the
    console can't/shouldn't render block art)."""
    version = f"v{__version__}"
    if _can_render_blocks(console):
        # Per-row blue gradient (light → deep) for a Hermes-style 3-D depth in our palette.
        rows = _WORDMARK.split("\n")
        for i, row in enumerate(rows, start=1):
            console.print(Text(row, style=f"banner.{min(i, 5)}"))
        line = Text(_TAGLINE, style="tagline")
        line.append(Text(f"{version}".rjust(max(1, 48 - len(_TAGLINE))), style="version"))
        console.print(line)
    else:
        console.print(f"DEEPDIVE {version}")
        console.print(_TAGLINE)


# --- the data-driven capability panel ---------------------------------------


def _artifact_names() -> list[str]:
    """The five durable artifacts (the contract), read from the canonical filename tuple —
    not hardcoded here. The conditional AGENT_BRIEF_DEEP overflow is excluded."""
    from forensic_deepdive.query.artifacts import ARTIFACT_FILENAMES

    return [n for n in ARTIFACT_FILENAMES if "DEEP" not in n]


def _protocol_names() -> list[str]:
    """The live cross-boundary protocol registry keys (DEC-043/055)."""
    from forensic_deepdive.contracts.registry import REGISTRY

    return sorted(REGISTRY)


def _mcp_tool_names() -> list[str]:
    """The live MCP tool names, introspected from a (cheap, DB-less) server build so the
    panel can never drift from the frozen 9-tool contract. The ``_tool`` suffix is dropped."""
    from pathlib import Path

    from forensic_deepdive.mcp_server.server import make_server

    server = make_server(Path("_capability_probe.lbug"))
    names = [t.name for t in server._tool_manager.list_tools()]
    return sorted(n[:-5] if n.endswith("_tool") else n for n in names)


def _confidence_legend(*, glyphs: bool = True) -> Text:
    from forensic_deepdive.cli.style.console import confidence_label

    legend = Text()
    for i, name in enumerate(("EXTRACTED", "INFERRED", "AMBIGUOUS")):
        if i:
            legend.append("   ")
        legend.append_text(confidence_label(name, glyphs=glyphs))
    return legend


def _section(table: Table, label: str, items: list[str]) -> None:
    table.add_row(Text(label, style="label"), Text(", ".join(items), style="value"))


def capability_panel(*, glyphs: bool = True) -> Panel:
    """A Rich Panel summarising the tool's capabilities, every list read from a live
    registry (artifacts / protocols / MCP tools) so it cannot drift from the contract.
    *glyphs* must be ``False`` on a non-UTF-8 / plain console (ASCII confidence markers)."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", no_wrap=True)
    grid.add_column()
    arts = _artifact_names()
    tools = _mcp_tool_names()
    protos = _protocol_names()
    _section(grid, "Artifacts", arts)
    _section(grid, "Protocols", protos)
    _section(grid, "MCP tools", tools)
    grid.add_row(Text("Confidence", style="label"), _confidence_legend(glyphs=glyphs))
    sep = " · " if glyphs else " | "  # middot only when the console can render it
    grid.add_row(
        Text("Surface", style="label"),
        Text(
            sep.join(
                (f"{len(arts)} artifacts", f"{len(protos)} protocols", f"{len(tools)} MCP tools")
            ),
            style="muted",
        ),
    )
    return Panel(
        grid,
        title=Text("Capabilities", style="brand"),
        border_style="border",
        box=SQUARE,
        expand=False,
    )


def render_info(console: Console) -> None:
    """The full ``forensic info`` view: banner + capability panel. Confidence markers use
    glyphs only when the console can render them (UTF-8 TTY); else ASCII letters."""
    glyphs = _can_render_blocks(console)
    render_banner(console)
    console.print(Group(Text(""), capability_panel(glyphs=glyphs)))
