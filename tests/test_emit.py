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


def _build_facts(*, is_git: bool = True, github: GitHubStats | None = None) -> RepoFacts:
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
    )


# --- MAP -------------------------------------------------------------------


def test_render_map() -> None:
    out = render_map(_build_facts())
    assert out.startswith("# MAP — python_sample")
    assert "## Overview" in out
    assert "## Most central files" in out
    assert "greeter.py" in out
    assert "EXTRACTED" in out  # confidence banner present


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
