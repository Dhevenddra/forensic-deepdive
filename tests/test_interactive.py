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


# ---------------------------------------------------------------------------
# DEC-100 — the Textual TUI graph browser (`forensic browse`)
# ---------------------------------------------------------------------------


def test_browser_module_imports_without_textual(monkeypatch):
    """browser.py (entry + snapshot loader) must import with the extra absent;
    only browser_app.py needs textual."""
    monkeypatch.setitem(sys.modules, "textual", None)
    import importlib

    import forensic_deepdive.cli.interactive.browser as browser_mod

    importlib.reload(browser_mod)
    assert hasattr(browser_mod, "run_browse")


def test_run_browse_missing_extra_prints_actionable_hint(monkeypatch, graph_repo, capsys):
    monkeypatch.setitem(sys.modules, "textual", None)  # force ImportError
    from forensic_deepdive.cli.interactive.browser import run_browse

    code = run_browse(graph_repo / "graph.lbug")
    assert code == 1
    assert "forensic-deepdive[interactive]" in capsys.readouterr().out


def test_load_snapshot_bounds_with_visible_truncation(graph_repo):
    """DEC-039 node-cap carried over: the snapshot is bounded, never
    silent-dropped — totals keep the full graph count."""
    from forensic_deepdive.cli.interactive.browser import load_snapshot

    snap = load_snapshot(graph_repo / "graph.lbug", max_nodes=2)
    assert len(snap.symbols) == 2
    assert snap.totals["symbol"] > 2
    assert snap.truncated("symbol")
    assert "python" in snap.languages


def test_load_snapshot_full_fixture_has_all_three_kinds(graph_repo):
    from forensic_deepdive.cli.interactive.browser import load_snapshot

    snap = load_snapshot(graph_repo / "graph.lbug")
    assert snap.totals["symbol"] == len(snap.symbols) > 0
    assert snap.totals["file"] == len(snap.files) > 0
    assert not snap.truncated("symbol")
    names = {node.name for node in snap.symbols}
    assert "format_message" in names  # a real fixture symbol
    # DEC-104 consistency: module-scope symbols display dotted, never <module>.
    assert not any("<module>" in node.name for node in snap.symbols)


def _browser_app(graph_repo, max_nodes: int = 500):
    pytest.importorskip("textual")
    from forensic_deepdive.cli.interactive.browser import load_snapshot
    from forensic_deepdive.cli.interactive.browser_app import GraphBrowser

    return GraphBrowser(load_snapshot(graph_repo / "graph.lbug", max_nodes=max_nodes))


async def _settle(pilot, predicate, tries: int = 50) -> bool:
    """Pause the Textual pilot until *predicate* holds. A single ``pause()``
    is not guaranteed to flush a posted message round-trip (Input.Changed →
    handler), so poll a bounded number of pauses — deterministic completion,
    fails only when the behaviour is genuinely absent."""
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause()
    return predicate()


def test_browser_app_boots_and_lists_symbols(graph_repo):
    import asyncio

    async def scenario():
        app = _browser_app(graph_repo)
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import DataTable, Static

            table = app.query_one(DataTable)
            assert table.row_count == len(app.snapshot.symbols) > 0
            status = str(app.query_one("#status", Static).content)
            assert "Symbols: showing" in status

    asyncio.run(scenario())


def test_browser_filter_narrows_the_list(graph_repo):
    import asyncio

    async def scenario():
        app = _browser_app(graph_repo)
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Input

            before = len(app.visible_nodes)
            app.query_one(Input).value = "format_message"
            assert await _settle(pilot, lambda: len(app.visible_nodes) < before)
            assert len(app.visible_nodes) > 0
            assert all("format_message" in n.name for n in app.visible_nodes)

    asyncio.run(scenario())


def test_browser_selection_renders_context_detail(graph_repo):
    import asyncio

    async def scenario():
        app = _browser_app(graph_repo)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")  # select the focused first row
            from textual.widgets import Static

            def _has_context() -> bool:
                return '"context"' in str(app.query_one("#detail", Static).content)

            assert await _settle(pilot, _has_context)  # the MCP context payload landed

    asyncio.run(scenario())


