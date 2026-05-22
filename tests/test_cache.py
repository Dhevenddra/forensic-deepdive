"""Tests for the run cache."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.cache import (
    file_sha256,
    read_last_run,
    repo_fingerprint,
    write_last_run,
)


def test_file_sha256_is_content_addressed(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    first.write_text("hello", encoding="utf-8")
    second = tmp_path / "b.txt"
    second.write_text("hello", encoding="utf-8")
    digest = file_sha256(first)
    assert len(digest) == 64
    assert file_sha256(second) == digest


def test_repo_fingerprint_is_order_independent(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("print(1)\n", encoding="utf-8")
    b = tmp_path / "b.py"
    b.write_text("print(2)\n", encoding="utf-8")
    assert repo_fingerprint([("a.py", a), ("b.py", b)]) == repo_fingerprint(
        [("b.py", b), ("a.py", a)]
    )


def test_repo_fingerprint_changes_with_content(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("print(1)\n", encoding="utf-8")
    before = repo_fingerprint([("a.py", a)])
    a.write_text("print(999)\n", encoding="utf-8")
    assert repo_fingerprint([("a.py", a)]) != before


def test_write_then_read_last_run(tmp_path: Path) -> None:
    written = write_last_run(
        tmp_path, "fp123", "2026-05-23T00:00:00+00:00", ["MAP.md", "AGENT_BRIEF.md"]
    )
    assert written.is_file()
    loaded = read_last_run(tmp_path)
    assert loaded is not None
    assert loaded.fingerprint == "fp123"
    assert loaded.artifacts == ["AGENT_BRIEF.md", "MAP.md"]  # stored sorted


def test_read_last_run_missing_returns_none(tmp_path: Path) -> None:
    assert read_last_run(tmp_path) is None
