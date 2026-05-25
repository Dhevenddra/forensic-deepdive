"""Tests for the editor/agent shim writer (DEC-031).

The shim writer drops 10 targets into a target repo:
- 4 editor shims (CLAUDE.md, AGENTS.md, .cursor/rules/codebase.mdc,
  .continue/rules/codebase.md)
- 5 emitted skills (.claude/skills/codebase-{exploring,debugging,
  impact-analysis,refactoring,onboarding}/SKILL.md)
- 1 Claude Code plugin manifest (.claude-plugin/plugin.json)

All are write-if-absent — hand-edited files / skills are never overwritten.
"""

from __future__ import annotations

import json
from pathlib import Path

from forensic_deepdive.emit.shims import write_shims

# All 10 expected target relative paths.
_EDITOR_SHIMS = (
    "CLAUDE.md",
    "AGENTS.md",
    ".cursor/rules/codebase.mdc",
    ".continue/rules/codebase.md",
)
_SKILL_NAMES = (
    "codebase-exploring",
    "codebase-debugging",
    "codebase-impact-analysis",
    "codebase-refactoring",
    "codebase-onboarding",
)
_SKILL_PATHS = tuple(f".claude/skills/{n}/SKILL.md" for n in _SKILL_NAMES)
_PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
_ALL_TARGETS = _EDITOR_SHIMS + _SKILL_PATHS + (_PLUGIN_MANIFEST,)


def test_write_shims_creates_all_ten(tmp_path: Path) -> None:
    """A fresh repo gets every editor shim, every skill, and the plugin manifest."""
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert len(result.written) == 10
    assert not result.skipped
    for rel in _ALL_TARGETS:
        assert (tmp_path / rel).is_file(), f"missing target: {rel}"
    # Brief path appears in every editor shim.
    for rel in _EDITOR_SHIMS:
        assert "docs/codebase/AGENT_BRIEF.md" in (tmp_path / rel).read_text(encoding="utf-8")


def test_write_shims_never_overwrites_editor_shim(tmp_path: Path) -> None:
    """Hand-edited CLAUDE.md is preserved; the other 9 targets still written."""
    own = tmp_path / "CLAUDE.md"
    own.write_text("MY OWN INSTRUCTIONS\n", encoding="utf-8")
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert own in result.skipped
    assert own.read_text(encoding="utf-8") == "MY OWN INSTRUCTIONS\n"
    assert len(result.written) == 9


def test_write_shims_never_overwrites_skill(tmp_path: Path) -> None:
    """Hand-edited skill body is preserved; other skills + manifest still written."""
    own = tmp_path / ".claude" / "skills" / "codebase-debugging" / "SKILL.md"
    own.parent.mkdir(parents=True)
    own.write_text("MY OWN SKILL\n", encoding="utf-8")
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert own in result.skipped
    assert own.read_text(encoding="utf-8") == "MY OWN SKILL\n"
    # The other 4 skills should still be written.
    for name in _SKILL_NAMES:
        if name == "codebase-debugging":
            continue
        assert (tmp_path / ".claude" / "skills" / name / "SKILL.md").is_file()


def test_write_shims_never_overwrites_plugin_manifest(tmp_path: Path) -> None:
    own = tmp_path / ".claude-plugin" / "plugin.json"
    own.parent.mkdir(parents=True)
    own.write_text('{"name": "user-edited"}\n', encoding="utf-8")
    result = write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    assert own in result.skipped
    assert own.read_text(encoding="utf-8") == '{"name": "user-edited"}\n'


def test_cursor_shim_has_frontmatter(tmp_path: Path) -> None:
    write_shims(tmp_path, "x/AGENT_BRIEF.md")
    content = (tmp_path / ".cursor" / "rules" / "codebase.mdc").read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "alwaysApply: true" in content


# ---------------------------------------------------------------------------
# Skill body invariants
# ---------------------------------------------------------------------------


