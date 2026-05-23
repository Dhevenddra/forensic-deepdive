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
