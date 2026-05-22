"""Tests for the symbol-graph PageRank ranking."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.graph import build_symbol_graph
from forensic_deepdive.static.pagerank import rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import Tag, extract_tags

FIXTURES = Path(__file__).parent / "fixtures"


def _rank_python_sample():
    tags: list[Tag] = []
    for rel in ("python_sample/greeter.py", "python_sample/app.py"):
        parsed = parse_file(FIXTURES / rel, rel_path=Path(rel).name)
        assert parsed is not None
        tags.extend(extract_tags(parsed))
    return rank_files(build_symbol_graph(tags))


def test_depended_upon_file_ranks_higher() -> None:
    """greeter.py is imported by app.py, so it must out-rank app.py."""
    ranked = _rank_python_sample()
    assert ranked.file_rank["greeter.py"] > ranked.file_rank["app.py"]


def test_definitions_are_ranked_and_carry_tags() -> None:
    ranked = _rank_python_sample()
    assert ranked.definitions
    # ranking is sorted highest-first
    scores = [d.rank for d in ranked.definitions]
    assert scores == sorted(scores, reverse=True)
    assert "Greeter" in {d.name for d in ranked.definitions}
    assert all(d.tags for d in ranked.definitions)


def test_empty_graph_yields_empty_ranking() -> None:
    ranked = rank_files(build_symbol_graph([]))
    assert ranked.file_rank == {}
    assert ranked.definitions == []


def test_personalization_biases_ranking() -> None:
    """Seeding app.py should lift it relative to the unseeded baseline."""
    tags: list[Tag] = []
    for rel in ("python_sample/greeter.py", "python_sample/app.py"):
        parsed = parse_file(FIXTURES / rel, rel_path=Path(rel).name)
        assert parsed is not None
        tags.extend(extract_tags(parsed))
    sg = build_symbol_graph(tags)

    baseline = rank_files(sg).file_rank["app.py"]
    seeded = rank_files(sg, personalization={"app.py": 1.0}).file_rank["app.py"]
    assert seeded > baseline
