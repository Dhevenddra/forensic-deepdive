"""CALLS ``via`` property round-trip (v0.3 Item C / DEC-037, layer C1).

The ``via`` property records *how* a CALLS edge's callee was resolved
(self|this|ctor|static|module|bare) — the rationale behind ``confidence``. It
must persist and read back, and default to ``"bare"`` for the DEC-025 bare-name
resolver's edges (no behavior change until layer C3 emits method-call edges).
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.graph import LadybugStore, Symbol, SymbolKind
from forensic_deepdive.graph.schema import CallsEdge, Confidence


def _symbol(qn: str) -> Symbol:
    return Symbol(
        qualified_name=qn,
        kind=SymbolKind.FUNCTION,
        file_path=qn.split("::")[0],
        line_start=1,
        line_end=2,
        signature="",
    )


def test_calls_edge_via_defaults_to_bare() -> None:
    assert CallsEdge(caller="a.py::f", callee="a.py::g").via == "bare"


def test_via_round_trips_through_store(tmp_path: Path) -> None:
    db = tmp_path / "g.lbug"
    with LadybugStore(db) as store:
        store.add_many_symbols([_symbol("a.py::f"), _symbol("a.py::g"), _symbol("a.py::h")])
        store.add_calls(
            CallsEdge(
                caller="a.py::f",
                callee="a.py::g",
                confidence=Confidence.INFERRED,
                evidence="receiver-self",
                via="self",
            )
        )
        store.add_many_calls(
            [
                CallsEdge(
                    caller="a.py::f",
                    callee="a.py::h",
                    confidence=Confidence.EXTRACTED,
                    evidence="same-file",
                    # via omitted → defaults to "bare"
                )
            ]
        )
        rows = dict(
            store.query(
                "MATCH (:Symbol {qualified_name: 'a.py::f'})-[c:CALLS]->(callee:Symbol) "
                "RETURN callee.qualified_name, c.via"
            )
        )
    assert rows == {"a.py::g": "self", "a.py::h": "bare"}
