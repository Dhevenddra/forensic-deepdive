"""DEC-051 (v0.4 Item A): stable node-ID authority."""

from __future__ import annotations

from forensic_deepdive.graph.schema import Symbol, SymbolKind
from forensic_deepdive.static.ids import (
    SymbolDescriptor,
    assign_disambiguators,
    make_endpoint_id,
    make_module_id,
    make_symbol_id,
)


def test_unique_symbol_gets_clean_id_no_disambiguator():
    ids = assign_disambiguators([SymbolDescriptor("method", "src/foo.py", "Greeter.greet")])
    assert ids == ["method:src/foo.py:Greeter.greet"]


def test_two_overloaded_methods_get_distinct_stable_ids():
    """The headline acceptance: same (kind, rel_path, qn_local) → distinct ids."""
    descriptors = [
        SymbolDescriptor("method", "src/foo.py", "Calc.add"),
        SymbolDescriptor("method", "src/foo.py", "Calc.add"),
    ]
    ids = assign_disambiguators(descriptors)
    assert len(set(ids)) == 2
    assert ids == [
        "method:src/foo.py:Calc.add#0",
        "method:src/foo.py:Calc.add#1",
    ]


def test_overloads_with_distinct_signatures_use_content_hash():
    """Distinct signatures on the same triple → ~hash, stable regardless of
    definition order."""
    a = SymbolDescriptor("method", "src/foo.py", "Calc.add", signature="(int, int)")
    b = SymbolDescriptor("method", "src/foo.py", "Calc.add", signature="(float, float)")

    ids_ab = assign_disambiguators([a, b])
    ids_ba = assign_disambiguators([b, a])

    # Both distinct, hash-tagged.
    assert len(set(ids_ab)) == 2
    assert all("~" in i for i in ids_ab)
    # Order-independent: a's id is the same whether it came first or second.
    assert ids_ab[0] == ids_ba[1]
    assert ids_ab[1] == ids_ba[0]


def test_id_is_invariant_under_unrelated_line_change():
    """The forward-compat seam: the id has no line numbers, so a symbol whose
    definition moves (an unrelated edit above it) keeps the same id."""
    before = make_symbol_id("function", "src/util.py", "helper")
    # Simulate the symbol shifting down 10 lines after an unrelated edit — the
    # descriptor's (kind, rel_path, qn_local) are unchanged.
    after = make_symbol_id("function", "src/util.py", "helper")
    assert before == after


def test_assign_disambiguators_deterministic_across_permutations():
    """Three colliding triples presented in any order mint the same id set."""
    triples = [
        SymbolDescriptor("method", "a.py", "C.m"),
        SymbolDescriptor("method", "a.py", "C.m"),
        SymbolDescriptor("method", "a.py", "C.m"),
    ]
    ids_forward = assign_disambiguators(triples)
    ids_reversed = assign_disambiguators(list(reversed(triples)))
    assert set(ids_forward) == set(ids_reversed)
    assert sorted(ids_forward) == [
        "method:a.py:C.m#0",
        "method:a.py:C.m#1",
        "method:a.py:C.m#2",
    ]


def test_distinct_triples_never_collide():
    ids = assign_disambiguators(
        [
            SymbolDescriptor("class", "a.py", "Foo"),
            SymbolDescriptor("function", "a.py", "Foo"),  # same name, different kind
            SymbolDescriptor("class", "b.py", "Foo"),  # same name+kind, different file
        ]
    )
    assert len(set(ids)) == 3
    assert "" not in ids


def test_endpoint_and_module_id_seams():
    assert make_endpoint_id("http::GET::/users/{param}") == "http::GET::/users/{param}"
    assert make_module_id("python", "os") == "python:os"
    assert make_module_id("go", "os") == "go:os"
    assert make_module_id("python", "os") != make_module_id("go", "os")


def test_symbol_node_id_falls_back_to_qualified_name():
    """A Symbol constructed without an explicit node_id keys on its
    qualified_name — read-side reconstructions need not supply the id."""
    s = Symbol(
        qualified_name="src/foo.py::Greeter.greet",
        kind=SymbolKind.METHOD,
        file_path="src/foo.py",
        line_start=1,
        line_end=3,
    )
    assert s.node_id == "src/foo.py::Greeter.greet"


def test_symbol_explicit_node_id_preserved():
    s = Symbol(
        qualified_name="src/foo.py::Greeter.greet",
        kind=SymbolKind.METHOD,
        file_path="src/foo.py",
        line_start=1,
        line_end=3,
        node_id="method:src/foo.py:Greeter.greet",
    )
    assert s.node_id == "method:src/foo.py:Greeter.greet"
    assert s.qualified_name == "src/foo.py::Greeter.greet"
