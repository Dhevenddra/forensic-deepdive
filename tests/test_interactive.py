"""Interactive CLI layer tests (v0.9 Track A — DEC-099 REPL).

The REPL is exercised through prompt_toolkit's testing utilities (pipe input +
DummyOutput) with a Rich capture console, per the PRD's interactive-testing
mandate: NL routes through query/nl.py, Cypher returns rows, the store opens
once per session (not per query), ``--plain`` degrades to ASCII chips, exits
are clean, and the module imports without the [interactive] extra.
"""

from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from forensic_deepdive.cli.app import app
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import EmitPhase, ExtractConfig, PipelineRunner, default_phases

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def graph_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """python_sample with a built graph — one build for the whole module."""
    base = tmp_path_factory.mktemp("repl_repo")
    repo = base / "python_sample"
    shutil.copytree(FIXTURES / "python_sample", repo)
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=base / "graph.lbug",
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    assert ctx.get(EmitPhase).artifacts
    return base


def _capture_console() -> tuple[Console, io.StringIO]:
    sio = io.StringIO()
    return Console(file=sio, force_terminal=False, no_color=True, width=200), sio


def _run_script(graph_repo: Path, tmp_path: Path, text: str, **kwargs) -> tuple[int, str]:
    """Drive run_repl with scripted pipe input; return (exit_code, output)."""
    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from forensic_deepdive.cli.interactive.repl import run_repl

    console, sio = _capture_console()
    with create_pipe_input() as inp:
        inp.send_text(text)
        inp.close()  # EOF after the script → clean Ctrl-D exit path
        code = run_repl(
            graph_repo / "graph.lbug",
            console=console,
            history_file=tmp_path / "history",
            pt_input=inp,
            pt_output=DummyOutput(),
            **kwargs,
        )
    return code, sio.getvalue()


# ---------------------------------------------------------------------------
# import-safety without the extra
# ---------------------------------------------------------------------------


def test_interactive_module_imports_without_prompt_toolkit():
    """The module itself must import with the extra absent — only invocation
    needs prompt_toolkit (lazy import inside run_repl)."""
    import forensic_deepdive.cli.interactive.repl as repl_mod

    assert hasattr(repl_mod, "run_repl")


def test_run_repl_missing_extra_prints_actionable_hint(monkeypatch, tmp_path, graph_repo):
    monkeypatch.setitem(sys.modules, "prompt_toolkit", None)  # force ImportError
    from forensic_deepdive.cli.interactive.repl import run_repl

    console, sio = _capture_console()
    code = run_repl(graph_repo / "graph.lbug", console=console, history_file=tmp_path / "h")
    assert code == 1
    assert "forensic-deepdive[interactive]" in sio.getvalue()


def test_cli_repl_missing_extra_exits_nonzero(monkeypatch, graph_repo):
    monkeypatch.setattr("forensic_deepdive.cli.interactive.interactive_available", lambda: False)
    result = CliRunner().invoke(
        app, ["repl", "--repo", str(graph_repo), "--graph", str(graph_repo / "graph.lbug")]
    )
    assert result.exit_code == 1
    assert "forensic-deepdive[interactive]" in result.output


# ---------------------------------------------------------------------------
# the REPL loop (scripted prompt_toolkit input)
# ---------------------------------------------------------------------------


def test_repl_nl_query_routes_through_query_nl(graph_repo, tmp_path):
    """A bare-text line runs the DEC-084 hybrid NL query and prints
    confidence-tagged hits from the held-open store."""
    code, out = _run_script(graph_repo, tmp_path, "greet\n:quit\n")
    assert code == 0
    assert "greeter.py" in out  # a real hit with its file
    assert "[E]" in out or "[I]" in out  # confidence chips (ASCII on non-TTY)
    assert "semantic tier not installed" in out  # honest degraded note (DEC-084)


def test_repl_cypher_prefix_returns_rows(graph_repo, tmp_path):
    code, out = _run_script(
        graph_repo, tmp_path, ":cypher MATCH (s:Symbol) RETURN s.qualified_name LIMIT 2\n:quit\n"
    )
    assert code == 0
    assert "row(s)" in out
    assert "::" in out  # qualified names came back


def test_repl_store_opened_once_across_queries(graph_repo, tmp_path, monkeypatch):
    """The persistent-open-store lifecycle (research §3): two NL queries + a
    Cypher query in one session must connect exactly once."""
    connects: list[int] = []
    orig = LadybugStore.connect

    def counting(self):  # noqa: ANN001
        connects.append(1)
        return orig(self)

    monkeypatch.setattr(LadybugStore, "connect", counting)
    code, _ = _run_script(
        graph_repo,
        tmp_path,
        "greet\nformat message\n:cypher MATCH (s:Symbol) RETURN count(s)\n:quit\n",
    )
    assert code == 0
    assert len(connects) == 1


def test_repl_plain_output_is_cp1252_safe(graph_repo, tmp_path):
    """DEC-078/080 parity: on a non-TTY console the chips are ASCII ``[E]/[I]``
    and the whole session output survives a cp1252 pipe."""
    _, out = _run_script(graph_repo, tmp_path, "greet\n:quit\n")
    assert "●" not in out and "◐" not in out
    out.encode("cp1252")  # must not raise


def test_repl_eof_exits_cleanly_and_closes_store(graph_repo, tmp_path, monkeypatch):
    closes: list[int] = []
    orig = LadybugStore.close

    def counting(self):  # noqa: ANN001
        closes.append(1)
        return orig(self)

    monkeypatch.setattr(LadybugStore, "close", counting)
    code, _ = _run_script(graph_repo, tmp_path, "greet\n")  # no :quit — EOF ends it
    assert code == 0
    assert len(closes) >= 1  # the finally ran


def test_repl_unknown_meta_command_is_friendly(graph_repo, tmp_path):
    code, out = _run_script(graph_repo, tmp_path, ":bogus\n:quit\n")
    assert code == 0
    assert "unknown command" in out and ":help" in out


def test_repl_help_lists_the_grammar(graph_repo, tmp_path):
    code, out = _run_script(graph_repo, tmp_path, ":help\n:quit\n")
    assert code == 0
    assert ":cypher" in out and "natural-language" in out


# ---------------------------------------------------------------------------
# CLI command guards
# ---------------------------------------------------------------------------


def test_cli_repl_registered_with_repo_and_graph_options():
    """Introspect the Click command (DEC-096 lesson: never substring-match
    rendered help)."""
    from typer.main import get_command

    cmd = get_command(app)
    params = {p.name for p in cmd.commands["repl"].params}
    assert {"repo", "graph", "semantic"} <= params


def test_cli_repl_refuses_missing_graph(tmp_path):
    result = CliRunner().invoke(app, ["repl", "--repo", str(tmp_path)])
    assert result.exit_code == 1
    assert "No graph" in result.output


def test_cli_repl_refuses_non_tty(graph_repo, monkeypatch):
    """Piped/redirected stdin → graceful refusal, never a hang."""
    pytest.importorskip("prompt_toolkit")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # non-tty stand-in
    result = CliRunner().invoke(app, ["repl", "--graph", str(graph_repo / "graph.lbug")])
    assert result.exit_code == 1
    assert "TTY" in result.output
