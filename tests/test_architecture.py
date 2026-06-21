"""ARCHITECTURE.md — the separate system-level surface (DEC-090).

Golden over a small cross-stack fixture, unit tests for the confidence→dash
mapping / node-cap / DB-store shape, the no-cross-boundary degrade, and the guard
that ARCHITECTURE.md is NOT a sixth contract artifact (the five goldens stay
byte-identical — that contract is asserted in test_golden_emit/test_emit).

Regenerate the golden after an intentional change:

    UPDATE_GOLDEN=1 uv run pytest tests/test_architecture.py
"""

from __future__ import annotations

import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.emit import render_all
from forensic_deepdive.emit.architecture_md import (
    ARCHITECTURE_FILENAME,
    _render,
    architecture_for_db,
    render_architecture,
)
from forensic_deepdive.pipeline import (
    EmitPhase,
    ExtractConfig,
    PipelineRunner,
    default_phases,
)

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "expected_emit" / ARCHITECTURE_FILENAME
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"
_FIXED = datetime(2026, 5, 23, tzinfo=UTC)


def _facts_with_graph(fixture: str, tmp_path: Path):
    repo = tmp_path / fixture
    shutil.copytree(FIXTURES / fixture, repo)
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=tmp_path / "graph.lbug",
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    return ctx.get(EmitPhase).facts


# --- golden ---------------------------------------------------------------


def test_architecture_golden_cross_stack(tmp_path: Path) -> None:
    """Byte-exact render of a small cross-stack repo (a single EXTRACTED
    ROUTES_TO join). repo_name is normalized so the golden is path-independent."""
    facts = _facts_with_graph("openapi_codegen_sample", tmp_path)
    facts = replace(facts, repo_name="openapi_codegen_sample", generated_at=_FIXED)
    out = render_architecture(facts)
    if UPDATE:
        GOLDEN.write_text(out, encoding="utf-8")
    assert out == GOLDEN.read_text(encoding="utf-8")


# --- unit: confidence -> dash, node cap, DB store shape -------------------


def _edge(src, dst, etype, label, conf, store=False):
    return (src, src.split("::")[-1], dst, dst.split("::")[-1], etype, label, conf, store)


def test_render_confidence_dash_mapping() -> None:
    """EXTRACTED = solid (no linkStyle), INFERRED = `6 4`, AMBIGUOUS = `2 3`."""
    body = "\n".join(
        _render(
            [
                _edge("a.py::x", "b.py::h1", "ROUTES_TO", "GET /a", "EXTRACTED"),
                _edge("a.py::y", "b.py::h2", "ROUTES_TO", "GET /b", "INFERRED"),
                _edge("a.py::z", "b.py::h3", "ROUTES_TO", "GET /c", "AMBIGUOUS"),
            ],
            40,
        )
    )
    # EXTRACTED is admitted first (confidence-sorted) → linkStyle 0 belongs to a
    # later (INFERRED/AMBIGUOUS) edge; assert both dash patterns are present and
    # that there are exactly two dashed links (the EXTRACTED one is solid).
    assert "stroke-dasharray: 6 4" in body  # INFERRED
    assert "stroke-dasharray: 2 3" in body  # AMBIGUOUS
    assert body.count("stroke-dasharray") == 2


def test_render_db_store_uses_cylinder_shape() -> None:
    body = "\n".join(
        _render(
            [
                _edge(
                    "m.py::User", "table::users", "PERSISTS_TO", "persists", "EXTRACTED", store=True
                )
            ],
            40,
        )
    )
    assert '[("users")]' in body  # cylinder node for a DB table
    assert "persists" in body


def test_render_node_cap_summarizes_not_silent_drops() -> None:
    edges = [
        _edge(f"a.py::c{i}", f"b.py::h{i}", "ROUTES_TO", f"GET /{i}", "EXTRACTED")
        for i in range(20)
    ]
    body = "\n".join(_render(edges, 6))  # cap = 6 nodes → most edges dropped
    assert "more edges beyond the 6-node cap" in body


def test_render_is_deterministic() -> None:
    edges = [
        _edge("a.py::y", "b.py::h2", "ROUTES_TO", "GET /b", "INFERRED"),
        _edge("a.py::x", "b.py::h1", "ROUTES_TO", "GET /a", "EXTRACTED"),
    ]
    assert _render(edges, 40) == _render(edges, 40)


# --- degrade + contract guards -------------------------------------------


def test_no_cross_boundary_degrades_honestly(tmp_path: Path) -> None:
    """A repo with no routes/DI/ORM says so instead of rendering an empty diagram."""
    facts = _facts_with_graph("python_sample", tmp_path)
    out = render_architecture(facts)
    assert "No cross-boundary architecture detected" in out
    assert "```mermaid" not in out


def test_architecture_is_not_a_sixth_contract_artifact(tmp_path: Path) -> None:
    """render_all (the five-artifact contract) must NOT include ARCHITECTURE.md."""
    facts = _facts_with_graph("openapi_codegen_sample", tmp_path)
    assert ARCHITECTURE_FILENAME not in render_all(facts)
    assert set(render_all(facts)) == {
        "MAP.md",
        "HOTPATHS.md",
        "ARCHAEOLOGY.md",
        "MENTAL_MODEL.md",
        "AGENT_BRIEF.md",
    }


def test_architecture_filename_is_the_stable_contract_value() -> None:
    """The style layer holds this filename as a local literal (it must not import
    emit/, DEC-078). Pin the constant so the two can't silently diverge."""
    assert ARCHITECTURE_FILENAME == "ARCHITECTURE.md"


def test_architecture_for_db_standalone(tmp_path: Path) -> None:
    """The `forensic diagram` path renders from a graph db alone (minimal facts)."""
    facts = _facts_with_graph("openapi_codegen_sample", tmp_path)
    out = architecture_for_db(facts.graph_db_path, "demo", generated_at=_FIXED)
    assert "# ARCHITECTURE — demo" in out
    assert "```mermaid" in out
    assert "/api/items" in out


def test_extract_writes_architecture_in_graph_mode_only(tmp_path: Path) -> None:
    """EmitPhase writes ARCHITECTURE.md in graph mode; the 5 artifacts always."""
    facts = _facts_with_graph("openapi_codegen_sample", tmp_path)
    out_dir = facts.repo_path / "out"
    assert (out_dir / ARCHITECTURE_FILENAME).is_file()
    assert (out_dir / "AGENT_BRIEF.md").is_file()
