"""Per-language inheritance extraction (DEC-028, REMAINING.md item 8b step 6).

Captures ``class A extends B`` / ``class A implements I`` /
``class A: Base, Protocol`` / ``class A with Mix`` patterns across the
6 supported languages with class hierarchies. Go has no class
hierarchy; C has no inheritance. Both are skipped.

Output is one :class:`InheritanceRecord` per (child_class, parent_name,
kind) triple. The build phase resolves ``parent_name`` to a real
Symbol via the same scoped lookup the CALLS resolver uses (same-file
→ import → cross-file fallback), then emits an EXTENDS or IMPLEMENTS
edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tree_sitter import Node

from forensic_deepdive.static.parse import ParsedFile

InheritanceKind = Literal["extends", "implements"]


@dataclass(frozen=True, slots=True)
class InheritanceRecord:
    """One ``A extends B`` or ``A implements I`` declaration.

    ``child_qn_local`` is the dotted local qualified name of the
    inheriting class (e.g. ``Outer.Inner`` for a nested class).
    ``parent_name`` is the raw type name as written in source; the
    build-phase resolver maps it to an intra-repo Symbol.
    """

    rel_path: str
    child_qn_local: str
    parent_name: str
    kind: InheritanceKind
    language: str
    line: int  # 0-based start row of the child class declaration


def _row(node: Node) -> int:
    point = node.start_point
    return point.row if hasattr(point, "row") else point[0]


def _text(node: Node) -> str:
    return node.text.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Per-language extractors
# ---------------------------------------------------------------------------


def _python_class_qn(node: Node) -> str:
    """Build the dotted qn_local of a Python class_definition by walking
    enclosing class_definitions outermost-to-innermost. Matches the
    convention DEC-023 set for def Tags."""
    chain: list[str] = []
    cur: Node | None = node
    while cur is not None:
        if cur.type == "class_definition":
            name_node = cur.child_by_field_name("name")
            if name_node is not None:
                chain.append(_text(name_node))
        cur = cur.parent
    chain.reverse()
    return ".".join(chain)


def _extract_python(parsed: ParsedFile) -> list[InheritanceRecord]:
    """Python: ``class Derived(Base, Mixin)`` — every identifier in the
    base argument_list is treated as EXTENDS (Python's MRO collapses
    interface-vs-superclass)."""
    records: list[InheritanceRecord] = []
    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "class_definition":
            child_qn = _python_class_qn(node)
            # Find the optional argument_list of base classes.
            for c in node.children:
                if c.type != "argument_list":
                    continue
                for arg in c.children:
                    if arg.type == "identifier":
                        records.append(
                            InheritanceRecord(
                                rel_path=parsed.rel_path,
                                child_qn_local=child_qn,
                                parent_name=_text(arg),
                                kind="extends",
                                language=parsed.language,
                                line=_row(node),
                            )
                        )
                    elif arg.type == "attribute":
                        # `pkg.Base` — keep only the rightmost identifier
                        # so the resolver can match against the imported
                        # name. v0.3 may track the qualified path.
                        last_id = None
                        for ac in arg.children:
                            if ac.type == "identifier":
                                last_id = ac
                        if last_id is not None:
                            records.append(
                                InheritanceRecord(
                                    rel_path=parsed.rel_path,
                                    child_qn_local=child_qn,
                                    parent_name=_text(last_id),
                                    kind="extends",
                                    language=parsed.language,
                                    line=_row(node),
                                )
                            )
        stack.extend(node.children)
    return records


def _ts_type_name(node: Node) -> str | None:
    """The declared name of a class/interface declaration: the ``name`` field,
    falling back to the first ``type_identifier`` child."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node)
    for c in node.children:
        if c.type == "type_identifier":
            return _text(c)
    return None


def _ts_base_name(node: Node) -> str | None:
    """Resolve a heritage *target* node to the resolvable parent name (DEC-050).

    Handles the four TS shapes a clause member can take:
      * ``identifier`` / ``type_identifier`` → its text (the simple case);
      * ``generic_type`` (``Comparable<Widget>``) → the inner base type's name,
        dropping the ``type_arguments``;
      * ``member_expression`` (``React.Component``) → the **rightmost**
        ``property_identifier`` (mirrors the Python ``attribute`` convention).
    ``type_arguments`` and other nodes yield ``None`` (skipped by the caller),
    so ``extends Foo<T>`` produces one record for ``Foo``, not a stray ``T``."""
    t = node.type
    if t in ("identifier", "type_identifier"):
        return _text(node)
    if t == "generic_type":
        for c in node.children:
            if c.type in ("identifier", "type_identifier"):
                return _text(c)
            if c.type == "member_expression":
                return _ts_member_expr_name(c)
        return None
    if t == "member_expression":
        return _ts_member_expr_name(node)
    return None


