"""Styled command rendering (DEC-079, v0.7 Step 7).

Console-only renderers for ``extract`` (a status line with the colour-coded confidence
split) and ``trace`` (a confidence-coloured Rich ``Tree`` with the ``via`` protocol on each
edge — plus a preserved plain/JSON machine mode for piping). The presentation keystone holds:
nothing here touches ``emit/`` or a machine-output stream; ``trace --json`` / a non-TTY
``trace`` emit plain JSON (no ANSI).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rich.text import Text
from rich.tree import Tree

from forensic_deepdive.cli.style.console import confidence_label

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from forensic_deepdive.pipeline import ExtractResult

_CONFIDENCE_ORDER = ("EXTRACTED", "INFERRED", "AMBIGUOUS")


def _glyphs_ok(console: Console) -> bool:
    """Block/●◐○ glyphs only on a UTF-8 colour TTY (else ASCII — cp1252-pipe safe)."""
    enc = (console.encoding or "").lower()
    return console.is_terminal and not console.no_color and "utf" in enc


def _cross_stack_split(graph_db_path: Path) -> dict[str, int]:
    """``{confidence: count}`` over the cross-stack ROUTES_TO edges, read-only from the
    freshly built graph. Best-effort — any failure yields ``{}`` (the summary still prints)."""
    try:
        from forensic_deepdive.graph import LadybugStore

        with LadybugStore(graph_db_path) as store:
            rows = store.query(
                "MATCH ()-[r:ROUTES_TO]->() RETURN r.confidence, count(r) ORDER BY r.confidence"
            )
            return {str(conf): int(n) for conf, n in rows}
    except Exception:
        return {}


def _confidence_split_text(split: dict[str, int], *, glyphs: bool) -> Text:
    """``● E:12  ◐ I:3  ○ A:1`` — the confidence split, coloured + never colour-alone."""
    total = sum(split.values())
    body = Text(f"{total} cross-stack route(s)", style="value")
    if total:
        body.append("  (")
        for i, name in enumerate(_CONFIDENCE_ORDER):
            if i:
                body.append("  ")
            chip = confidence_label(name, compact=True, glyphs=glyphs)
            chip.append(f" {split.get(name, 0)}", style="muted")
            body.append_text(chip)
        body.append(")")
    return body


def print_extract_summary(console: Console, result: ExtractResult) -> None:
    """The styled post-``extract`` summary (replaces the plain print). Console-only; the
    artifacts on disk are unchanged plain markdown."""
    if result.cache_hit:
        console.print(
            Text("✓ cache hit", style="ok").append(
                f" — artifacts already current in {result.output_dir} (use --force).",
                style="muted",
            )
        )
        return

    facts = result.facts
    assert facts is not None  # only None on a cache hit
    languages = (
        ", ".join(
            f"{name} ({count})"
            for name, count in sorted(
                facts.language_breakdown.items(), key=lambda kv: (-kv[1], kv[0])
            )
        )
        or "none"
    )
    console.print(
        Text("✓ forensic extract complete", style="ok").append(
            f"  {facts.repo_name}", style="brand"
        )
    )
    g = facts.symbol_graph.graph
    rows = [
        ("Files", f"{facts.file_count}  ({languages})"),
        ("Graph", f"{g.number_of_nodes()} files · {g.number_of_edges()} edges"),
        ("Artifacts", f"{result.output_dir}"),
    ]
    for label, val in rows:
        console.print(Text(f"  {label:>10}  ", style="label").append(val, style="value"))
    # The colour-coded confidence split over the cross-stack routes (the v0.7 headline).
    split = _cross_stack_split(facts.graph_db_path) if facts.graph_db_path else {}
    console.print(
        Text(f"  {'Routes':>10}  ", style="label").append_text(
            _confidence_split_text(split, glyphs=_glyphs_ok(console))
        )
    )
    for name in sorted(result.artifacts):
        console.print(Text(f"    - {name}", style="muted"))
    if result.shims.written:
        console.print(
            Text("  Shims", style="label").append(
                f"  {', '.join(p.name for p in result.shims.written)}", style="muted"
            )
        )


# --- trace -------------------------------------------------------------------


def _endpoint_label(chain: dict[str, Any], conf_field: str, *, glyphs: bool) -> Text:
    """``[GET] /api/users  via http  ● EXTRACTED`` — one endpoint edge."""
    method = chain.get("method") or "*"
    path = chain.get("normalized_path") or chain.get("endpoint", "")
    via = chain.get("endpoint", "").split("::", 1)[0] or "?"
    label = Text(f"[{method}] ", style="brand")
    label.append(path, style="value")
    label.append(f"  via {via}  ", style="muted")
    label.append_text(confidence_label(chain.get(conf_field, ""), glyphs=glyphs))
    return label


def render_trace(console: Console, payload: dict[str, Any], *, plain: bool) -> None:
    """Render a ``trace`` payload. *plain* (or ``--json`` / a non-TTY) → JSON for piping;
    otherwise a confidence-coloured Rich ``Tree``."""
    if plain or not console.is_terminal:
        # Machine mode: plain JSON, no ANSI/highlight even on a colour TTY (pipe-safe).
        console.print(json.dumps(payload, indent=2), highlight=False, markup=False)
        return
    if payload.get("error"):
        console.print(Text(f"trace: {payload['error']}", style="err"))
        return
    if payload.get("unresolved") or not payload.get("matches"):
        console.print(
            Text(f"trace: no symbol matched '{payload.get('symbol', '')}'.", style="warn")
        )
        return

    glyphs = _glyphs_ok(console)
    direction = payload.get("direction", "downstream")
    matched = ", ".join(m["qualified_name"] for m in payload["matches"][:3])
    root = Tree(Text(f"{matched}  ({direction})", style="brand"))
    chains = payload.get("chains", [])
    if not chains:
        root.add(
            Text("no cross-stack chain from here (no CALLS_ENDPOINT / HANDLES).", style="muted")
        )
    for chain in chains:
        if direction == "downstream":
            node = root.add(_endpoint_label(chain, "call_confidence", glyphs=glyphs))
            if chain.get("unlocated"):
                node.add(Text("⚠ endpoint we can't locate (no handler)", style="warn"))
                continue
            handler = node.add(
                Text("→ ", style="muted")
                .append(chain.get("handler", ""), style="value")
                .append("  ")
                .append_text(confidence_label(chain.get("handles_confidence", ""), glyphs=glyphs))
            )
            for tail in chain.get("downstream", []):
                handler.add(Text(tail if isinstance(tail, str) else str(tail), style="muted"))
        else:  # upstream
            node = root.add(_endpoint_label(chain, "handles_confidence", glyphs=glyphs))
            for caller in chain.get("callers", []):
                node.add(
                    Text("← ", style="muted")
                    .append(caller.get("consumer", ""), style="value")
                    .append("  ")
                    .append_text(confidence_label(caller.get("confidence", ""), glyphs=glyphs))
                )
    console.print(root)
