"""Guided onboarding wizard — ``forensic onboard`` (DEC-101, v0.9 Track A step 3).

A linear, re-runnable flow that walks a newcomer from an unanalyzed repo to a
wired MCP server, surfacing the exact gotchas the manual-test history recorded:

  1. confirm the repo
  2. run ``extract`` (the cache makes a re-run a no-op — the wizard is idempotent)
  3. point at ``AGENT_BRIEF.md`` first, then the other four artifacts
  4. print the **correct** MCP client snippet — rendered by
     :mod:`forensic_deepdive.cli.mcp_snippet`, the single source of truth
     ``forensic mcp-config`` also prints (never a second hardcoded copy), with
     the dev/uvx form auto-picked from whether we run out of a source checkout
  5. state the restart-and-approve step, which no config snippet can imply

Keystones: zero-LLM; the tool/artifact contract is frozen (this orchestrates
existing commands and adds nothing); cp1252 + ``--plain`` parity.

``prompt_toolkit`` is needed only for the *prompts*: a ``--yes`` run takes every
default, asks nothing, and therefore works on the lean agent-first install (and
in CI). Interactive runs without the extra fail with the actionable install hint.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.text import Text

from forensic_deepdive.cli.interactive import INSTALL_HINT
from forensic_deepdive.cli.mcp_snippet import CLIENTS, is_source_checkout, render_mcp_config
from forensic_deepdive.cli.style import get_console, print_extract_summary

if TYPE_CHECKING:
    from rich.console import Console

# Wizard prompt history, beside the REPL's (DEC-018 convention).
DEFAULT_HISTORY_FILE = Path.home() / ".deepdive" / "onboard_history"

# Display order = the artifact contract order; AGENT_BRIEF is the headline and
# is called out separately, so it is last here (read the brief, then the rest).
ARTIFACT_ORDER = (
    "MAP.md",
    "HOTPATHS.md",
    "ARCHAEOLOGY.md",
    "MENTAL_MODEL.md",
    "AGENT_BRIEF.md",
)
BRIEF = "AGENT_BRIEF.md"

_RESTART_NOTE = """\
Restart the client, then approve the server when it asks — an MCP server is
never enabled by the config file alone. In Claude Code the approval prompt
appears on the next launch; in Cursor/VS Code, reload the window.
"""

_CANCELLED = "onboarding cancelled — nothing was written."


class _CancelledError(Exception):
    """The user answered 'no', or pressed Ctrl-C / Ctrl-D at a prompt."""


def run_onboard(
    repo: Path,
    *,
    yes: bool = False,
    force: bool = False,
    client: str | None = None,
    dev: bool | None = None,
    console: Console | None = None,
    history_file: Path | None = None,
    pt_input: Any | None = None,
    pt_output: Any | None = None,
) -> int:
    """Run the wizard against *repo*. Returns an exit code.

    *yes* takes every default without prompting (scriptable, CI-safe, and the
    only mode that doesn't need the ``[interactive]`` extra). *dev* forces the
    snippet form; ``None`` auto-picks it from :func:`is_source_checkout`.
    *console* / *history_file* / *pt_input* / *pt_output* exist for the test
    harness and the session shell; the CLI passes none of them.
    """
    out = console or get_console()
    repo = Path(repo).resolve()
    if not repo.is_dir():
        out.print(f"[err]Error:[/err] {repo} is not a directory.")
        return 1

    ask = _make_asker(out, yes, history_file, pt_input, pt_output)
    if ask is None:
        return 1  # the extra is missing and we'd have to prompt

    _soft(out, Text("deepdive onboard", style="brand").append(f" — {repo}", style="muted"))
    try:
        if not ask.yes_no("Analyze this repo?", default=True):
            raise _CancelledError
        _step(out, 1, "extract")
        if not _extract(out, repo, ask, force=force):
            return 1
        _step(out, 2, "read the brief")
        _report_artifacts(out, repo)
        _step(out, 3, "wire the MCP server")
        chosen = client or ask.choice("Which MCP client?", CLIENTS, default="claude")
        _print_snippet(out, repo, chosen, dev)
        _step(out, 4, "restart and approve")
        out.print(_RESTART_NOTE, markup=False, highlight=False)
        _print_next_steps(out, repo)
    except _CancelledError:
        out.print(Text(_CANCELLED, style="warn"))
        return 0
    return 0


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _soft(out: Console, renderable: Text | str) -> None:
    """Print without Rich's hard wrap. Every wizard line carries a path or a
    command the user copy-pastes; a wrap inserted mid-path breaks the paste.
    Soft-wrapping leaves that to the terminal, which reflows instead."""
    out.print(renderable, soft_wrap=True)


def _step(out: Console, number: int, title: str) -> None:
    out.print(Text(f"\n[{number}/4] {title}", style="brand"))


def _extract(out: Console, repo: Path, ask: _Asker, *, force: bool) -> bool:
    """Run the pipeline. Re-running is safe: the cache turns it into a no-op,
    and an existing-artifacts run asks before spending the time again."""
    from forensic_deepdive.pipeline import run_extract

    artifacts_dir = repo / "docs" / "codebase"
    if (artifacts_dir / BRIEF).exists() and not force:
        _soft(out, Text(f"artifacts already exist in {artifacts_dir}", style="muted"))
        if not ask.yes_no("Re-analyze the repo?", default=False):
            out.print(Text("kept the existing artifacts.", style="muted"))
            return True
    try:
        with out.status(f"[brand]forensic extract[/brand] — analyzing {repo} …"):
            result = run_extract(repo, None, force=force)
    except (NotADirectoryError, FileNotFoundError) as exc:
        out.print(f"[err]Error:[/err] {exc}")
        return False
    print_extract_summary(out, result)
    return True


def _report_artifacts(out: Console, repo: Path) -> None:
    """Point at AGENT_BRIEF.md first — it is the one an agent loads every session."""
    artifacts_dir = repo / "docs" / "codebase"
    brief = artifacts_dir / BRIEF
    if brief.exists():
        size = brief.stat().st_size
        _soft(
            out,
            Text("  read first: ", style="muted")
            .append(str(brief), style="value")
            .append(f"  ({size} bytes)", style="muted"),
        )
    for name in ARTIFACT_ORDER:
        path = artifacts_dir / name
        if name != BRIEF and path.exists():
            _soft(out, Text("  also: ", style="muted").append(str(path), style="value"))
    graph = repo / ".deepdive" / "graph.lbug"
    if graph.exists():
        _soft(
            out,
            Text("  graph: ", style="muted")
            .append(str(graph), style="value")
            .append("  (queried by the MCP server, `forensic repl`, `forensic browse`)", "muted"),
        )


def _print_snippet(out: Console, repo: Path, client: str, dev: bool | None) -> None:
    """Print the client config, rendered by the one shared renderer."""
    use_dev = is_source_checkout() if dev is None else dev
    why = (
        "running from a source checkout, so this uses `uv run --project`"
        if use_dev
        else "running from an installed package, so this uses `uvx`"
    )
    out.print(Text(f"  {client} config ({why}):", style="muted"))
    snippet = render_mcp_config(repo, client=client, dev=use_dev)
    out.print(snippet, markup=False, highlight=False, soft_wrap=True)
    dest = ".mcp.json" if client in ("claude", "cursor") else "your client's config file"
    _soft(
        out,
        Text("  paste into ", style="muted")
        .append(dest, style="value")
        .append("  (or: ", style="muted")
        .append(f"forensic mcp-config --repo {repo}{' --dev' if use_dev else ''}", style="value")
        .append(")", style="muted"),
    )


def _print_next_steps(out: Console, repo: Path) -> None:
    out.print(Text("\nnext:", style="brand"))
    for cmd, what in (
        (f"deepdive --repo {repo}", "the session shell — everything below, one open store"),
        ("forensic repl", "ask questions over the graph"),
        ("forensic browse", "the full-screen graph browser"),
        ("forensic trace <symbol>", "a cross-stack feature slice"),
    ):
        line = Text("  ", style="muted").append(cmd, style="value")
        _soft(out, line.append(f"  - {what}", style="muted"))


# ---------------------------------------------------------------------------
# Prompting (the only part that needs the extra)
# ---------------------------------------------------------------------------


class _Asker:
    """Yes/no + choice prompts, or every default when ``--yes`` is in force."""

    def __init__(self, session: Any | None) -> None:
        self._session = session

    def _read(self, question: str, hint: str) -> str:
        if self._session is None:
            return ""
        try:
            return self._session.prompt(f"{question} [{hint}] ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise _CancelledError from exc

    def yes_no(self, question: str, *, default: bool) -> bool:
        answer = self._read(question, "Y/n" if default else "y/N").lower()
        if not answer:
            return default
        return answer in ("y", "yes")

    def choice(self, question: str, options: tuple[str, ...], *, default: str) -> str:
        while True:
            answer = self._read(question, "/".join(options) + f", default {default}").lower()
            if not answer:
                return default
            if answer in options:
                return answer
            if self._session is None:  # pragma: no cover — unreachable with --yes
                return default


def _make_asker(
    out: Console,
    yes: bool,
    history_file: Path | None,
    pt_input: Any | None,
    pt_output: Any | None,
) -> _Asker | None:
    """Build the prompt source. ``None`` means the extra is missing for a run
    that would have to prompt — the caller prints nothing more and exits 1."""
    if yes:
        return _Asker(None)
    try:
        from prompt_toolkit import PromptSession  # noqa: PLC0415 — [interactive] extra
        from prompt_toolkit.history import FileHistory  # noqa: PLC0415
    except ImportError:
        out.print(INSTALL_HINT, markup=False, highlight=False)
        out.print(
            "\nOr run the wizard non-interactively: `forensic onboard --yes`",
            markup=False,
            highlight=False,
        )
        return None
    hist_path = history_file or DEFAULT_HISTORY_FILE
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    return _Asker(
        PromptSession(history=FileHistory(str(hist_path)), input=pt_input, output=pt_output)
    )
