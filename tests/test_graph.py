"""Tests for the NetworkX symbol-graph builder."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.graph import build_symbol_graph
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import Tag, extract_tags

FIXTURES = Path(__file__).parent / "fixtures"


def _all_tags(*rels: str) -> list[Tag]:
    tags: list[Tag] = []
    for rel in rels:
        parsed = parse_file(FIXTURES / rel, rel_path=Path(rel).name)
        assert parsed is not None, rel
        tags.extend(extract_tags(parsed))
    return tags


def test_build_symbol_graph_python() -> None:
    tags = _all_tags("python_sample/greeter.py", "python_sample/app.py")
    sg = build_symbol_graph(tags)

    assert {"greeter.py", "app.py"} <= set(sg.graph.nodes)
    # app.py references Greeter / format_message, both defined in greeter.py.
    assert sg.graph.has_edge("app.py", "greeter.py")
    assert sg.defines["Greeter"] == {"greeter.py"}
    assert ("greeter.py", "Greeter") in sg.definitions


def test_edges_carry_ident_and_weight() -> None:
    tags = _all_tags("python_sample/greeter.py", "python_sample/app.py")
    sg = build_symbol_graph(tags)
    for _u, _v, data in sg.graph.edges(data=True):
        assert "ident" in data
        assert data["weight"] > 0


def test_empty_tags_yield_empty_graph() -> None:
    sg = build_symbol_graph([])
    assert sg.graph.number_of_nodes() == 0
    assert sg.defines == {}


def test_isolated_file_still_a_node() -> None:
    """A file with a definition nobody references is still a graph node."""
    tags = [Tag("lonely.py", "Orphan", "def", "class", 0)]
    sg = build_symbol_graph(tags)
    assert "lonely.py" in sg.graph.nodes
