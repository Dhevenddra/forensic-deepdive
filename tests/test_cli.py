"""Smoke tests for the wired-up CLI."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from forensic_deepdive.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "forensic-deepdive" in result.stdout


def test_cli_extract_end_to_end(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / "python_sample", repo)
    result = runner.invoke(app, ["extract", str(repo)])
    assert result.exit_code == 0, result.stdout
    assert (repo / "docs" / "codebase" / "AGENT_BRIEF.md").is_file()


def test_cli_extract_missing_dir_exits_nonzero() -> None:
    result = runner.invoke(app, ["extract", "nonexistent-dir-xyz-123"])
    assert result.exit_code == 1


def test_cli_mcp_config_default_is_valid_mcpservers_json(tmp_path: Path) -> None:
    """DEC-091: `forensic mcp-config` prints a copy-paste mcpServers snippet."""
    import json

    result = runner.invoke(app, ["mcp-config", "--repo", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    cfg = json.loads(result.stdout)  # pure-stdout JSON, redirectable
    server = cfg["mcpServers"]["forensic-deepdive"]
    assert server["command"] == "uvx"
    assert server["args"][:3] == ["forensic-deepdive", "serve", "--repo"]
    assert server["args"][3] == str(tmp_path.resolve())  # CWD-independent absolute path


def test_cli_mcp_config_client_variants(tmp_path: Path) -> None:
    """vscode uses the `servers` key; codex emits TOML."""
    import json

    vscode = runner.invoke(app, ["mcp-config", "--repo", str(tmp_path), "--client", "vscode"])
    assert "servers" in json.loads(vscode.stdout)
    codex = runner.invoke(app, ["mcp-config", "--repo", str(tmp_path), "--client", "codex"])
    assert "[mcp_servers.forensic-deepdive]" in codex.stdout
    assert 'command = "uvx"' in codex.stdout


def test_cli_query_finds_match(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "codebase"
    artifacts.mkdir(parents=True)
    (artifacts / "AGENT_BRIEF.md").write_text(
        "# AGENT_BRIEF — demo\n\nA Python codebase.\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["query", "Python", "--artifacts-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "1 match" in result.stdout
    assert "AGENT_BRIEF.md" in result.stdout


def test_cli_query_no_match_is_not_an_error(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "codebase"
    artifacts.mkdir(parents=True)
    (artifacts / "AGENT_BRIEF.md").write_text("# x\n", encoding="utf-8")
    result = runner.invoke(app, ["query", "missing-term", "--artifacts-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No matches" in result.stdout


def test_cli_serve_accepts_repo_option(tmp_path: Path) -> None:
    """`serve --repo <path>` must be accepted (matches trace/graph + MANUAL_TEST §7/§8
    and the MCP config). A positional-only `repo` previously broke `serve --ui --repo …`
    with 'No such option --repo'. Regression guard: reach the 'No graph' branch (exit 1),
    not a usage error (exit 2)."""
    result = runner.invoke(app, ["serve", "--repo", str(tmp_path), "--ui"])
    assert result.exit_code == 1, result.stdout
    assert "No such option" not in result.stdout
    assert "No graph" in result.stdout


def test_cli_serve_repo_option_in_help() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.stdout


def test_cli_graph_empty_degrades_honestly(tmp_path: Path, monkeypatch) -> None:
    """`graph --central` on a repo with no resolved CALLS edges used to emit a hollow
    ```mermaid flowchart LR``` block with zero nodes (useless to paste). It now degrades
    honestly with a note and no empty block (cf. ARCHITECTURE.md). v0.8 CLI-usability fix."""
    db = tmp_path / ".deepdive" / "graph.lbug"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"")  # exists, so we reach render_mermaid (which we stub)

    def _fake_render(*_a, **_k):
        return {"mermaid": "```mermaid\nflowchart LR\n```", "node_count": 0, "truncated": False}

    monkeypatch.setattr("forensic_deepdive.emit.mermaid.render_mermaid", _fake_render)
    result = runner.invoke(app, ["graph", "--repo", str(tmp_path), "--central"])
    assert result.exit_code == 0, result.stdout
    assert "No graph to draw" in result.stdout
    assert "flowchart LR" not in result.stdout  # no hollow block printed


def test_help_text_is_cp1252_safe() -> None:
    """Typer/Click prints command help text (docstrings + option-help) through a
    printer that honours the Windows console code page. A non-ASCII glyph — e.g.
    the arrow that used to be in trace's docstring — raised UnicodeEncodeError when
    `--help` was piped on cp1252. Guard the text content of every command (the
    Rich panel *borders* are dropped in the real piped/non-TTY path, so they aren't
    the concern here — the body text is)."""
    strings: list[str] = []
    main_cb = getattr(app, "registered_callback", None)
    if main_cb is not None and main_cb.callback is not None:
        strings.append(main_cb.callback.__doc__ or "")

    def _collect(typer_app) -> None:
        for cmd in typer_app.registered_commands:
            if cmd.callback is not None:
                strings.append(cmd.callback.__doc__ or "")
                ann = getattr(cmd.callback, "__annotations__", {})
                for meta in ann.values():
                    for m in getattr(meta, "__metadata__", ()):  # Annotated[...] options
                        strings.append(getattr(m, "help", "") or "")
        for group in typer_app.registered_groups:
            _collect(group.typer_instance)

    _collect(app)
    for text in strings:
        # Must encode under the Windows ANSI code page without raising.
        text.encode("cp1252")