def _read_skill(tmp_path: Path, name: str) -> str:
    return (tmp_path / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def _frontmatter_block(body: str) -> str:
    """Return the YAML frontmatter block (between the two ``---`` lines)."""
    assert body.startswith("---\n")
    end = body.index("\n---\n", 4)
    return body[4:end]


def _description_from_frontmatter(body: str) -> str:
    block = _frontmatter_block(body)
    for line in block.splitlines():
        if line.startswith("description:"):
            return line[len("description:") :].strip()
    raise AssertionError(f"description: missing from frontmatter\n{block}")


def test_every_skill_has_yaml_frontmatter_with_name_and_description(tmp_path: Path) -> None:
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    for name in _SKILL_NAMES:
        body = _read_skill(tmp_path, name)
        block = _frontmatter_block(body)
        assert f"name: {name}" in block, f"{name}: frontmatter missing name field"
        assert "description:" in block, f"{name}: frontmatter missing description"


def test_skill_descriptions_are_single_intent_and_bounded(tmp_path: Path) -> None:
    """DEC-002 / DEC-016 lesson: descriptions are the load-bearing selector.
    Each one must (a) name the user phrases that fire it ("Use when..."),
    (b) name what it should NOT fire on ("Do NOT use"), and (c) stay under
    a rough 200-token budget so the 5 descriptions together don't blow the
    skill-list metadata context."""
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    for name in _SKILL_NAMES:
        body = _read_skill(tmp_path, name)
        desc = _description_from_frontmatter(body)
        assert "Use when" in desc, f"{name}: description must say 'Use when'"
        assert "Do NOT use" in desc or "do NOT use" in desc, (
            f"{name}: description must say 'Do NOT use'"
        )
        # Roughly 1 token ≈ 4 chars for English text. 200 tokens ≈ 800 chars.
        # Keep a small headroom so we stay well inside the budget.
        assert len(desc) <= 900, (
            f"{name}: description {len(desc)} chars > 900 (≈225 tokens). "
            "Tighten it — DEC-016 cap is ~200 tokens."
        )


def test_skill_descriptions_are_distinct_intents(tmp_path: Path) -> None:
    """Each skill's description should mention a unique intent verb so the
    selector doesn't fire two skills on one user phrase. Spot-check anchors."""
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    intent_anchors = {
        "codebase-exploring": "walk me through",
        "codebase-debugging": "broken",
        "codebase-impact-analysis": "blast radius",
        "codebase-refactoring": "refactor",
        "codebase-onboarding": "joined",
    }
    for name, anchor in intent_anchors.items():
        desc = _description_from_frontmatter(_read_skill(tmp_path, name))
        assert anchor in desc, f"{name}: description missing anchor phrase {anchor!r}"


def test_skill_bodies_reference_agent_brief(tmp_path: Path) -> None:
    """Every skill must point readers at AGENT_BRIEF.md — the brief is the
    headline artifact (CLAUDE.md "Sacred abstractions")."""
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    for name in _SKILL_NAMES:
        body = _read_skill(tmp_path, name)
        assert "AGENT_BRIEF.md" in body, f"{name}: must mention AGENT_BRIEF.md"
        assert "docs/codebase/AGENT_BRIEF.md" in body, f"{name}: must use the configured brief path"


def test_skill_paths_respect_brief_location(tmp_path: Path) -> None:
    """The artifact directory in skill bodies should derive from brief_rel,
    not be hard-coded to ``docs/codebase``."""
    write_shims(tmp_path, "artifacts/AGENT_BRIEF.md")
    body = _read_skill(tmp_path, "codebase-exploring")
    assert "artifacts/MAP.md" in body
    assert "artifacts/AGENT_BRIEF.md" in body
    assert "docs/codebase" not in body


# ---------------------------------------------------------------------------
# Plugin manifest invariants
# ---------------------------------------------------------------------------


def test_plugin_manifest_is_valid_json(tmp_path: Path) -> None:
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    manifest = json.loads((tmp_path / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "forensic-deepdive-codebase"
    assert "version" in manifest
    assert "description" in manifest


def test_plugin_manifest_lists_all_five_skills(tmp_path: Path) -> None:
    write_shims(tmp_path, "docs/codebase/AGENT_BRIEF.md")
    manifest = json.loads((tmp_path / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    listed = {s["name"] for s in manifest["skills"]}
    assert listed == set(_SKILL_NAMES)
    # Paths in the manifest should resolve to actual files on disk.
    for entry in manifest["skills"]:
        assert (tmp_path / entry["path"]).is_file()


def test_plugin_manifest_includes_repo_name(tmp_path: Path) -> None:
    """The manifest description names the target repo so a user with
    multiple analyzed repos can tell their plugins apart."""
    repo = tmp_path / "my-cool-repo"
    repo.mkdir()
    write_shims(repo, "docs/codebase/AGENT_BRIEF.md")
    manifest = json.loads((repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "my-cool-repo" in manifest["description"]
