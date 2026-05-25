"""Tests for the five artifact emitters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.emit import (
    RepoFacts,
    render_agent_brief,
    render_all,
    render_archaeology,
    render_hotpaths,
    render_map,
    render_mental_model,
)
from forensic_deepdive.emit.common import AGENT_BRIEF_BYTE_CAP, byte_len
from forensic_deepdive.history.git_archaeology import (
    Contributor,
    FileChurn,
    GitHistory,
    GitHubStats,
)
from forensic_deepdive.static.graph import build_symbol_graph
from forensic_deepdive.static.pagerank import rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import extract_tags

FIXTURES = Path(__file__).parent / "fixtures"


def _build_facts(
    *,
    is_git: bool = True,
    github: GitHubStats | None = None,
    test_files: int = 0,
    fixture_files: int = 0,
) -> RepoFacts:
    """Build a RepoFacts from the python_sample fixture plus synthetic history."""
    tags = []
    for rel in ("greeter.py", "app.py"):
        parsed = parse_file(FIXTURES / "python_sample" / rel, rel_path=rel)
        assert parsed is not None
        tags.extend(extract_tags(parsed))
    symbol_graph = build_symbol_graph(tags)
    ranked = rank_files(symbol_graph)

    if is_git:
        history = GitHistory(
            repo_path=Path("python_sample"),
            is_git_repo=True,
            total_commits=10,
            first_commit=datetime(2020, 1, 1, tzinfo=UTC),
            last_commit=datetime(2024, 6, 1, tzinfo=UTC),
            contributors=[
                Contributor("Alice", "alice@example.com", 7),
                Contributor("Bob", "bob@example.com", 3),
            ],
            churn=[FileChurn("greeter.py", 9), FileChurn("app.py", 2)],
            github=github,
        )
    else:
        history = GitHistory(
            repo_path=Path("python_sample"),
            is_git_repo=False,
            total_commits=0,
            first_commit=None,
            last_commit=None,
            contributors=[],
            churn=[],
        )

    return RepoFacts(
        repo_path=Path("python_sample"),
        repo_name="python_sample",
        generated_at=datetime(2026, 5, 23, tzinfo=UTC),
        file_count=2,
        language_breakdown={"python": 2},
        tags=tags,
        symbol_graph=symbol_graph,
        ranked=ranked,
        history=history,
        test_file_count=test_files,
        fixture_file_count=fixture_files,
    )


# --- MAP -------------------------------------------------------------------


def test_render_map() -> None:
    out = render_map(_build_facts())
    assert out.startswith("# MAP — python_sample")
    assert "## Overview" in out
    assert "## Most central files" in out
    assert "greeter.py" in out
    assert "EXTRACTED" in out  # confidence banner present


def test_render_map_reports_test_surface() -> None:
    out = render_map(_build_facts(test_files=9, fixture_files=4))
    assert "Test surface" in out
    assert "9 test file(s)" in out
    assert "4 fixture file(s)" in out


# --- HOTPATHS --------------------------------------------------------------


def test_render_hotpaths() -> None:
    out = render_hotpaths(_build_facts())
    assert out.startswith("# HOTPATHS — python_sample")
    assert "## Dependency hot spots" in out
    assert "## Change hot spots" in out
    assert "## Churn × centrality" in out
    assert "greeter.py" in out


def test_render_hotpaths_without_git() -> None:
    out = render_hotpaths(_build_facts(is_git=False))
    assert "No git history available" in out
    assert "## Churn × centrality" not in out  # omitted without history


# --- ARCHAEOLOGY -----------------------------------------------------------


def test_render_archaeology() -> None:
    out = render_archaeology(_build_facts())
    assert out.startswith("# ARCHAEOLOGY — python_sample")
    assert "## Timeline" in out
    assert "Alice" in out
    assert "## GitHub" in out


def test_render_archaeology_without_git() -> None:
    out = render_archaeology(_build_facts(is_git=False))
    assert "not a git repository" in out


def test_render_archaeology_with_github() -> None:
    github = GitHubStats(
        owner="octocat",
        name="python-sample",
        description="A sample repo",
        stars=123,
        open_issues=4,
        created_at=datetime(2015, 3, 1, tzinfo=UTC),
        pushed_at=datetime(2024, 1, 1, tzinfo=UTC),
        default_branch="main",
    )
    out = render_archaeology(_build_facts(github=github))
    assert "octocat/python-sample" in out
    assert "123" in out


# --- MENTAL_MODEL ----------------------------------------------------------


def test_render_mental_model() -> None:
    out = render_mental_model(_build_facts())
    assert out.startswith("# MENTAL_MODEL — python_sample")
    assert "## Core modules" in out
    assert "## Layers" in out
    # app.py matches the entry-point stem heuristic
    assert "Likely entry points" in out
    assert "app.py" in out


# --- AGENT_BRIEF -----------------------------------------------------------


def test_render_agent_brief_under_cap() -> None:
    brief, deep = render_agent_brief(_build_facts())
    assert brief.startswith("# AGENT_BRIEF — python_sample")
    assert byte_len(brief) <= AGENT_BRIEF_BYTE_CAP
    assert deep is None  # a tiny repo fits comfortably
    assert "### Always" in brief
    assert "### Never" in brief
    assert "[EXTRACTED]" in brief


def test_render_agent_brief_overflows_into_deep() -> None:
    brief, deep = render_agent_brief(_build_facts(), byte_cap=900)
    assert byte_len(brief) <= 900
    assert deep is not None
    assert deep.startswith("# AGENT_BRIEF_DEEP — python_sample")
    assert "AGENT_BRIEF_DEEP.md" in brief  # pointer to the overflow


# --- render_all ------------------------------------------------------------


# --- DEC-015 confidence labels --------------------------------------------


def test_confidence_banner_drops_v01_blanket_claim() -> None:
    """DEC-015: the v0.1 'every fact below is EXTRACTED' banner overstated
    determinism for ranking-derived sections. The new banner declares
    EXTRACTED as the default and points readers at per-section overrides."""
    out = render_map(_build_facts())
    # Old wording must be gone.
    assert "every fact below is `EXTRACTED`" not in out
    # New wording present and references DEC-015.
    assert "unless a section / line says otherwise" in out
    assert "DEC-015" in out


def test_map_pagerank_sections_carry_inferred_note() -> None:
    """DEC-015: 'Most central files' and 'Key definitions' are ranking
    interpretations — INFERRED, not EXTRACTED."""
    out = render_map(_build_facts())
    # Both PageRank-derived sections must declare INFERRED.
    central_pos = out.index("## Most central files")
    keydefs_pos = out.index("## Key definitions")
    central_section = out[central_pos:keydefs_pos]
    keydefs_section = out[keydefs_pos:]
    assert "`INFERRED`" in central_section
    assert "`INFERRED`" in keydefs_section


def test_archaeology_automation_section_carries_inferred_note() -> None:
    """DEC-015: bot classification is regex heuristic — INFERRED."""
    history = GitHistory(
        repo_path=Path("python_sample"),
        is_git_repo=True,
        total_commits=10,
        first_commit=datetime(2020, 1, 1, tzinfo=UTC),
        last_commit=datetime(2024, 6, 1, tzinfo=UTC),
        contributors=[Contributor("Alice", "alice@example.com", 7)],
        churn=[FileChurn("greeter.py", 9)],
        bots=[Contributor("dependabot[bot]", "noreply@github.com", 3)],
    )
    facts = _build_facts()
    facts_with_bot = RepoFacts(
        repo_path=facts.repo_path,
        repo_name=facts.repo_name,
        generated_at=facts.generated_at,
        file_count=facts.file_count,
        language_breakdown=facts.language_breakdown,
        tags=facts.tags,
        symbol_graph=facts.symbol_graph,
        ranked=facts.ranked,
        history=history,
    )
    out = render_archaeology(facts_with_bot)
    automation_pos = out.index("## Automation")
    next_section = out.index("##", automation_pos + 10)
    automation_section = out[automation_pos:next_section]
    assert "`INFERRED`" in automation_section


def test_archaeology_timeline_does_not_carry_inferred_note() -> None:
    """DEC-015: git facts default to EXTRACTED — no override note."""
    out = render_archaeology(_build_facts())
    timeline_pos = out.index("## Timeline")
    contributors_pos = out.index("## Contributors")
    timeline = out[timeline_pos:contributors_pos]
    assert "INFERRED" not in timeline


def test_mental_model_heuristic_sections_carry_inferred_note() -> None:
    """DEC-015: entry-point stem heuristic and PageRank centrality are
    INFERRED."""
    out = render_mental_model(_build_facts())
    entry_pos = out.index("## Likely entry points")
    core_pos = out.index("## Core modules")
    layers_pos = out.index("## Layers")
    entry_section = out[entry_pos:core_pos]
    core_section = out[core_pos:layers_pos]
    layers_section = out[layers_pos:]
    assert "`INFERRED`" in entry_section
    assert "`INFERRED`" in core_section
    # Layers is a raw directory count — pure EXTRACTED.
    assert "INFERRED" not in layers_section


def test_hotpaths_pagerank_fallback_carries_inferred_note() -> None:
    """DEC-015: NetworkX-fallback 'Dependency hot spots' uses PageRank
    ranks — must be flagged INFERRED. (Graph mode uses confidence-mix
    column instead — verified in test_emit_graph_mode.)"""
    out = render_hotpaths(_build_facts())  # no graph_db_path → fallback
    hotspots_pos = out.index("## Dependency hot spots")
    next_pos = out.index("##", hotspots_pos + 10)
    section = out[hotspots_pos:next_pos]
    assert "`INFERRED`" in section


def test_hotpaths_churn_x_centrality_carries_inferred_note() -> None:
    """DEC-015: 'Churn × centrality' is the centrality-derived risk
    framing — INFERRED."""
    out = render_hotpaths(_build_facts())
    pos = out.index("## Churn × centrality")
    section = out[pos:]
    assert "`INFERRED`" in section


def test_agent_brief_header_drops_uniform_extracted_claim() -> None:
    """DEC-015: the v0.1 'Every rule is EXTRACTED' header line lied about
    PageRank-derived rules. New header explains the per-rule tag scheme."""
    brief, _deep = render_agent_brief(_build_facts())
    # Old wording must be gone.
    assert "Every rule is `EXTRACTED`" not in brief
    # New wording present.
    assert "Each rule carries a confidence tag" in brief
    assert "DEC-015" in brief


def test_agent_brief_load_bearing_rule_is_inferred() -> None:
    """DEC-015: 'Treat X as load-bearing' is PageRank-derived — INFERRED.
    The v0.1 rule was always-EXTRACTED, which lied about derivation."""
    brief, _deep = render_agent_brief(_build_facts())
    # Find the load-bearing rule line and assert it carries [INFERRED].
    for line in brief.splitlines():
        if "load-bearing" in line and "Treat" in line:
            assert "`[INFERRED]`" in line, f"load-bearing rule must be INFERRED, got: {line}"
            break
    else:
        raise AssertionError("expected a load-bearing rule in the brief")


def test_agent_brief_central_symbol_rule_is_inferred() -> None:
    """DEC-015: 'Expect X to be central' is PageRank-derived — INFERRED."""
    brief, _deep = render_agent_brief(_build_facts())
    for line in brief.splitlines():
        if "to be central" in line and "carries the most" in line:
            assert "`[INFERRED]`" in line, f"central symbol rule must be INFERRED, got: {line}"
            break
    else:
        raise AssertionError("expected a central-symbol rule in the brief")


def test_agent_brief_churn_point_rule_is_extracted() -> None:
    """DEC-015: churn count is a raw git fact — EXTRACTED."""
    brief, _deep = render_agent_brief(_build_facts())
    for line in brief.splitlines():
        if "biggest churn point" in line:
            assert "`[EXTRACTED]`" in line, f"churn-point rule must be EXTRACTED, got: {line}"
            break
    else:
        raise AssertionError("expected a churn-point rule in the brief")


def test_agent_brief_not_a_git_repo_rule_is_extracted() -> None:
    """DEC-015: the 'not a git repository' claim is literal observation
    — EXTRACTED."""
    brief, _deep = render_agent_brief(_build_facts(is_git=False))
    for line in brief.splitlines():
        if "Never rely on git history" in line:
            assert "`[EXTRACTED]`" in line, f"not-a-git rule must be EXTRACTED, got: {line}"
            break
    else:
        raise AssertionError("expected a 'not a git repo' rule")


def test_agent_brief_still_under_cap_with_mixed_tags() -> None:
    """DEC-015 changes the rule tags but the 5 KB cap holds — INFERRED is
    one char shorter than EXTRACTED so the budget is unaffected."""
    brief, _deep = render_agent_brief(_build_facts())
    assert byte_len(brief) <= AGENT_BRIEF_BYTE_CAP


# --- render_all ------------------------------------------------------------


def test_render_all_produces_the_contract() -> None:
    artifacts = render_all(_build_facts())
    assert set(artifacts) == {
        "MAP.md",
        "HOTPATHS.md",
        "ARCHAEOLOGY.md",
        "MENTAL_MODEL.md",
        "AGENT_BRIEF.md",
    }
    assert byte_len(artifacts["AGENT_BRIEF.md"]) <= AGENT_BRIEF_BYTE_CAP
    for content in artifacts.values():
        assert content.endswith("\n")