def test_browser_truncation_note_on_oversized_graph(graph_repo):
    import asyncio

    async def scenario():
        app = _browser_app(graph_repo, max_nodes=2)
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Static

            status = str(app.query_one("#status", Static).content)
            assert "showing 2 of" in status
            assert "loaded top 2" in status  # never silent-drop

    asyncio.run(scenario())


def test_browser_confidence_chips_are_ascii(graph_repo):
    """DEC-078/080 discipline inside the TUI: letter chips, no glyphs."""
    from forensic_deepdive.cli.interactive.browser import load_snapshot

    pytest.importorskip("textual")
    from forensic_deepdive.cli.interactive.browser_app import _chips

    snap = load_snapshot(graph_repo / "graph.lbug")
    for node in snap.symbols:
        chips = _chips(node.confidences)
        chips.encode("ascii")  # must not raise
        assert "●" not in chips and "◐" not in chips


def test_cli_browse_registered_with_expected_options():
    from typer.main import get_command

    cmd = get_command(app)
    params = {p.name for p in cmd.commands["browse"].params}
    assert {"repo", "graph", "max_nodes"} <= params


def test_cli_browse_refuses_missing_graph(tmp_path):
    result = CliRunner().invoke(app, ["browse", "--repo", str(tmp_path)])
    assert result.exit_code == 1
    assert "No graph" in result.output


# ---------------------------------------------------------------------------
# DEC-101 — the `forensic onboard` wizard
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_repo(tmp_path: Path) -> Path:
    """An unanalyzed copy of python_sample — onboard writes artifacts + shims
    into it, so every test that runs the wizard needs its own."""
    repo = tmp_path / "python_sample"
    shutil.copytree(FIXTURES / "python_sample", repo)
    return repo


def _run_onboard(repo: Path, tmp_path: Path, script: str | None = None, **kwargs):
    """Drive run_onboard; with *script* the prompts read from a pipe. Returns
    (exit_code, output)."""
    from forensic_deepdive.cli.interactive.onboard import run_onboard

    console, sio = _capture_console()
    if script is None:
        code = run_onboard(repo, console=console, **kwargs)
        return code, sio.getvalue()

    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    with create_pipe_input() as inp:
        inp.send_text(script)
        inp.close()
        code = run_onboard(
            repo,
            console=console,
            history_file=tmp_path / "onboard_history",
            pt_input=inp,
            pt_output=DummyOutput(),
            **kwargs,
        )
    return code, sio.getvalue()


def test_onboard_yes_runs_extract_and_reports_the_brief(fresh_repo, tmp_path):
    """The scripted happy path: extract runs, AGENT_BRIEF is the headline, the
    graph is reported, and the restart-and-approve step is stated."""
    code, out = _run_onboard(fresh_repo, tmp_path, yes=True)
    assert code == 0
    assert (fresh_repo / "docs" / "codebase" / "AGENT_BRIEF.md").exists()
    assert "read first:" in out and "AGENT_BRIEF.md" in out
    assert "MENTAL_MODEL.md" in out  # the other four are listed too
    assert "graph.lbug" in out
    assert "Restart the client" in out and "approve" in out


def test_onboard_prints_the_shared_mcp_config_snippet(fresh_repo, tmp_path):
    """The wizard must print exactly what the one renderer produces — never a
    second hardcoded snippet (the DEC-105 output is the source of truth)."""
    from forensic_deepdive.cli.mcp_snippet import is_source_checkout, render_mcp_config

    _, out = _run_onboard(fresh_repo, tmp_path, yes=True, client="claude")
    expected = render_mcp_config(fresh_repo, client="claude", dev=is_source_checkout())
    # Rich soft-wraps but doesn't reflow; compare the payload lines individually.
    for line in expected.splitlines():
        assert line.strip() in out