def _ts_member_expr_name(node: Node) -> str | None:
    """``a.b.c`` → the rightmost named segment (``c``). Mirrors how the Python
    extractor keeps only the rightmost identifier of a dotted base type."""
    name: str | None = None
    for c in node.children:
        if c.type in ("property_identifier", "identifier", "type_identifier"):
            name = _text(c)
    return name


def _ts_js_extract(parsed: ParsedFile) -> list[InheritanceRecord]:
    """TypeScript / TSX / JavaScript heritage (DEC-028 + DEC-050).

    Classes (``class_declaration`` **and** ``abstract_class_declaration``) carry
    a ``class_heritage`` with TS-wrapped ``extends_clause`` / ``implements_clause``
    or a JS bare-identifier shape. Interfaces (``interface_declaration``) carry an
    ``extends_type_clause`` (interface→interface, modeled as EXTENDS). Heritage
    targets may be plain identifiers, ``generic_type``, or ``member_expression`` —
    all unwrapped by :func:`_ts_base_name`."""
    records: list[InheritanceRecord] = []

    def emit(child_name: str, base: str | None, kind: InheritanceKind, line: int) -> None:
        if base:
            records.append(
                InheritanceRecord(
                    rel_path=parsed.rel_path,
                    child_qn_local=child_name,
                    parent_name=base,
                    kind=kind,
                    language=parsed.language,
                    line=line,
                )
            )

    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in ("class_declaration", "abstract_class_declaration"):
            child_name = _ts_type_name(node)
            if child_name is not None:
                for child in node.children:
                    if child.type != "class_heritage":
                        continue
                    # Walk class_heritage children. TS wraps each clause; JS puts
                    # bare identifiers directly under class_heritage, with an
                    # `extends` / `implements` keyword flipping the mode.
                    mode: InheritanceKind = "extends"  # JS heritage starts in extends
                    for hc in child.children:
                        if hc.type == "extends":
                            mode = "extends"
                        elif hc.type == "implements":
                            mode = "implements"
                        elif hc.type == "extends_clause":
                            for ec in hc.children:
                                emit(child_name, _ts_base_name(ec), "extends", _row(node))
                        elif hc.type == "implements_clause":
                            for ic in hc.children:
                                emit(child_name, _ts_base_name(ic), "implements", _row(node))
                        else:
                            # JS shape — bare target under class_heritage.
                            emit(child_name, _ts_base_name(hc), mode, _row(node))
        elif node.type == "interface_declaration":
            child_name = _ts_type_name(node)
            if child_name is not None:
                for child in node.children:
                    if child.type == "extends_type_clause":
                        for ec in child.children:
                            emit(child_name, _ts_base_name(ec), "extends", _row(node))
        stack.extend(node.children)
    return records


def _extract_java(parsed: ParsedFile) -> list[InheritanceRecord]:
    """Java: ``class_declaration > superclass: (extends type_identifier)
    > super_interfaces (implements type_list type_identifier+)``."""
    records: list[InheritanceRecord] = []
    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                stack.extend(node.children)
                continue
            child_name = _text(name_node)
            for child in node.children:
                if child.type == "superclass":
                    for sc in child.children:
                        if sc.type == "type_identifier":
                            records.append(
                                InheritanceRecord(
                                    rel_path=parsed.rel_path,
                                    child_qn_local=child_name,
                                    parent_name=_text(sc),
                                    kind="extends",
                                    language=parsed.language,
                                    line=_row(node),
                                )
                            )
                elif child.type == "super_interfaces":
                    for sic in child.children:
                        if sic.type == "type_list":
                            for tic in sic.children:
                                if tic.type == "type_identifier":
                                    records.append(
                                        InheritanceRecord(
                                            rel_path=parsed.rel_path,
                                            child_qn_local=child_name,
                                            parent_name=_text(tic),
                                            kind="implements",
                                            language=parsed.language,
                                            line=_row(node),
                                        )
                                    )
        elif node.type == "interface_declaration":
            # Java interface extends interface — model as EXTENDS.
            name_node = node.child_by_field_name("name")
            if name_node is None:
                stack.extend(node.children)
                continue
            child_name = _text(name_node)
            for child in node.children:
                if child.type == "extends_interfaces":
                    for sub in child.children:
                        if sub.type == "type_list":
                            for tic in sub.children:
                                if tic.type == "type_identifier":
                                    records.append(
                                        InheritanceRecord(
                                            rel_path=parsed.rel_path,
                                            child_qn_local=child_name,
                                            parent_name=_text(tic),
                                            kind="extends",
                                            language=parsed.language,
                                            line=_row(node),
                                        )
                                    )
        stack.extend(node.children)
    return records


