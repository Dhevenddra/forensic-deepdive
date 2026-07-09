"""The `deepdive` session shell (DEC-102, v0.9 Track A step 4).

The umbrella surface: launch ``deepdive`` inside a repo and run the existing
commands as in-session commands with shared state and one history — it
**orchestrates** the REPL, the browser and the wizard, and re-implements none of
them.

The store lifecycle is the load-bearing design. On Windows LadybugDB takes an
exclusive file lock, so a *second* handle on the same graph raises ``Could not
set lock on file`` (on Linux the same open happens to succeed — CI proved the
difference, and depending on it would make the shell platform-dependent). Yet
``trace``/``impact``/``flow``/``diagram``/``browse`` all open their own handle by
design (the frozen tool contract passes a ``db_path``, never a store).
:class:`StoreSession` therefore **borrows**:

* the hot path (natural-language query, ``:cypher``) runs on ONE held-open store
  — the DEC-099 lifecycle, connect-once across many questions;
* every path-based tool runs inside :meth:`StoreSession.released`, which closes
  the handle first and lets the *next* query lazily re-open it.

That same borrow makes an in-session ``extract`` correct for free: the store is
released before the pipeline rewrites the graph, and the following command
re-opens the new one (no stale handle, no cache of a dead schema).

``browse`` is dispatched blocking from the command loop, never nested inside a
prompt: ``PromptSession.prompt()`` has already returned when we launch the
Textual App, and the App reclaims the terminal on exit (DEC-100's rule).
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.text import Text

from forensic_deepdive.cli.interactive import INSTALL_HINT, TERMINAL_HINT, terminal_errors
from forensic_deepdive.cli.style import get_console
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.query.lexical import lexical_index_path_for_db

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rich.console import Console

DEFAULT_HISTORY_FILE = Path.home() / ".deepdive" / "shell_history"

GRAPH_SUBPATH = (".deepdive", "graph.lbug")

_COMMANDS = (
    "extract",
    "query",
    "trace",
    "impact",
    "flow",
    "diagram",
    "browse",
    "onboard",
    "serve",
)
_META = (":help", ":cypher", ":quit", ":exit")

_HELP_TEXT = """\
Commands (a bare line that doesn't start with one of these is a NL query):
  <text> | query <text>   natural-language query over the graph (no LLM)
  :cypher <query>         raw Cypher against the graph (alias :c)
  trace <symbol>          cross-stack slice   [--upstream] [--depth N]
  impact <symbol>         blast radius of a change
  flow <symbol>           the call flow through a symbol
  extract                 (re-)analyze this repo, then reopen the graph  [--force]
  diagram                 regenerate ARCHITECTURE.md
  browse                  full-screen graph browser (returns here on quit)
  onboard                 the guided setup wizard
  serve                   the stdio MCP server (takes over this terminal)
  :help                   this list
  :quit / :exit           leave (Ctrl-D also exits; Ctrl-C cancels the line)

The graph is held open across queries; commands that need their own handle
release it and the next query reopens it.
"""

_NO_GRAPH = "no graph yet — run `extract` here, or `onboard` for the guided setup."


class StoreSession:
    """Owns the single LadybugDB handle for a shell session.

    Lazily connects, and hands the handle back around any tool that opens its
    own (mandatory on Windows, where the DB lock is exclusive; correct
    everywhere). Re-entrant use is not supported (a shell is one loop, one
    thread).
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._store: LadybugStore | None = None

    @property
    def has_graph(self) -> bool:
        return self.db_path.exists()

    @property
    def store(self) -> LadybugStore:
        """The held-open store, connecting on first use after a release."""
        if self._store is None:
            store = LadybugStore(self.db_path)
            store.connect()
            self._store = store
        return self._store

    @property
    def index_path(self) -> Path:
        return lexical_index_path_for_db(self.db_path)

    def release(self) -> None:
        """Drop the handle (idempotent). The next ``.store`` re-opens it."""
        if self._store is not None:
            self._store.close()
            self._store = None

    @contextmanager
    def released(self) -> Iterator[None]:
        """Run a block with no handle held — the only way a ``db_path``-taking
        tool (or an ``extract`` that rewrites the graph) can take the lock."""
        self.release()
        yield

    def close(self) -> None:
        self.release()


def run_shell(
    repo: Path,
    *,
    graph: Path | None = None,
    semantic: bool = False,
    console: Console | None = None,
    history_file: Path | None = None,
    pt_input: Any | None = None,
    pt_output: Any | None = None,
) -> int:
    """Run the session shell against *repo*. Returns an exit code."""
    try:
        from prompt_toolkit import PromptSession  # noqa: PLC0415 — [interactive] extra
        from prompt_toolkit.completion import WordCompleter  # noqa: PLC0415
        from prompt_toolkit.history import FileHistory  # noqa: PLC0415
    except ImportError:
        (console or get_console()).print(INSTALL_HINT, markup=False, highlight=False)
        return 1

    out = console or get_console()
    repo = Path(repo).resolve()
    session = StoreSession(graph or repo.joinpath(*GRAPH_SUBPATH))

    hist_path = history_file or DEFAULT_HISTORY_FILE
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        prompt: PromptSession[str] = PromptSession(
            history=FileHistory(str(hist_path)),
            completer=WordCompleter([*_COMMANDS, *_META], ignore_case=True),
            input=pt_input,
            output=pt_output,
        )
    except terminal_errors():
        out.print(TERMINAL_HINT, markup=False, highlight=False)
        return 1

    out.print(
        Text("deepdive", style="brand").append(f" — {repo}", style="muted"),
        soft_wrap=True,
    )
    if not session.has_graph:
        out.print(Text(_NO_GRAPH, style="warn"), soft_wrap=True)
    out.print(Text("(:help for commands, Ctrl-D to exit)", style="muted"))

    try:
        while True:
            try:
                line = prompt.prompt("deepdive> ").strip()
            except KeyboardInterrupt:
                continue  # cancel the line, keep the session
            except EOFError:
                break
            if not line:
                continue
            if line in (":quit", ":exit", ":q"):
                break
            _dispatch(out, session, repo, line, semantic=semantic)
    finally:
        session.close()
    return 0


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _dispatch(
    out: Console, session: StoreSession, repo: Path, line: str, *, semantic: bool
) -> None:
    """Run one command line against the session."""
    from forensic_deepdive.cli.interactive.repl import run_cypher, run_nl

    if line == ":help":
        out.print(_HELP_TEXT, markup=False, highlight=False)
        return
    if line.startswith((":cypher ", ":c ")):
        if _needs_graph(out, session):
            run_cypher(out, session.store, line.split(" ", 1)[1].strip())
        return
    if line.startswith(":"):
        out.print(f"[warn]unknown command {line.split()[0]!r} — :help lists them.[/warn]")
        return

    word, _, rest = line.partition(" ")
    rest = rest.strip()
    # `query <text>` is the explicit form; any line that doesn't open with a
    # known command word is a natural-language question (the REPL's rule).
    if word.lower() == "query" or word.lower() not in _HANDLERS:
        question = rest if word.lower() == "query" else line
        if not question:
            out.print("[warn]query needs a question, e.g. `query where is auth handled`[/warn]")
        elif _needs_graph(out, session):
            run_nl(out, session.store, session.index_path, question, semantic=semantic)
        return
    _HANDLERS[word.lower()](out, session, repo, rest)


def _needs_graph(out: Console, session: StoreSession) -> bool:
    if not session.has_graph:
        out.print(Text(_NO_GRAPH, style="warn"))
        return False
    return True


def _flags(rest: str) -> tuple[list[str], dict[str, str | bool]]:
    """Split ``sym --upstream --depth 3`` into positionals + flags."""
    tokens = rest.split()
    positional: list[str] = []
    flags: dict[str, str | bool] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--"):
            name = token[2:]
            if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                flags[name] = tokens[index + 1]
                index += 1
            else:
                flags[name] = True
        else:
            positional.append(token)
        index += 1
    return positional, flags


def _int_flag(flags: dict[str, str | bool], name: str, default: int) -> int:
    value = flags.get(name)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _print_json(out: Console, payload: dict[str, Any]) -> None:
    import json

    out.print(json.dumps(payload, indent=2, ensure_ascii=True), markup=False, highlight=False)


def _cmd_extract(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    """Re-analyze in place. The store is released first (the pipeline rewrites
    the very file we hold), and the next command reopens the new graph."""
    from forensic_deepdive.cli.style import print_extract_summary
    from forensic_deepdive.pipeline import run_extract

    _, flags = _flags(rest)
    with session.released():
        try:
            with out.status(f"[brand]forensic extract[/brand] — analyzing {repo} …"):
                result = run_extract(repo, None, force=bool(flags.get("force")))
        except (NotADirectoryError, FileNotFoundError) as exc:
            out.print(f"[err]Error:[/err] {exc}")
            return
    print_extract_summary(out, result)
    if session.has_graph:
        out.print(Text("graph reopened on the next query.", style="muted"))


def _cmd_trace(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    from forensic_deepdive.cli.style import render_trace
    from forensic_deepdive.mcp_server.server import trace as trace_query

    positional, flags = _flags(rest)
    if not positional:
        out.print("[warn]trace needs a symbol, e.g. `trace format_message`[/warn]")
        return
    if not _needs_graph(out, session):
        return
    with session.released():
        payload = trace_query(
            session.db_path,
            positional[0],
            direction="upstream" if flags.get("upstream") else "downstream",
            max_depth=_int_flag(flags, "depth", 6),
        )
    payload.setdefault("symbol", positional[0])
    render_trace(out, payload, plain=False)


def _cmd_impact(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    from forensic_deepdive.mcp_server.server import impact

    _symbol_tool(out, session, rest, "impact", impact)


def _cmd_flow(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    from forensic_deepdive.mcp_server.server import flow

    _symbol_tool(out, session, rest, "flow", flow)


def _symbol_tool(out: Console, session: StoreSession, rest: str, name: str, func: Any) -> None:
    positional, _ = _flags(rest)
    if not positional:
        out.print(f"[warn]{name} needs a symbol, e.g. `{name} format_message`[/warn]")
        return
    if not _needs_graph(out, session):
        return
    with session.released():
        payload = func(session.db_path, positional[0])
    _print_json(out, payload)


def _cmd_diagram(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    from forensic_deepdive.emit.architecture_md import ARCHITECTURE_FILENAME, architecture_for_db

    if not _needs_graph(out, session):
        return
    dest = repo / "docs" / "codebase" / ARCHITECTURE_FILENAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.released():
        dest.write_text(architecture_for_db(session.db_path, repo.name), encoding="utf-8")
    written = Text("ARCHITECTURE.md", style="ok").append(f" written to {dest}", style="muted")
    out.print(written, soft_wrap=True)


def _cmd_browse(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    """Dispatch the Textual App blocking — never nested inside the prompt loop.

    ``prompt()`` has already returned, so prompt_toolkit owns no terminal state
    here; the App takes the screen and gives it back on quit (DEC-100).
    """
    from forensic_deepdive.cli.interactive.browser import DEFAULT_NODE_CAP, run_browse

    if not _needs_graph(out, session):
        return
    _, flags = _flags(rest)
    with session.released():  # the browser's snapshot needs the lock
        run_browse(session.db_path, max_nodes=_int_flag(flags, "max-nodes", DEFAULT_NODE_CAP))


def _cmd_onboard(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    from forensic_deepdive.cli.interactive.onboard import run_onboard

    _, flags = _flags(rest)
    with session.released():  # the wizard may run extract
        run_onboard(repo, yes=bool(flags.get("yes")), force=bool(flags.get("force")), console=out)


def _cmd_serve(out: Console, session: StoreSession, repo: Path, rest: str) -> None:
    """The stdio MCP server. It speaks JSON-RPC on this terminal's stdin, so the
    shell is unusable until it stops — say so before taking the terminal."""
    import asyncio

    from forensic_deepdive.mcp_server import serve_stdio

    if not _needs_graph(out, session):
        return
    out.print(
        Text("stdio MCP server", style="brand").append(
            " — this terminal now speaks JSON-RPC; Ctrl-C returns to the shell.", style="muted"
        )
    )
    with session.released():
        try:
            asyncio.run(serve_stdio(session.db_path))
        except KeyboardInterrupt:
            out.print(Text("\nserver stopped.", style="muted"))


_HANDLERS: dict[str, Any] = {
    "extract": _cmd_extract,
    "trace": _cmd_trace,
    "impact": _cmd_impact,
    "flow": _cmd_flow,
    "diagram": _cmd_diagram,
    "browse": _cmd_browse,
    "onboard": _cmd_onboard,
    "serve": _cmd_serve,
}


# ---------------------------------------------------------------------------
# Repo resolution + the `deepdive` console-script entry
# ---------------------------------------------------------------------------


def resolve_repo(repo: Path | None, console: Console, ask: Any | None = None) -> Path | None:
    """Pick the repo: an explicit ``--repo``, the cwd if it has a graph, else a
    numbered picker over the registry's live graphs. ``None`` = the user quit."""
    if repo is not None:
        return Path(repo).resolve()
    cwd = Path.cwd().resolve()
    if cwd.joinpath(*GRAPH_SUBPATH).exists():
        return cwd

    from forensic_deepdive.registry import load

    live = [
        entry
        for entry in sorted(load().repos, key=lambda r: r.name)
        if entry.graph_db_path and Path(entry.graph_db_path).exists()
    ]
    if not live or ask is None:
        return cwd  # nothing to pick from: open here, `extract` will build it
    console.print(Text("analyzed repos:", style="brand"))
    for number, entry in enumerate(live, start=1):
        console.print(
            Text(f"  {number}. ", style="muted").append(entry.name, style="value"),
            soft_wrap=True,
        )
    answer = ask(f"pick 1-{len(live)} (blank = here, {cwd.name}): ").strip()
    if not answer:
        return cwd
    if answer.isdigit() and 1 <= int(answer) <= len(live):
        return Path(live[int(answer) - 1].repo_path).resolve()
    console.print(Text(f"no such choice {answer!r} — staying in {cwd}", style="warn"))
    return cwd


def main() -> None:  # pragma: no cover — the console-script wrapper
    """The ``deepdive`` entry point (``[project.scripts]``)."""
    import typer

    typer.run(_entry)


def _entry(
    repo: Path | None = None,
    graph: Path | None = None,
    semantic: bool = False,
    plain: bool = False,
) -> None:  # pragma: no cover — argument plumbing for the console script
    """Open a deepdive session shell on a repo (default: cwd, or pick one)."""
    import sys

    import typer

    from forensic_deepdive.cli.style import set_plain

    set_plain(plain)
    out = get_console()
    if not sys.stdin.isatty():
        out.print(
            "[err]deepdive needs a TTY[/err] (stdin is piped/redirected). "
            "For scripted use, run `forensic` subcommands directly."
        )
        raise typer.Exit(code=1)
    resolved = resolve_repo(repo, out, ask=input)
    if resolved is None:
        raise typer.Exit(code=0)
    raise typer.Exit(code=run_shell(resolved, graph=graph, semantic=semantic))
