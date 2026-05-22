"""forensic-deepdive CLI.

Subcommands:
  extract  — full pipeline; produces 5 artifacts.
  update   — incremental refresh (v0.1: stub calls extract --force).
  query    — query existing artifacts (v0.2: full MCP-style; v0.1: grep).
  serve    — MCP server stdio mode (v0.2 only).
  version  — print version.

A top-level ``--version`` flag mirrors the ``version`` subcommand so that both
``forensic version`` and ``forensic --version`` work (CLAUDE.md documents the
latter as the smoke test).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from forensic_deepdive import __version__

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
    output: Annotated[Path, typer.Option(help="Where to write artifacts.")] = Path(
        "./docs/codebase"
    ),
    force: Annotated[bool, typer.Option(help="Ignore cache, regenerate.")] = False,
    local: Annotated[bool, typer.Option(help="Use Ollama/LM Studio (v0.2).")] = False,
    with_graphiti: Annotated[bool, typer.Option(help="Enable temporal KG (v0.2).")] = False,
    fast: Annotated[bool, typer.Option(help="Use yek instead of Repomix (v0.2).")] = False,
    stage: Annotated[
        str | None,
        typer.Option(help="Run only one stage: inventory|static|flatten|history|emit"),
    ] = None,
) -> None:
    """Run the full forensic deep-dive pipeline."""
    # TODO(v0.1): implement
    raise NotImplementedError("Stub. See PROGRESS.md for v0.1 implementation plan.")


@app.command()
def update(
    path: Annotated[Path, typer.Argument(help="Repo root to refresh.")],
    since: Annotated[
        str, typer.Option(help="Refresh since this commit or 'last-extract'.")
    ] = "last-extract",
) -> None:
    """Incrementally refresh artifacts. v0.1: calls extract --force."""
    # TODO(v0.1): stub that calls extract(path, force=True)
    raise NotImplementedError(
        "Stub. v0.1 will call extract --force; v0.2 will be truly incremental."
    )


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Question to answer from artifacts.")],
    artifacts_dir: Annotated[Path, typer.Option()] = Path("./docs/codebase"),
) -> None:
    """Query existing artifacts. v0.1: grep-based; v0.2: MCP-style with section extraction."""
    # TODO(v0.1): basic grep wrapper across artifacts
    raise NotImplementedError("Stub.")


@app.command()
def serve(
    transport: Annotated[str, typer.Option(help="stdio | sse")] = "stdio",
) -> None:
    """Start MCP server exposing artifacts as queryable tools. v0.2 only."""
    raise NotImplementedError("MCP server is v0.2. See DEC-001.")


if __name__ == "__main__":
    app()
