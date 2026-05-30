"""Mermaid visual export (DEC-039, PRD §4.6 tests).

Two graph styles: a real python_sample graph (structural / auto-pick /
determinism) and a hand-built graph with controlled confidences (the exact
confidence -> dash mapping).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from forensic_deepdive.emit.mermaid import render_mermaid
from forensic_deepdive.graph import (
    CallsEdge,
    Confidence,
    DefinesEdge,
    File,
    LadybugStore,
    Symbol,
    SymbolKind,
)
from forensic_deepdive.graph.schema import FileRole
from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    repo = tmp_path / "py"
    shutil.copytree(FIXTURES / "python_sample", repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return db_path


def _hand_built(tmp_path: Path, confidences: list[str], *, n_extracted: int = 0) -> Path:
    """A graph with one root calling one callee per confidence in *confidences*
    (plus *n_extracted* extra EXTRACTED callees, for the node-cap test)."""
    db_path = tmp_path / "hand.lbug"
    files = [
        File(path="a.py", language="python", role=FileRole.SOURCE, sha="x", loc=1, last_modified="")
    ]
    symbols = [
        Symbol(
            qualified_name="a.py::root",
            kind=SymbolKind.FUNCTION,
            file_path="a.py",
            line_start=1,
            line_end=1,
        )
    ]
    defines = [DefinesEdge(file_path="a.py", symbol="a.py::root")]
    calls: list[CallsEdge] = []
    for i, conf in enumerate(confidences):
        qn = f"a.py::callee_{conf.lower()}_{i}"
        symbols.append(
            Symbol(
                qualified_name=qn,
                kind=SymbolKind.FUNCTION,
                file_path="a.py",
                line_start=2,
                line_end=2,
            )
        )
        defines.append(DefinesEdge(file_path="a.py", symbol=qn))
        calls.append(CallsEdge(caller="a.py::root", callee=qn, confidence=Confidence(conf)))
    for i in range(n_extracted):
        qn = f"a.py::extra_{i:03d}"
        symbols.append(
            Symbol(
                qualified_name=qn,
                kind=SymbolKind.FUNCTION,
                file_path="a.py",
                line_start=3,
                line_end=3,
            )
        )
        defines.append(DefinesEdge(file_path="a.py", symbol=qn))
        calls.append(CallsEdge(caller="a.py::root", callee=qn, confidence=Confidence.EXTRACTED))
    with LadybugStore(db_path) as store:
        store.add_many_files(files)
        store.add_many_symbols(symbols)
        store.add_many_defines(defines)
        store.add_many_calls(calls)
    return db_path


# --- structural / real graph ------------------------------------------------


def test_flowchart_for_symbol(populated_db: Path) -> None:
    out = render_mermaid(populated_db, "Greeter.greet", direction="out", depth=1)
    body = out["mermaid"]
    assert out["diagram"] == "flowchart"
    assert body.startswith("```mermaid\nflowchart LR")
    assert body.endswith("\n```")
    # greet calls format_message — the callee should appear.
    assert "format_message" in body
    assert "-->|CALLS|" in body


def test_auto_picks_classdiagram_for_a_class(populated_db: Path) -> None:
    out = render_mermaid(populated_db, "Greeter")
    assert out["diagram"] == "classDiagram"
    body = out["mermaid"]
    assert "classDiagram" in body
    assert "class Greeter" in body
    assert "+greet()" in body
    assert "+__init__()" in body


def test_unresolved_target(populated_db: Path) -> None:
    out = render_mermaid(populated_db, "no_such_symbol_xyz")
    assert out.get("unresolved") is True


def test_central_renders_flowchart(populated_db: Path) -> None:
    out = render_mermaid(populated_db, central=True, max_nodes=10)
    assert out["diagram"] == "flowchart"
    assert out["mermaid"].startswith("```mermaid\nflowchart LR")
    assert out["target"] == "<central>"


def test_render_is_deterministic(populated_db: Path) -> None:
    a = render_mermaid(populated_db, "Greeter.greet", direction="out", depth=2)
    b = render_mermaid(populated_db, "Greeter.greet", direction="out", depth=2)
    assert a["mermaid"] == b["mermaid"]  # byte-identical


def test_bad_direction_and_format(populated_db: Path) -> None:
    assert "error" in render_mermaid(populated_db, "Greeter", direction="sideways")


# --- confidence -> dash mapping (hand-built) --------------------------------


def test_confidence_dash_mapping(tmp_path: Path) -> None:
    db = _hand_built(tmp_path, ["EXTRACTED", "INFERRED", "AMBIGUOUS"])
    body = render_mermaid(db, "a.py::root", direction="out", depth=1)["mermaid"]
    # INFERRED -> dashed, AMBIGUOUS -> dotted, EXTRACTED -> solid (no linkStyle).
    assert "stroke-dasharray: 6 4" in body  # INFERRED
    assert "stroke-dasharray: 2 3" in body  # AMBIGUOUS
    assert body.count("linkStyle ") == 2  # only the two non-EXTRACTED edges styled
    assert body.count("-->|CALLS|") == 3  # all three edges drawn


def test_node_cap_summarizes_not_drops(tmp_path: Path) -> None:
    db = _hand_built(tmp_path, [], n_extracted=50)  # root + 50 callees
    out = render_mermaid(db, "a.py::root", direction="out", depth=1, max_nodes=5)
    assert out["truncated"] is True
    body = out["mermaid"]
    assert "… (+" in body  # summary node, not a silent drop
    assert "more)" in body
