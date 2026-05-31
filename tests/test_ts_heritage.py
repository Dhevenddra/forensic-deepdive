"""TS/TSX heritage capture (v0.4 Item B / DEC-050).

Covers the four under-capture gaps the v0.3 findings surfaced — abstract
classes, interface->interface extends, generic_type targets, and
member_expression targets — plus the simple-case regression guard.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.inheritance import extract_inheritance
from forensic_deepdive.static.parse import parse_file

FIXTURES = Path(__file__).parent / "fixtures"
HERITAGE = FIXTURES / "typescript_heritage_sample"


def _records(name: str) -> set[tuple[str, str, str]]:
    """{(child, kind, parent)} for every heritage record in a fixture file."""
    parsed = parse_file(HERITAGE / name, rel_path=name)
    return {(r.child_qn_local, r.kind, r.parent_name) for r in extract_inheritance(parsed)}


def test_interface_extends_interface_single_and_multiple() -> None:
    recs = _records("heritage.ts")
    # interface Animal extends Named
    assert ("Animal", "extends", "Named") in recs
    # interface Pet extends Animal, Comparable<Pet> — multiple, incl. generic.
    assert ("Pet", "extends", "Animal") in recs
    assert ("Pet", "extends", "Comparable") in recs


def test_abstract_class_heritage_captured() -> None:
    recs = _records("heritage.ts")
    # abstract class Shape extends Widget implements Named
    assert ("Shape", "extends", "Widget") in recs
    assert ("Shape", "implements", "Named") in recs


def test_generic_type_and_member_expression_targets() -> None:
    recs = _records("heritage.ts")
    # class Button extends React.Component<Props> implements Comparable<Button>
    # member_expression React.Component -> rightmost "Component".
    assert ("Button", "extends", "Component") in recs
    # generic_type Comparable<Button> -> base "Comparable".
    assert ("Button", "implements", "Comparable") in recs
    # The type argument must NOT leak as its own record.
    assert ("Button", "extends", "Props") not in recs


def test_simple_case_regression_guard() -> None:
    """Plain identifier extends + multi-interface implements still works
    exactly (DEC-050 is purely additive)."""
    recs = _records("heritage.ts")
    assert ("Card", "extends", "Widget") in recs
    assert ("Card", "implements", "Named") in recs
    assert ("Card", "implements", "Mix") in recs


def test_no_spurious_records_for_base_file() -> None:
    """base.ts has no heritage clauses (only declarations) -> no records."""
    assert _records("base.ts") == set()
