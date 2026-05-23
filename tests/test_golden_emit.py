"""Golden-file emit tests over ``tests/fixtures/tiny_fixture``.

These tests pin the exact text the emitters produce for a small, realistic
mini-repo (Python + Dart, with source / test / fixture roles). If a deliberate
emitter change shifts the output, regenerate the expected files with::

    UPDATE_GOLDEN=1  uv run pytest tests/test_golden_emit.py

Then commit the updated files under ``tests/fixtures/expected_emit/``.

``generated_at`` is pinned and ``GitHistory.is_git_repo`` is forced to ``False``
so the output is deterministic regardless of when or where the test runs.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forensic_deepdive.emit import (
    RepoFacts,
    render_agent_brief,
    render_archaeology,
    render_hotpaths,
    render_map,
    render_mental_model,
)
from forensic_deepdive.history.git_archaeology import GitHistory
from forensic_deepdive.inventory import take_inventory
from forensic_deepdive.static.graph import build_symbol_graph
from forensic_deepdive.static.pagerank import rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import extract_tags

FIXTURES = Path(__file__).parent / "fixtures"
TINY = FIXTURES / "tiny_fixture"
EXPECTED = FIXTURES / "expected_emit"
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"

_FIXED_GENERATED_AT = datetime(2026, 5, 23, tzinfo=UTC)


@pytest.fixture(scope="module")
def tiny_facts() -> RepoFacts:
    """Deterministic RepoFacts built from tiny_fixture (no git, no flatten)."""
    inventory = take_inventory(TINY)
    tags = []
    for source in inventory.source_files:
        parsed = parse_file(source.path, rel_path=source.rel_path)
        if parsed is not None:
            tags.extend(extract_tags(parsed))
    symbol_graph = build_symbol_graph(tags)
    ranked = rank_files(symbol_graph)
    # tiny_fixture sits inside forensic-deepdive's own git tree, so a real
    # analyze_history() would render *this project's* history. Force the
    # non-git path for a stable golden.
    history = GitHistory(
        repo_path=TINY,
        is_git_repo=False,
        total_commits=0,
        first_commit=None,
        last_commit=None,
        contributors=[],
        churn=[],
    )
    return RepoFacts(
        repo_path=TINY,
        repo_name="tiny_fixture",
        generated_at=_FIXED_GENERATED_AT,
        file_count=len(inventory.source_files),
        language_breakdown=inventory.language_breakdown,
        tags=tags,
        symbol_graph=symbol_graph,
        ranked=ranked,
        history=history,
        test_file_count=len(inventory.test_files),
        fixture_file_count=len(inventory.fixture_files),
    )


def _assert_golden(name: str, actual: str) -> None:
    """Compare *actual* to the saved golden, or write it if UPDATE_GOLDEN=1."""
    expected_path = EXPECTED / name
    if UPDATE:
        EXPECTED.mkdir(parents=True, exist_ok=True)
        # Force LF line endings so the file is identical across OSes.
        with expected_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(actual)
        return
    with expected_path.open("r", encoding="utf-8", newline="") as handle:
        expected = handle.read()
    # Normalize CRLF that git autocrlf may have introduced on Windows checkout.
    expected = expected.replace("\r\n", "\n")
    assert actual == expected, (
        f"Golden mismatch for {name}. "
        "Rerun with UPDATE_GOLDEN=1 to refresh after a deliberate change."
    )


@pytest.mark.parametrize(
    ("name", "render"),
    [
        ("MAP.md", render_map),
        ("HOTPATHS.md", render_hotpaths),
        ("ARCHAEOLOGY.md", render_archaeology),
        ("MENTAL_MODEL.md", render_mental_model),
    ],
)
def test_golden_artifact(
    name: str, render: Callable[[RepoFacts], str], tiny_facts: RepoFacts
) -> None:
    _assert_golden(name, render(tiny_facts))


def test_golden_agent_brief(tiny_facts: RepoFacts) -> None:
    brief, deep = render_agent_brief(tiny_facts)
    _assert_golden("AGENT_BRIEF.md", brief)
    # tiny_fixture is small — should comfortably fit the 5 KB cap.
    assert deep is None, "tiny_fixture should fit in AGENT_BRIEF.md"
