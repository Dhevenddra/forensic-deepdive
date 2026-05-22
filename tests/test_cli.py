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
