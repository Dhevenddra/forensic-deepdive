"""Tests for the editor/agent shim writer."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.emit.shims import write_shims


def test_write_shims_creates_all_four(tmp_path: Path) -> None:
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert len(result.written) == 4
    assert not result.skipped
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".cursor" / "rules" / "codebase.mdc").is_file()
    assert (tmp_path / ".continue" / "rules" / "codebase.md").is_file()
    assert "docs/codebase/AGENT_BRIEF.md" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")


def test_write_shims_never_overwrites(tmp_path: Path) -> None:
    own = tmp_path / "CLAUDE.md"
    own.write_text("MY OWN INSTRUCTIONS\n", encoding="utf-8")
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert own in result.skipped
    assert own.read_text(encoding="utf-8") == "MY OWN INSTRUCTIONS\n"
    assert len(result.written) == 3


def test_cursor_shim_has_frontmatter(tmp_path: Path) -> None:
    write_shims(tmp_path, "x/AGENT_BRIEF.md")
    content = (tmp_path / ".cursor" / "rules" / "codebase.mdc").read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "alwaysApply: true" in content
