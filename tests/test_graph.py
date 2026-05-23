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


def test_build_symbol_graph_new_languages() -> None:
    """DEC-020. Each v0.2 language (TS, JS, Java, Go) produces a real
    caller->definer edge through the v0.1 graph builder, with DEC-012
    language scoping applied (no cross-language false edges)."""
    cases = [
        ("typescript_sample/greeter.ts", "typescript_sample/app.ts"),
        ("javascript_sample/greeter.js", "javascript_sample/app.js"),
        ("java_sample/Greeter.java", "java_sample/Main.java"),
        ("go_sample/greeter.go", "go_sample/main.go"),
    ]
    for definer_rel, caller_rel in cases:
        tags = _all_tags(definer_rel, caller_rel)
        sg = build_symbol_graph(tags)
        # The graph builder uses Path(rel).name as the node id (via _all_tags
        # above), so we compare on basenames.
        caller = Path(caller_rel).name
        definer = Path(definer_rel).name
        assert sg.graph.has_edge(caller, definer), (
            f"{caller} -> {definer} edge missing for {definer_rel}"
        )


def test_empty_tags_yield_empty_graph() -> None:
    sg = build_symbol_graph([])
    assert sg.graph.number_of_nodes() == 0
    assert sg.defines == {}


def test_isolated_file_still_a_node() -> None:
    """A file with a definition nobody references is still a graph node."""
    tags = [Tag("lonely.py", "Orphan", "def", "class", 0, "python")]
    sg = build_symbol_graph(tags)
    assert "lonely.py" in sg.graph.nodes


def test_no_cross_language_edges() -> None:
    """DEC-012: a referencer only links to definers of the same language."""
    tags = [
        Tag("b.py", "Shared", "def", "class", 0, "python"),
        Tag("c.dart", "Shared", "def", "class", 0, "dart"),
        Tag("a.dart", "Shared", "ref", "call", 0, "dart"),
    ]
    sg = build_symbol_graph(tags)
    assert sg.graph.has_edge("a.dart", "c.dart")  # same language
    assert not sg.graph.has_edge("a.dart", "b.py")  # cross-language: dropped


def test_local_definition_shadows() -> None:
    """DEC-012: a file that defines an identifier resolves it locally."""
    tags = [
        Tag("a.py", "helper", "def", "function", 0, "python"),
        Tag("a.py", "helper", "ref", "call", 5, "python"),
        Tag("b.py", "helper", "def", "function", 0, "python"),
        Tag("c.py", "helper", "ref", "call", 0, "python"),
    ]
    sg = build_symbol_graph(tags)
    # a.py defines `helper`, so its own reference is shadowed — no edge.
    assert not sg.graph.has_edge("a.py", "b.py")
    # c.py does not define `helper`, so it links to every definer.
    assert sg.graph.has_edge("c.py", "a.py")
    assert sg.graph.has_edge("c.py", "b.py")
