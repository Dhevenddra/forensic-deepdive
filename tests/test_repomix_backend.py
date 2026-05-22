"""Tests for the Repomix flatten backend (Layer 2).

Unit tests mock the subprocess so they never need the Repomix binary; a single
integration test runs the real CLI and is skipped when it is not installed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from forensic_deepdive.flatten import repomix_backend as rb
from forensic_deepdive.flatten.repomix_backend import (
    RepomixError,
    RepomixNotFoundError,
    flatten_repo,
    is_repomix_available,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "python_sample"

_REAL_SUMMARY = (
    "\U0001f4ca Pack Summary:\n"
    "  Total Files: 2 files\n"
    " Total Tokens: 529 tokens\n"
    "  Total Chars: 2,367 chars\n"
)


def _fake_run(*, returncode: int = 0, summary: str = _REAL_SUMMARY, write: bool = True):
    """Build a fake ``subprocess.run`` that writes the output file Repomix would."""

    def run(command, **_kwargs):
        if write and returncode == 0:
            out = Path(command[command.index("--output") + 1])
            out.write_text("# packed repo\n\ncontent here\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, summary, "")

    return run


# --- discovery -------------------------------------------------------------


def test_is_repomix_available_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    assert is_repomix_available() is True


def test_is_repomix_available_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: None)
    assert is_repomix_available() is False


# --- argument / environment guards -----------------------------------------


def test_invalid_style_raises() -> None:
    with pytest.raises(RepomixError, match="Unsupported style"):
        flatten_repo(SAMPLE_REPO, Path("out.md"), style="yaml")


def test_missing_repo_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(RepomixError, match="not a directory"):
        flatten_repo(tmp_path / "does_not_exist", tmp_path / "out.md")


def test_not_installed_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: None)
    with pytest.raises(RepomixNotFoundError, match="npm install -g repomix"):
        flatten_repo(SAMPLE_REPO, tmp_path / "out.md")


# --- mocked runs -----------------------------------------------------------


def test_builds_command_and_parses_stats(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    monkeypatch.setattr(rb.subprocess, "run", _fake_run())

    out = tmp_path / "nested" / "out.md"
    result = flatten_repo(SAMPLE_REPO, out, style="markdown")

    assert result.output_path == out
    assert out.is_file()  # parent dir was created
    assert result.style == "markdown"
    assert result.char_count > 0
    assert result.file_count == 2
    assert result.token_count == 529
    assert "--style" in result.command
    assert result.command[result.command.index("--style") + 1] == "markdown"
    assert "--compress" not in result.command


def test_optional_flags_are_passed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    monkeypatch.setattr(rb.subprocess, "run", _fake_run())

    result = flatten_repo(
        SAMPLE_REPO,
        tmp_path / "out.md",
        compress=True,
        remove_comments=True,
        security_check=False,
        include="src/**",
        ignore="*.test.py",
    )
    cmd = result.command
    assert "--compress" in cmd
    assert "--remove-comments" in cmd
    assert "--no-security-check" in cmd
    assert cmd[cmd.index("--include") + 1] == "src/**"
    assert cmd[cmd.index("--ignore") + 1] == "*.test.py"


def test_nonzero_exit_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    monkeypatch.setattr(rb.subprocess, "run", _fake_run(returncode=1, summary="boom", write=False))
    with pytest.raises(RepomixError, match="exited with code 1"):
        flatten_repo(SAMPLE_REPO, tmp_path / "out.md")


def test_missing_output_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    monkeypatch.setattr(rb.subprocess, "run", _fake_run(write=False))
    with pytest.raises(RepomixError, match="wrote no output"):
        flatten_repo(SAMPLE_REPO, tmp_path / "out.md")


def test_timeout_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 1.0)

    monkeypatch.setattr(rb.shutil, "which", lambda _name: "/fake/bin/repomix")
    monkeypatch.setattr(rb.subprocess, "run", boom)
    with pytest.raises(RepomixError, match="timed out"):
        flatten_repo(SAMPLE_REPO, tmp_path / "out.md", timeout=1.0)


# --- summary parser --------------------------------------------------------


def test_parse_count() -> None:
    assert rb._parse_count("Total Files: 2 files", "Total Files") == 2
    assert rb._parse_count("Total Tokens: 1,234 tokens", "Total Tokens") == 1234
    assert rb._parse_count("nothing here", "Total Files") is None


# --- integration (real binary) ---------------------------------------------


@pytest.mark.skipif(not is_repomix_available(), reason="repomix CLI not installed")
def test_flatten_repo_integration(tmp_path: Path) -> None:
    out = tmp_path / "packed.md"
    result = flatten_repo(SAMPLE_REPO, out, style="markdown")

    assert out.is_file()
    assert result.char_count > 0
    assert result.style == "markdown"
    # python_sample holds exactly greeter.py and app.py
    assert result.file_count == 2
    assert result.token_count is not None and result.token_count > 0