def test_onboard_snippet_matches_the_mcp_config_command(fresh_repo, tmp_path):
    """Same renderer, same bytes: `forensic mcp-config --dev` and the wizard."""
    from forensic_deepdive.cli.mcp_snippet import render_mcp_config

    result = CliRunner().invoke(app, ["mcp-config", "--repo", str(fresh_repo), "--dev"])
    assert result.exit_code == 0
    rendered = render_mcp_config(fresh_repo, client="claude", dev=True)
    assert result.output.strip() == rendered.strip()


def test_onboard_auto_picks_the_dev_form_from_a_source_checkout(fresh_repo, tmp_path):
    """Running out of this checkout, the snippet must be launchable (uv run
    --project), not the not-yet-published uvx form."""
    from forensic_deepdive.cli.mcp_snippet import is_source_checkout

    assert is_source_checkout()  # the test suite runs from the checkout
    _, out = _run_onboard(fresh_repo, tmp_path, yes=True)
    assert "source checkout" in out
    assert "--project" in out


def test_onboard_dev_flag_overrides_the_auto_pick(fresh_repo, tmp_path):
    _, out = _run_onboard(fresh_repo, tmp_path, yes=True, dev=False)
    assert "uvx" in out and "installed package" in out


def test_onboard_is_idempotent_and_keeps_existing_artifacts(fresh_repo, tmp_path):
    """Re-running is safe: with defaults taken, an already-analyzed repo is not
    re-extracted, and the wizard still emits the wiring instructions."""
    first, _ = _run_onboard(fresh_repo, tmp_path, yes=True)
    assert first == 0
    code, out = _run_onboard(fresh_repo, tmp_path, yes=True)
    assert code == 0
    assert "artifacts already exist" in out
    assert "kept the existing artifacts" in out
    assert "Restart the client" in out  # still finishes the wiring steps


def test_onboard_declining_the_repo_never_runs_extract(fresh_repo, tmp_path, monkeypatch):
    def _boom(*args, **kwargs):  # pragma: no cover — must never be called
        raise AssertionError("extract ran after the user declined")

    monkeypatch.setattr("forensic_deepdive.pipeline.run_extract", _boom)
    code, out = _run_onboard(fresh_repo, tmp_path, script="n\n")
    assert code == 0
    assert "cancelled" in out
    assert not (fresh_repo / "docs" / "codebase").exists()


def test_onboard_prompts_for_the_client_and_renders_codex_toml(fresh_repo, tmp_path):
    """Scripted prompts: confirm repo -> decline re-analysis -> pick codex."""
    assert _run_onboard(fresh_repo, tmp_path, yes=True)[0] == 0  # pre-analyze
    code, out = _run_onboard(fresh_repo, tmp_path, script="y\nn\ncodex\n")
    assert code == 0
    assert "[mcp_servers.forensic-deepdive]" in out


def test_onboard_eof_at_a_prompt_cancels_cleanly(fresh_repo, tmp_path):
    code, out = _run_onboard(fresh_repo, tmp_path, script="")  # immediate EOF (Ctrl-D)
    assert code == 0
    assert "cancelled" in out


def test_onboard_missing_extra_hints_at_the_install_and_at_yes(monkeypatch, fresh_repo, tmp_path):
    monkeypatch.setitem(sys.modules, "prompt_toolkit", None)  # force ImportError
    code, out = _run_onboard(fresh_repo, tmp_path)
    assert code == 1
    assert "forensic-deepdive[interactive]" in out
    assert "--yes" in out


def test_onboard_yes_works_without_the_extra(monkeypatch, fresh_repo, tmp_path):
    """The scripted mode asks nothing, so it must not need prompt_toolkit —
    that keeps the agent-first lean install onboardable in CI."""
    monkeypatch.setitem(sys.modules, "prompt_toolkit", None)
    code, out = _run_onboard(fresh_repo, tmp_path, yes=True)
    assert code == 0
    assert "Restart the client" in out


def test_onboard_rejects_a_non_directory(tmp_path):
    from forensic_deepdive.cli.interactive.onboard import run_onboard

    console, sio = _capture_console()
    code = run_onboard(tmp_path / "nope", yes=True, console=console)
    assert code == 1
    assert "not a directory" in sio.getvalue()