def _extract_dart(parsed: ParsedFile) -> list[InheritanceRecord]:
    """Dart: ``class_definition > superclass (extends Base [with Mix])
    > interfaces (implements I)``. Mixins (the ``with`` clause) are
    modeled as IMPLEMENTS — they're closer to interface-style
    capability bundles than to true superclasses in our graph."""
    records: list[InheritanceRecord] = []
    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            # Fall back to the first identifier child.
            if name_node is None:
                for c in node.children:
                    if c.type == "identifier":
                        name_node = c
                        break
            if name_node is None:
                stack.extend(node.children)
                continue
            child_name = _text(name_node)
            for child in node.children:
                if child.type == "superclass":
                    for sc in child.children:
                        if sc.type == "type_identifier":
                            records.append(
                                InheritanceRecord(
                                    rel_path=parsed.rel_path,
                                    child_qn_local=child_name,
                                    parent_name=_text(sc),
                                    kind="extends",
                                    language=parsed.language,
                                    line=_row(node),
                                )
                            )
                        elif sc.type == "mixins":
                            for mc in sc.children:
                                if mc.type == "type_identifier":
                                    records.append(
                                        InheritanceRecord(
                                            rel_path=parsed.rel_path,
                                            child_qn_local=child_name,
                                            parent_name=_text(mc),
                                            kind="implements",
                                            language=parsed.language,
                                            line=_row(node),
                                        )
                                    )
                elif child.type == "interfaces":
                    for ic in child.children:
                        if ic.type == "type_identifier":
                            records.append(
                                InheritanceRecord(
                                    rel_path=parsed.rel_path,
                                    child_qn_local=child_name,
                                    parent_name=_text(ic),
                                    kind="implements",
                                    language=parsed.language,
                                    line=_row(node),
                                )
                            )
        stack.extend(node.children)
    return records


def _extract_swift(parsed: ParsedFile) -> list[InheritanceRecord]:
    """Swift: ``class_declaration > inheritance_specifier > user_type >
    type_identifier``. We can't trivially distinguish "is a class vs is
    a protocol" without symbol-kind cross-reference, so all parents are
    captured as EXTENDS. v0.3 may refine by joining against the
    parent's SymbolKind."""
    records: list[InheritanceRecord] = []
    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                for c in node.children:
                    if c.type == "type_identifier":
                        name_node = c
                        break
            if name_node is None:
                stack.extend(node.children)
                continue
            child_name = _text(name_node)
            for child in node.children:
                if child.type == "inheritance_specifier":
                    for sc in child.children:
                        if sc.type == "user_type":
                            for ut in sc.children:
                                if ut.type == "type_identifier":
                                    records.append(
                                        InheritanceRecord(
                                            rel_path=parsed.rel_path,
                                            child_qn_local=child_name,
                                            parent_name=_text(ut),
                                            kind="extends",
                                            language=parsed.language,
                                            line=_row(node),
                                        )
                                    )
        stack.extend(node.children)
    return records


# ---------------------------------------------------------------------------
# Rust (DEC-040)
# ---------------------------------------------------------------------------


def _extract_rust(parsed: ParsedFile) -> list[InheritanceRecord]:
    """``impl Trait for Type`` declares that ``Type`` implements ``Trait`` →
    one IMPLEMENTS record. (Inherent ``impl Type {}`` blocks carry no trait and
    produce nothing.) Rust has no struct inheritance, so there are no EXTENDS
    records — trait *supertraits* (``trait A: B``) are a v0.6 follow-on."""
    records: list[InheritanceRecord] = []
    stack = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "impl_item":
            trait_node = node.child_by_field_name("trait")
            type_node = node.child_by_field_name("type")
            if trait_node is not None and type_node is not None:
                records.append(
                    InheritanceRecord(
                        rel_path=parsed.rel_path,
                        child_qn_local=_text(type_node),
                        parent_name=_text(trait_node),
                        kind="implements",
                        language="rust",
                        line=_row(node),
                    )
                )
        stack.extend(node.children)
    return records


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


_EXTRACTORS = {
    "python": _extract_python,
    "typescript": _ts_js_extract,
    "tsx": _ts_js_extract,
    "javascript": _ts_js_extract,
    "java": _extract_java,
    "dart": _extract_dart,
    "swift": _extract_swift,
    "rust": _extract_rust,  # DEC-040: impl Trait for Type → IMPLEMENTS
    # Go: no class hierarchy; interface satisfaction is structural at
    # use-sites and not declared. v0.3 may infer via type-set analysis.
    # C: no inheritance.
}


def extract_inheritance(parsed: ParsedFile) -> list[InheritanceRecord]:
    """Per-language inheritance extraction. Returns an empty list for
    languages without a class hierarchy (Go, C)."""
    extractor = _EXTRACTORS.get(parsed.language)
    if extractor is None:
        return []
    records = extractor(parsed)
    records.sort(key=lambda r: (r.rel_path, r.child_qn_local, r.kind, r.parent_name))
    return records
