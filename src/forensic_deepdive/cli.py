"""forensic-deepdive CLI.

Subcommands:
  extract  — full pipeline; produces 5 artifacts.
  update   — incremental refresh (v0.1: stub calls extract --force).
  query    — query existing artifacts (v0.2: full MCP-style; v0.1: grep).
  serve    — MCP server stdio mode (v0.2), or `--ui` Sigma.js graph explorer (v0.4).
  version  — print version.

A top-level ``--version`` flag mirrors the ``version`` subcommand so that both
``forensic version`` and ``forensic --version`` work (CLAUDE.md documents the
latter as the smoke test).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from forensic_deepdive import __version__

if TYPE_CHECKING:
    from forensic_deepdive.pipeline import ExtractResult

app = typer.Typer(
    name="forensic",
    help="Forensic deep-dive of any codebase. Produces 5 durable markdown artifacts.",
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    """Eager callback for the top-level ``--version`` flag."""
    if value:
        console.print(f"forensic-deepdive {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Forensic deep-dive of any codebase. Produces 5 durable markdown artifacts."""


@app.command()
def version() -> None:
    """Print version and exit."""
    console.print(f"forensic-deepdive {__version__}")


@app.command()
def extract(
    path: Annotated[Path, typer.Argument(help="Repo root to analyze.")],
    output: Annotated[
        Path | None,
        typer.Option(help="Where to write artifacts (default: <repo>/docs/codebase)."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Ignore cache, regenerate.")] = False,
    workers: Annotated[
        int | None,
        typer.Option(
            help="DEC-035: parse worker count (default min(cpu-1,16); 1 = serial).",
        ),
    ] = None,
    legacy_repomix: Annotated[
        bool,
        typer.Option(
            "--legacy-repomix",
            help="DEC-017: also run Repomix flatten (demoted to opt-in in v0.2).",
        ),
    ] = False,
    semantic: Annotated[
        bool,
        typer.Option(
            "--semantic",
            help="DEC-042: build offline ONNX embeddings for hybrid NL query "
            "(needs the [semantic] extra + a local model).",
        ),
    ] = False,
    local: Annotated[bool, typer.Option(help="Use Ollama/LM Studio (v0.2).")] = False,
    with_graphiti: Annotated[bool, typer.Option(help="Enable temporal KG (v0.2).")] = False,
    fast: Annotated[bool, typer.Option(help="Use yek instead of Repomix (v0.2).")] = False,
    stage: Annotated[
        str | None,
        typer.Option(help="Run only one stage: inventory|static|flatten|history|emit"),
    ] = None,
) -> None:
    """Run the full forensic deep-dive pipeline."""
    from forensic_deepdive.pipeline import run_extract

    for flag, enabled in (("--local", local), ("--with-graphiti", with_graphiti), ("--fast", fast)):
        if enabled:
            console.print(f"[yellow]{flag} is a v0.2 flag; ignored in v0.1.[/yellow]")
    if stage is not None:
        console.print("[yellow]--stage is not implemented in v0.1; running all stages.[/yellow]")

    try:
        result = run_extract(
            path,
            output,
            force=force,
            flatten=legacy_repomix,
            workers=workers,
            semantic=semantic,
        )
    except (NotADirectoryError, FileNotFoundError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    _print_extract_summary(result)


@app.command()
def update(
    path: Annotated[Path, typer.Argument(help="Repo root to refresh.")],
    since: Annotated[
        str, typer.Option(help="Refresh since this commit or 'last-extract'.")
    ] = "last-extract",
    workers: Annotated[
        int | None,
        typer.Option(help="DEC-035: parse worker count (default min(cpu-1,16); 1 = serial)."),
    ] = None,
) -> None:
    """Incrementally refresh artifacts. v0.1: re-runs extract with --force."""
    from forensic_deepdive.pipeline import run_extract

    console.print(
        "[dim]v0.1 update is a full re-extract (--force); "
        "incremental refresh arrives in v0.2.[/dim]"
    )
    try:
        result = run_extract(path, None, force=True, workers=workers)
    except (NotADirectoryError, FileNotFoundError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    _print_extract_summary(result)


def _print_extract_summary(result: ExtractResult) -> None:
    """Print a human-readable summary of an extract run."""
    if result.cache_hit:
        console.print(
            f"[green]Cache hit[/green]: artifacts already current in "
            f"[bold]{result.output_dir}[/bold] (use --force to regenerate)."
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
    console.print(f"[bold green]forensic extract complete[/bold green]: {facts.repo_name}")
    console.print(f"  Files analyzed : {facts.file_count}  ({languages})")
    console.print(
        f"  Symbol graph   : {facts.symbol_graph.graph.number_of_nodes()} files, "
        f"{facts.symbol_graph.graph.number_of_edges()} edges"
    )
    console.print(f"  Flatten        : {'Repomix ok' if result.flatten_ok else 'skipped'}")
    console.print(f"  Artifacts      : {result.output_dir}")
    for name in sorted(result.artifacts):
        console.print(f"    - {name}")
    if result.shims.written:
        console.print(f"  Shims written  : {', '.join(p.name for p in result.shims.written)}")
    if result.shims.skipped:
        console.print(
            f"  Shims skipped  : {', '.join(p.name for p in result.shims.skipped)} (already exist)"
        )


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Substring to search for in the artifacts.")],
    artifacts_dir: Annotated[
        Path,
        typer.Option(help="Artifacts dir (or repo root). Default: ./docs/codebase."),
    ] = Path("./docs/codebase"),
    context: Annotated[int, typer.Option(help="Lines of context around each match.")] = 2,
    case_sensitive: Annotated[bool, typer.Option(help="Case-sensitive match.")] = False,
) -> None:
    """Grep the generated artifacts for *question*. v0.1: substring match."""
    from forensic_deepdive.query import query_artifacts

    try:
        result = query_artifacts(
            artifacts_dir, question, context=context, case_sensitive=case_sensitive
        )
    except NotADirectoryError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if not result.hits:
        console.print(f"[yellow]No matches for '{question}' in {result.artifacts_dir}[/yellow]")
        return

    console.print(
        f"[bold green]{len(result.hits)} match(es)[/bold green] for "
        f"'{question}' across {len(result.files_searched)} artifact(s) "
        f"in {result.artifacts_dir}:"
    )
    for hit in result.hits:
        console.print(f"\n[cyan]{hit.file}:{hit.line}[/cyan]")
        for line in hit.context_before:
            console.print(f"  {line}")
        console.print(f"[bold]> {hit.text}[/bold]")
        for line in hit.context_after:
            console.print(f"  {line}")


@app.command()
def graph(
    target: Annotated[
        str,
        typer.Argument(help="Symbol or file to centre the diagram on (ignored with --central)."),
    ] = "",
    repo: Annotated[Path, typer.Option(help="Repo with a built .deepdive/graph.lbug.")] = Path("."),
    graph_db: Annotated[
        Path | None,
        typer.Option(
            "--graph", help="Explicit .lbug path (overrides <repo>/.deepdive/graph.lbug)."
        ),
    ] = None,
    fmt: Annotated[str, typer.Option("--format", help="Only 'mermaid' in v0.3.")] = "mermaid",
    diagram: Annotated[
        str | None,
        typer.Option(help="flowchart | classDiagram (default: auto by target kind)."),
    ] = None,
    depth: Annotated[int, typer.Option(help="Neighborhood depth (flowchart).")] = 2,
    max_nodes: Annotated[int, typer.Option(help="Node cap (default 40).")] = 40,
    direction: Annotated[str, typer.Option(help="in | out | both (flowchart).")] = "both",
    central: Annotated[
        bool, typer.Option("--central", help="Diagram the top-N central symbols instead.")
    ] = False,
) -> None:
    """Render a bounded Mermaid diagram of the code graph (DEC-039).

    Prints a fenced ```mermaid block, paste-ready into Claude Code, a PR, or
    Notion. Edge dash style encodes confidence (solid=EXTRACTED,
    dashed=INFERRED, dotted=AMBIGUOUS)."""
    from forensic_deepdive.emit.mermaid import render_mermaid

    db_path = graph_db or repo / ".deepdive" / "graph.lbug"
    if not db_path.exists():
        console.print(f"[red]No graph at {db_path}.[/red] Run `forensic extract` first.")
        raise typer.Exit(code=1)
    if not central and not target:
        console.print("[red]Pass a target symbol/file, or --central.[/red]")
        raise typer.Exit(code=1)

    result = render_mermaid(
        db_path,
        target or None,
        diagram=diagram,
        depth=depth,
        max_nodes=max_nodes,
        direction=direction,
        central=central,
    )
    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(code=1)
    if result.get("unresolved"):
        console.print(f"[yellow]Could not resolve target '{target}' in the graph.[/yellow]")
        raise typer.Exit(code=1)
    # Print the raw fenced block (no Rich markup) so it copies cleanly.
    print(result["mermaid"])
    if result.get("truncated"):
        console.print(
            f"[dim]Diagram truncated at {max_nodes} nodes; pass --max-nodes to widen.[/dim]"
        )


@app.command(name="list")
def list_repos() -> None:
    """List repos in the multi-repo registry (DEC-018)."""
    from forensic_deepdive.registry import load

    registry = load()
    if not registry.repos:
        console.print("[dim]No repos in registry. Run `forensic extract <repo>` to add one.[/dim]")
        return
    console.print(
        f"[bold green]{len(registry.repos)} registered repo(s)[/bold green] "
        f"in the forensic-deepdive registry:"
    )
    for entry in sorted(registry.repos, key=lambda r: r.name):
        graph = entry.graph_db_path or "[dim](no graph)[/dim]"
        console.print(
            f"  [cyan]{entry.name}[/cyan] — {entry.repo_path}\n"
            f"    graph: {graph}\n"
            f"    last extracted: {entry.last_extracted_at}"
        )


@app.command()
def serve(
    repo: Annotated[
        Path,
        typer.Argument(help="Repo with a built `.deepdive/graph.lbug`."),
    ] = Path("."),
    graph: Annotated[
        Path | None,
        typer.Option(help="Explicit .lbug path (overrides <repo>/.deepdive/graph.lbug)."),
    ] = None,
    transport: Annotated[str, typer.Option(help="MCP transport: stdio (default).")] = "stdio",
    ui: Annotated[
        bool,
        typer.Option("--ui", help="Serve the Sigma.js graph explorer over local HTTP (DEC-053)."),
    ] = False,
    host: Annotated[
        str,
        typer.Option(help="Bind host for --ui. Loopback only (127.0.0.1); 0.0.0.0 is refused."),
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port for --ui (0 = pick a free port).")] = 8765,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Don't auto-open a browser for --ui.")
    ] = False,
) -> None:
    """Serve the graph: MCP stdio (default), or the Sigma.js explorer via ``--ui``.

    Default — the 9 composite MCP tools (impact / context / archaeology / flow /
    query / record_insight / recall_insights / visualize / trace) over stdio,
    consumed by Claude Code, Cursor, Codex, Continue, Cline.

    ``--ui`` (DEC-053) — a read-only, 127.0.0.1-only HTTP server hosting a
    vendored Sigma.js (WebGL) whole-graph explorer with mandatory level-of-detail
    bounding + filtering (edge type / confidence / language / directory), the
    cross-stack ROUTES_TO joins highlighted.
    """
    db_path = graph or repo / ".deepdive" / "graph.lbug"
    if not db_path.exists():
        console.print(
            f"[red]No graph at {db_path}.[/red] Run `forensic extract` first to build it."
        )
        raise typer.Exit(code=1)

    if ui:
        from forensic_deepdive.serve import is_loopback_host, serve_ui

        if not is_loopback_host(host):
            console.print(
                f"[red]Refusing to bind non-loopback host {host!r}.[/red] "
                "`serve --ui` is 127.0.0.1-only (never 0.0.0.0)."
            )
            raise typer.Exit(code=1)
        console.print(
            f"[bold green]forensic serve --ui[/bold green] — graph explorer (read-only, {host})"
        )
        try:
            serve_ui(
                db_path,
                host=host,
                port=port,
                open_browser=not no_browser,
                on_ready=lambda url: console.print(
                    f"  serving [cyan]{url}[/cyan]  (Ctrl-C to stop)"
                ),
            )
        except KeyboardInterrupt:
            console.print("\n[dim]stopped.[/dim]")
        return

    if transport != "stdio":
        console.print(
            f"[red]Only stdio is supported for the MCP transport; got {transport!r}.[/red]"
        )
        raise typer.Exit(code=1)
    import asyncio

    from forensic_deepdive.mcp_server import serve_stdio

    asyncio.run(serve_stdio(db_path))


insights_app = typer.Typer(
    name="insights",
    help="Manage the durable agent-insight store (lane iii).",
    no_args_is_help=True,
)
app.add_typer(insights_app)


@insights_app.command("push")
def insights_push(
    repo: Annotated[
        Path, typer.Argument(help="Repo whose insight shadow-ref to push (default: cwd).")
    ] = Path("."),
    remote: Annotated[
        str | None,
        typer.Option(help="Git remote to push to (default: origin, else the first remote)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be pushed without pushing."),
    ] = False,
) -> None:
    """Publish the local insight shadow-ref (``refs/forensic-deepdive/insights``) to a remote
    (DEC-075). **Explicit only** — insights never push automatically (the never-push
    discipline extends to the insight ref). Best-effort: a clear message if there's no ref,
    no remote, or no git repo."""
    from forensic_deepdive.insights.shadow_ref import push_shadow_ref, save_to_shadow_ref

    # Refresh the ref from the current JSONL first, so a push always reflects local insights.
    save_to_shadow_ref(repo, repo / ".deepdive" / "insights.jsonl")
    ok, message = push_shadow_ref(repo, remote=remote, dry_run=dry_run)
    if ok:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[yellow]insights push: {message}[/yellow]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
