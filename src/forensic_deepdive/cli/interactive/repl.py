"""Interactive query REPL — ``forensic repl`` (DEC-099, v0.9 Track A step 1).

A prompt_toolkit line-editing loop over **one held-open** :class:`LadybugStore`
+ lexical index, so successive questions don't pay the per-invocation open
cost. This module establishes the persistent-open-store lifecycle the session
shell (DEC-102) reuses: open on entry, share across the loop, close in a
``finally``.

Command grammar (KICKOFF §8 Q2 — prefix scheme, pgcli-style):
  bare text            → hybrid NL query (``query/nl.py``, DEC-084 — never an LLM)
  :cypher <query>      → raw Cypher against the graph (alias ``:c``)
  :help                → the command list
  :quit / :exit        → leave (so does Ctrl-D; Ctrl-C cancels the current line)

Keystones: zero-LLM (DEC-009); the frozen 9-tool contract (this surfaces the
existing query paths, adds nothing); cp1252/``--plain``/``NO_COLOR`` parity
(DEC-078/080) — confidence chips degrade to ``[E]/[I]/[A]`` off a UTF-8 colour
TTY. ``prompt_toolkit`` is imported lazily so this module imports without the
``[interactive]`` extra; invocation then fails with the actionable install hint.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.text import Text

from forensic_deepdive.cli.interactive import INSTALL_HINT
from forensic_deepdive.cli.style import get_console
from forensic_deepdive.cli.style.console import confidence_label
from forensic_deepdive.cli.style.render import _glyphs_ok
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.query.lexical import lexical_index_path_for_db
from forensic_deepdive.query.nl import hybrid_query_on_store

if TYPE_CHECKING:
    from rich.console import Console

# Session history lives beside the multi-repo registry (DEC-018 convention).
DEFAULT_HISTORY_FILE = Path.home() / ".deepdive" / "repl_history"

# Tab-completion pool: meta-commands + a bounded set of symbol leaf names.
_META_COMMANDS = (":help", ":cypher", ":quit", ":exit")
_COMPLETION_SYMBOL_CAP = 2000
# Cypher rows shown per query before the honest truncation note.
_CYPHER_ROW_CAP = 50

_HELP_TEXT = """\
Commands:
  <text>            natural-language query over the graph (lexical + structural
                    retrieval — no LLM; add the [semantic] extra for embeddings)
  :cypher <query>   raw Cypher against the LadybugDB graph (alias :c)
  :help             this list
  :quit / :exit     leave (Ctrl-D also exits; Ctrl-C cancels the current line)
"""


def run_repl(
    db_path: Path,
    *,
    semantic: bool = False,
    console: Console | None = None,
    history_file: Path | None = None,
    pt_input: Any | None = None,
    pt_output: Any | None = None,
) -> int:
    """Run the REPL loop against the graph at *db_path*. Returns an exit code.

    *console* / *history_file* / *pt_input* / *pt_output* exist for the test
    harness (prompt_toolkit pipe input + a capture console) and for the session
    shell; the CLI passes none of them.
    """
    try:
        from prompt_toolkit import PromptSession  # noqa: PLC0415 — [interactive] extra
        from prompt_toolkit.completion import WordCompleter  # noqa: PLC0415
        from prompt_toolkit.history import FileHistory  # noqa: PLC0415
    except ImportError:
        (console or get_console()).print(INSTALL_HINT, markup=False, highlight=False)
        return 1

    out = console or get_console()
    hist_path = history_file or DEFAULT_HISTORY_FILE
    hist_path.parent.mkdir(parents=True, exist_ok=True)

    store = LadybugStore(db_path)
    store.connect()
    try:
        index_path = lexical_index_path_for_db(db_path)
        session: PromptSession[str] = PromptSession(
            history=FileHistory(str(hist_path)),
            completer=WordCompleter([*_META_COMMANDS, *_completion_names(store)], ignore_case=True),
            input=pt_input,
            output=pt_output,
        )
        out.print(
            Text("deepdive repl", style="brand").append(
                f" — {db_path}  (:help for commands, Ctrl-D to exit)", style="muted"
            )
        )
        while True:
            try:
                line = session.prompt("deepdive> ").strip()
            except KeyboardInterrupt:
                continue  # cancel the current line, keep the session
            except EOFError:
                break
            if not line:
                continue
            if line in (":quit", ":exit", ":q"):
                break
            if line == ":help":
                out.print(_HELP_TEXT, markup=False, highlight=False)
                continue
            if line.startswith((":cypher ", ":c ")):
                _run_cypher(out, store, line.split(" ", 1)[1].strip())
                continue
            if line.startswith(":"):
                out.print(f"[warn]unknown command {line.split()[0]!r} — :help lists them.[/warn]")
                continue
            _run_nl(out, store, index_path, line, semantic=semantic)
    finally:
        store.close()
    return 0


# ---------------------------------------------------------------------------
# Dispatch targets
# ---------------------------------------------------------------------------


def _run_cypher(out: Console, store: LadybugStore, cypher: str) -> None:
    """Raw Cypher over the open store; bounded, honest row rendering."""
    if not cypher:
        out.print("[warn]:cypher needs a query, e.g. :cypher MATCH (s:Symbol) RETURN s[/warn]")
        return
    try:
        rows = list(store.query(cypher))
    except Exception as exc:  # LadybugDB raises backend-specific types
        out.print(f"[err]cypher error:[/err] {exc}")
        return
    for row in rows[:_CYPHER_ROW_CAP]:
        out.print(Text("  " + " | ".join(str(v) for v in row), style="value"))
    shown = min(len(rows), _CYPHER_ROW_CAP)
    tail = f"showing {shown} of {len(rows)}" if len(rows) > _CYPHER_ROW_CAP else f"{len(rows)}"
    out.print(Text(f"{tail} row(s)", style="muted"))


def _run_nl(
    out: Console, store: LadybugStore, index_path: Path, query: str, *, semantic: bool
) -> None:
    """Hybrid NL query (DEC-084) over the open store; confidence-styled hits."""
    payload = hybrid_query_on_store(store, index_path, query, semantic=semantic)
    results = payload.get("results", [])
    if not results:
        out.print(Text(f"no hits for {query!r}", style="warn"))
        return
    glyphs = _glyphs_ok(out)
    for hit in results:
        line = confidence_label(hit["confidence"], compact=True, glyphs=glyphs)
        line.append(f" {hit['qualified_name']}", style="value")
        line.append(f"  {hit['file']}:{hit['line']}", style="muted")
        line.append(f"  ({hit['kind']})", style="muted")
        out.print(line)
    if payload.get("degraded"):
        out.print(Text(payload.get("note", ""), style="muted"))


# ---------------------------------------------------------------------------
# Completion pool
# ---------------------------------------------------------------------------


def _completion_names(store: LadybugStore) -> list[str]:
    """A bounded, deterministic pool of symbol leaf names for tab-completion."""
    try:
        rows = store.query(
            "MATCH (s:Symbol) RETURN s.qualified_name ORDER BY s.qualified_name "
            f"LIMIT {_COMPLETION_SYMBOL_CAP}"
        )
    except Exception:  # pragma: no cover — completion is best-effort
        return []
    seen: set[str] = set()
    names: list[str] = []
    for (qn,) in rows:
        leaf = qn.split("::")[-1].split(".")[-1]
        if leaf and not leaf.startswith("<") and leaf not in seen:
            seen.add(leaf)
            names.append(leaf)
    return names