def test_onboard_output_is_cp1252_safe(fresh_repo, tmp_path):
    _, out = _run_onboard(fresh_repo, tmp_path, yes=True)
    out.encode("cp1252")  # must not raise


def test_onboard_never_hard_wraps_a_path_or_command(fresh_repo, tmp_path):
    """Found while driving the real CLI: Rich hard-wrapped the long temp-dir
    path mid-segment, so the printed config path and `mcp-config` command could
    not be copy-pasted. Every path/command line soft-wraps instead."""
    from forensic_deepdive.cli.interactive.onboard import run_onboard

    sio = io.StringIO()
    narrow = Console(file=sio, force_terminal=False, no_color=True, width=40)
    assert run_onboard(fresh_repo, yes=True, console=narrow) == 0
    out = sio.getvalue()
    repo_str = str(fresh_repo.resolve())
    assert repo_str in out  # unbroken, despite a 40-column console
    assert f"forensic mcp-config --repo {repo_str}" in out
    for line in out.splitlines():  # nothing was chopped into a dangling fragment
        assert not line.endswith("\\")


def test_cli_onboard_registered_with_expected_options():
    from typer.main import get_command

    cmd = get_command(app)
    params = {p.name for p in cmd.commands["onboard"].params}
    assert {"repo", "yes", "force", "client", "dev"} <= params


def test_cli_onboard_rejects_an_unknown_client(fresh_repo):
    result = CliRunner().invoke(
        app, ["onboard", "--repo", str(fresh_repo), "--yes", "--client", "emacs"]
    )
    assert result.exit_code == 1
    assert "Unknown client" in result.output


