"""Tests for the grep-based query module."""

from __future__ import annotations

from pathlib import Path

import pytest

from forensic_deepdive.query import (
    query_artifacts,
    resolve_artifacts_dir,
)


def _write_artifacts(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "AGENT_BRIEF.md").write_text(
        "# AGENT_BRIEF — demo\n"
        "\n"
        "## What this is\n"
        "\n"
        "A Python codebase.\n"
        "\n"
        "## Rules\n"
        "\n"
        "### Always\n"
        "\n"
        "- Always run pytest\n",
        encoding="utf-8",
    )
    (directory / "MAP.md").write_text(
        "# MAP — demo\n\n## Overview\n\n- Source files: 5\n\n## Most central files\n\n1. cli.py\n",
        encoding="utf-8",
    )


def test_query_finds_matches(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    result = query_artifacts(tmp_path, "Python")
    assert result.hits
    assert any(h.file == "AGENT_BRIEF.md" for h in result.hits)


def test_query_is_case_insensitive_by_default(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    assert query_artifacts(tmp_path, "python").hits


def test_query_case_sensitive_opt_in(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    assert query_artifacts(tmp_path, "python", case_sensitive=True).hits == []
    assert query_artifacts(tmp_path, "Python", case_sensitive=True).hits


def test_query_no_match(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    assert query_artifacts(tmp_path, "nonexistent-term").hits == []


def test_query_records_only_existing_files(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    result = query_artifacts(tmp_path, "Python")
    assert "AGENT_BRIEF.md" in result.files_searched
    assert "MAP.md" in result.files_searched
    # HOTPATHS / ARCHAEOLOGY / MENTAL_MODEL not written → not listed
    assert "HOTPATHS.md" not in result.files_searched


def test_query_context_lines(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    hits = query_artifacts(tmp_path, "Always run", context=1).hits
    assert hits
    assert len(hits[0].context_before) == 1
    # there's a trailing line after "Always run pytest" only if the file has one
    assert len(hits[0].context_after) <= 1


def test_query_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        query_artifacts(tmp_path / "no-such-dir", "foo")


def test_resolve_artifacts_dir_repo_root(tmp_path: Path) -> None:
    """Passing a repo root resolves to <repo>/docs/codebase."""
    nested = tmp_path / "docs" / "codebase"
    _write_artifacts(nested)
    assert resolve_artifacts_dir(tmp_path) == nested


def test_resolve_artifacts_dir_already_artifacts(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    assert resolve_artifacts_dir(tmp_path) == tmp_path


def test_query_via_repo_root(tmp_path: Path) -> None:
    """End-to-end: pass a repo root, query searches docs/codebase under it."""
    _write_artifacts(tmp_path / "docs" / "codebase")
    result = query_artifacts(tmp_path, "Python")
    assert result.hits
    assert result.artifacts_dir == tmp_path / "docs" / "codebase"