def test_cli_onboard_refuses_non_tty_without_yes(fresh_repo, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # non-tty stand-in
    result = CliRunner().invoke(app, ["onboard", "--repo", str(fresh_repo)])
    assert result.exit_code == 1
    assert "TTY" in result.output and "--yes" in result.output


# ---------------------------------------------------------------------------
# DEC-102 — the `deepdive` session shell
# ---------------------------------------------------------------------------


def _run_shell(repo: Path, tmp_path: Path, script: str, **kwargs) -> tuple[int, str]:
    """Drive run_shell with a scripted command sequence."""
    pytest.importorskip("prompt_toolkit")
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from forensic_deepdive.cli.interactive.shell import run_shell

    console, sio = _capture_console()
    with create_pipe_input() as inp:
        inp.send_text(script)
        inp.close()
        code = run_shell(
            repo,
            console=console,
            history_file=tmp_path / "shell_history",
            pt_input=inp,
            pt_output=DummyOutput(),
            **kwargs,
        )
    return code, sio.getvalue()


def _shell_repo(graph_repo: Path) -> tuple[Path, Path]:
    return graph_repo / "python_sample", graph_repo / "graph.lbug"


def test_shell_module_imports_without_prompt_toolkit(monkeypatch):
    monkeypatch.setitem(sys.modules, "prompt_toolkit", None)
    import importlib

    import forensic_deepdive.cli.interactive.shell as shell_mod

    importlib.reload(shell_mod)
    assert hasattr(shell_mod, "run_shell")


def test_shell_missing_extra_prints_actionable_hint(monkeypatch, graph_repo, tmp_path):
    monkeypatch.setitem(sys.modules, "prompt_toolkit", None)  # force ImportError
    from forensic_deepdive.cli.interactive.shell import run_shell

    repo, graph = _shell_repo(graph_repo)
    console, sio = _capture_console()
    code = run_shell(repo, graph=graph, console=console, history_file=tmp_path / "h")
    assert code == 1
    assert "forensic-deepdive[interactive]" in sio.getvalue()


def test_store_session_release_frees_the_lock_and_reopens(graph_repo):
    """The load-bearing invariant, and it holds on every platform: with no handle
    held, a `db_path`-taking tool can always take one; afterwards `.store`
    lazily re-opens. (Whether a *concurrent* second handle would have raised is
    platform-dependent — see the test below.)"""
    from forensic_deepdive.cli.interactive.shell import StoreSession

    _, graph = _shell_repo(graph_repo)
    session = StoreSession(graph)
    assert session.store.query("MATCH (s:Symbol) RETURN count(s)")  # held open

    with session.released():
        second = LadybugStore(graph)
        second.connect()  # must not raise — the shell gave the handle back
        second.close()

    assert session.store.query("MATCH (s:Symbol) RETURN count(s)")  # lazily reopened
    session.close()


@pytest.mark.skipif(sys.platform != "win32", reason="the exclusive lock is Windows behaviour")
def test_second_concurrent_handle_is_rejected_on_windows(graph_repo):
    """Why `released()` exists at all. On Windows LadybugDB takes an exclusive
    file lock, so calling any db_path-taking tool while the shell holds a store
    raises `Could not set lock on file`. On Linux the same open currently
    succeeds — which is exactly why the shell must not depend on it (CI caught
    this: the assertion below passes on Windows and fails on ubuntu)."""
    from forensic_deepdive.cli.interactive.shell import StoreSession

    _, graph = _shell_repo(graph_repo)
    session = StoreSession(graph)
    assert session.store.query("MATCH (s:Symbol) RETURN count(s)")
    try:
        with pytest.raises(RuntimeError, match="lock"):
            LadybugStore(graph).connect()
    finally:
        session.close()


def test_shell_store_opened_once_across_queries(graph_repo, tmp_path, monkeypatch):
    """The DEC-099 hot path survives: repeated questions share one open store."""
    connects: list[int] = []
    orig = LadybugStore.connect
    monkeypatch.setattr(LadybugStore, "connect", lambda self: (connects.append(1), orig(self))[1])

    repo, graph = _shell_repo(graph_repo)
    code, _ = _run_shell(
        repo,
        tmp_path,
        "greet\nformat message\n:cypher MATCH (s:Symbol) RETURN count(s)\n:quit\n",
        graph=graph,
    )
    assert code == 0
    assert len(connects) == 1


def test_shell_trace_runs_between_queries_without_a_lock_error(graph_repo, tmp_path):
    """The bug this design exists to prevent: `trace` opens its own handle, so a
    naive held-open store would raise 'Could not set lock on file'. The query
    before and after it must both still work."""
    repo, graph = _shell_repo(graph_repo)
    script = "greet\ntrace format_message\ngreet\n:quit\n"
    code, out = _run_shell(repo, tmp_path, script, graph=graph)
    assert code == 0
    assert "lock" not in out.lower()
    assert "format_message" in out
    assert out.count("greeter.py") >= 2  # both NL queries ran


def test_shell_impact_and_flow_render_json(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    script = "impact format_message\nflow greet\n:quit\n"
    code, out = _run_shell(repo, tmp_path, script, graph=graph)
    assert code == 0
    assert '"symbol"' in out or '"callers"' in out
    assert "lock" not in out.lower()


def test_shell_browse_is_dispatched_with_the_lock_released(graph_repo, tmp_path, monkeypatch):
    """`browse` must be launched blocking (never nested in the prompt) AND with
    no handle held — the Textual App loads its snapshot through its own store."""
    calls: list[tuple[Path, int]] = []

    def fake_run_browse(db_path, *, max_nodes=500):
        probe = LadybugStore(db_path)
        probe.connect()  # raises if the shell still holds the lock
        probe.close()
        calls.append((db_path, max_nodes))
        return 0

    monkeypatch.setattr(
        "forensic_deepdive.cli.interactive.browser.run_browse", fake_run_browse, raising=True
    )
    repo, graph = _shell_repo(graph_repo)
    script = "greet\nbrowse --max-nodes 7\ngreet\n:quit\n"
    code, out = _run_shell(repo, tmp_path, script, graph=graph)
    assert code == 0
    assert calls == [(graph, 7)]
    assert "lock" not in out.lower()


def test_shell_serve_releases_the_lock_before_serving(graph_repo, tmp_path, monkeypatch):
    served: list[Path] = []

    async def fake_serve_stdio(db_path):
        probe = LadybugStore(db_path)
        probe.connect()  # raises if the shell still holds the lock
        probe.close()
        served.append(db_path)

    monkeypatch.setattr("forensic_deepdive.mcp_server.serve_stdio", fake_serve_stdio, raising=True)
    repo, graph = _shell_repo(graph_repo)
    code, out = _run_shell(repo, tmp_path, "greet\nserve\n:quit\n", graph=graph)
    assert code == 0
    assert served == [graph]
    assert "JSON-RPC" in out


def test_shell_extract_invalidates_and_reopens_the_store(fresh_repo, tmp_path):
    """An in-session extract rewrites the graph under us: the store is released
    first, and the next query transparently opens the NEW graph."""
    code, out = _run_shell(fresh_repo, tmp_path, "trace greet\nextract\ngreet\n:quit\n")
    assert code == 0
    assert "no graph yet" in out  # the pre-extract trace was refused, not crashed
    assert (fresh_repo / ".deepdive" / "graph.lbug").exists()
    assert "greeter.py" in out  # the post-extract NL query hit the fresh graph
    assert "lock" not in out.lower()


def test_shell_diagram_writes_architecture(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    code, out = _run_shell(repo, tmp_path, "diagram\n:quit\n", graph=graph)
    assert code == 0
    assert (repo / "docs" / "codebase" / "ARCHITECTURE.md").exists()
    assert "ARCHITECTURE.md" in out


def test_shell_onboard_dispatches_the_wizard(graph_repo, tmp_path, monkeypatch):
    seen: list[bool] = []

    def fake_onboard(repo, **kwargs):
        seen.append(kwargs.get("yes", False))
        return 0

    monkeypatch.setattr(
        "forensic_deepdive.cli.interactive.onboard.run_onboard", fake_onboard, raising=True
    )
    repo, graph = _shell_repo(graph_repo)
    code, _ = _run_shell(repo, tmp_path, "onboard --yes\n:quit\n", graph=graph)
    assert code == 0
    assert seen == [True]


def test_shell_bare_text_is_nl_and_query_takes_the_rest(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    _, bare = _run_shell(repo, tmp_path, "greet\n:quit\n", graph=graph)
    _, explicit = _run_shell(repo, tmp_path, "query greet\n:quit\n", graph=graph)
    assert "greeter.py" in bare and "greeter.py" in explicit


def test_shell_commands_need_a_symbol(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    code, out = _run_shell(repo, tmp_path, "trace\nimpact\n:quit\n", graph=graph)
    assert code == 0
    assert out.count("needs a symbol") == 2


def test_shell_without_a_graph_guides_to_extract(fresh_repo, tmp_path):
    code, out = _run_shell(fresh_repo, tmp_path, "greet\nbrowse\n:quit\n")
    assert code == 0
    assert out.count("no graph yet") >= 2


def test_shell_help_and_unknown_meta_command(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    code, out = _run_shell(repo, tmp_path, ":help\n:bogus\n:quit\n", graph=graph)
    assert code == 0
    assert "trace <symbol>" in out and ":cypher" in out
    assert "unknown command" in out


def test_shell_eof_exits_cleanly_and_closes_the_store(graph_repo, tmp_path, monkeypatch):
    closes: list[int] = []
    orig = LadybugStore.close
    monkeypatch.setattr(LadybugStore, "close", lambda self: (closes.append(1), orig(self))[1])
    repo, graph = _shell_repo(graph_repo)
    code, _ = _run_shell(repo, tmp_path, "greet\n", graph=graph)  # EOF, no :quit
    assert code == 0
    assert len(closes) >= 1


def test_shell_output_is_cp1252_safe(graph_repo, tmp_path):
    repo, graph = _shell_repo(graph_repo)
    _, out = _run_shell(repo, tmp_path, "greet\n:help\n:quit\n", graph=graph)
    out.encode("cp1252")  # must not raise


def test_deepdive_console_script_is_declared_and_importable():
    """The `deepdive` [project.scripts] entry must resolve to a real callable."""
    import tomllib

    from forensic_deepdive.cli.interactive.shell import main

    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text("utf-8"))
    target = pyproject["project"]["scripts"]["deepdive"]
    assert target == "forensic_deepdive.cli.interactive.shell:main"
    assert callable(main)


def test_terminal_errors_include_the_windows_console_failure():
    """MinTTY/Git Bash reports isatty()==True but has no Windows console screen
    buffer, so prompt_toolkit raises on construction. The tuple must catch it."""
    from forensic_deepdive.cli.interactive import terminal_errors

    errors = terminal_errors()
    assert io.UnsupportedOperation in errors
    if sys.platform == "win32":
        pytest.importorskip("prompt_toolkit")
        from prompt_toolkit.output.win32 import NoConsoleScreenBufferError

        assert NoConsoleScreenBufferError in errors


@pytest.mark.parametrize("surface", ["shell", "repl"])
def test_hostile_terminal_gets_a_hint_not_a_traceback(surface, graph_repo, tmp_path, monkeypatch):
    """Found by running the real `deepdive` script under Git Bash: the TTY guard
    passed, then prompt_toolkit died with a raw traceback."""
    pytest.importorskip("prompt_toolkit")
    import prompt_toolkit

    def explode(*args, **kwargs):
        raise io.UnsupportedOperation("no console screen buffer")

    monkeypatch.setattr(prompt_toolkit, "PromptSession", explode)
    console, sio = _capture_console()
    repo, graph = _shell_repo(graph_repo)
    if surface == "shell":
        from forensic_deepdive.cli.interactive.shell import run_shell

        code = run_shell(repo, graph=graph, console=console, history_file=tmp_path / "h")
    else:
        from forensic_deepdive.cli.interactive.repl import run_repl

        code = run_repl(graph, console=console, history_file=tmp_path / "h")
    assert code == 1
    assert "winpty" in sio.getvalue()
    assert "Traceback" not in sio.getvalue()


def test_shell_resolve_repo_prefers_explicit_then_cwd(tmp_path, monkeypatch):
    from forensic_deepdive.cli.interactive.shell import resolve_repo

    console, _ = _capture_console()
    assert resolve_repo(tmp_path, console) == tmp_path.resolve()

    graphed = tmp_path / "withgraph"
    (graphed / ".deepdive").mkdir(parents=True)
    (graphed / ".deepdive" / "graph.lbug").write_text("x", encoding="utf-8")
    monkeypatch.chdir(graphed)
    assert resolve_repo(None, console) == graphed.resolve()


def test_shell_resolve_repo_picks_from_the_registry(tmp_path, monkeypatch):
    """No graph in cwd: offer the analyzed repos, and honour the pick."""
    from forensic_deepdive.cli.interactive import shell as shell_mod

    picked = tmp_path / "analyzed"
    (picked / ".deepdive").mkdir(parents=True)
    graph = picked / ".deepdive" / "graph.lbug"
    graph.write_text("x", encoding="utf-8")

    class _Entry:
        name = "analyzed"
        repo_path = str(picked)
        graph_db_path = str(graph)

    class _Reg:
        repos = (_Entry(),)

    monkeypatch.setattr("forensic_deepdive.registry.load", lambda: _Reg(), raising=True)
    empty = tmp_path / "elsewhere"
    empty.mkdir()
    monkeypatch.chdir(empty)
    console, sio = _capture_console()

    assert shell_mod.resolve_repo(None, console, ask=lambda _p: "1") == picked.resolve()
    assert "analyzed" in sio.getvalue()
    # a blank answer stays put; a bad answer warns and stays put
    assert shell_mod.resolve_repo(None, console, ask=lambda _p: "") == empty.resolve()
    assert shell_mod.resolve_repo(None, console, ask=lambda _p: "9") == empty.resolve()
    assert "no such choice" in sio.getvalue()
