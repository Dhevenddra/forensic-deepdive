"""ORM entity→table extraction (DEC-059, v0.5 Step 4 — the ORM tail terminal).

A sibling to :mod:`forensic_deepdive.static.inheritance`: it walks a parsed file and
emits one :class:`PersistenceRecord` per ORM model. The build phase materializes a
:class:`~forensic_deepdive.graph.schema.Table` node (PK ``table::<name>``) and a
``PERSISTS_TO`` edge from the model Symbol.

Shapes (research §4):
- **SQLAlchemy (Python)** — ``class User(Base): __tablename__ = "users"`` → literal
  table name (EXTRACTED).
- **Django (Python)** — ``class User(models.Model): class Meta: db_table = "users"``
  → literal (EXTRACTED); no ``db_table`` → the model name lowered (INFERRED,
  convention-derived — the true Django default is ``<app>_<model>``, but the app
  label isn't statically recoverable here).
- **JPA (Java)** — ``@Entity @Table(name="users") class User`` → literal (EXTRACTED);
  ``@Entity`` with no ``@Table`` → the class name (the JPA default, INFERRED).

Deferred (DEC-059): TypeORM/Prisma; SQLAlchemy imperative ``Table()`` mapping;
relationship / foreign-key (``RELATES_TO``) table-to-table edges.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from forensic_deepdive.static.parse import ParsedFile


@dataclass(frozen=True, slots=True)
class PersistenceRecord:
    """One ORM model→table binding. ``model_qn_local`` is the model class's dotted
    local qn; ``table_name`` is the resolved table name; ``literal`` marks a
    syntactic name (``__tablename__``/``@Table(name=)``) vs a convention-derived one."""

    rel_path: str
    model_qn_local: str
    table_name: str
    orm: str  # sqlalchemy | jpa | django
    framework: str
    language: str
    line: int
    literal: bool


def _row(node: Node) -> int:
    point = node.start_point
    return point.row if hasattr(point, "row") else point[0]


def _text(node: Node) -> str:
    return node.text.decode("utf-8", "replace")


def _iter(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def _py_string_value(node: Node) -> str | None:
    """A plain Python ``string`` literal's content, or ``None`` if computed."""
    if node.type != "string":
        return None
    parts: list[str] = []
    for child in node.children:
        if child.type == "interpolation":
            return None
        if child.type == "string_content":
            parts.append(_text(child))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Python — SQLAlchemy + Django
# ---------------------------------------------------------------------------


def _python_class_qn(node: Node) -> str:
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


def _class_base_names(node: Node) -> list[str]:
    names: list[str] = []
    for c in node.children:
        if c.type != "argument_list":
            continue
        for arg in c.children:
            if arg.type == "identifier":
                names.append(_text(arg))
            elif arg.type == "attribute":  # models.Model → rightmost
                attr = arg.child_by_field_name("attribute")
                if attr is not None:
                    names.append(_text(attr))
    return names


def _class_assign_literal(body: Node, name: str) -> str | None:
    """A class-body ``<name> = "literal"`` value (handles the bare ``assignment``
    or one wrapped in an ``expression_statement``)."""
    for stmt in body.children:
        assign = stmt if stmt.type == "assignment" else None
        if assign is None and stmt.type == "expression_statement":
            assign = next((c for c in stmt.children if c.type == "assignment"), None)
        if assign is None:
            continue
        left = assign.child_by_field_name("left")
        right = assign.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier":
            continue
        if _text(left) == name and right.type == "string":
            return _py_string_value(right)
    return None


def _django_meta_db_table(body: Node) -> str | None:
    """The literal ``db_table`` from a nested ``class Meta:`` block, or ``None``."""
    for stmt in body.children:
        inner = stmt if stmt.type == "class_definition" else None
        if inner is None:
            continue
        name_node = inner.child_by_field_name("name")
        if name_node is None or _text(name_node) != "Meta":
            continue
        meta_body = inner.child_by_field_name("body")
        if meta_body is not None:
            return _class_assign_literal(meta_body, "db_table")
    return None


def _extract_python(parsed: ParsedFile) -> list[PersistenceRecord]:
    records: list[PersistenceRecord] = []
    for node in _iter(parsed.tree.root_node):
        if node.type != "class_definition":
            continue
        body = node.child_by_field_name("body")
        name_node = node.child_by_field_name("name")
        if body is None or name_node is None:
            continue
        model_qn = _python_class_qn(node)
        tablename = _class_assign_literal(body, "__tablename__")
        if tablename:  # SQLAlchemy declarative
            records.append(
                PersistenceRecord(
                    parsed.rel_path,
                    model_qn,
                    tablename,
                    "sqlalchemy",
                    "sqlalchemy",
                    parsed.language,
                    _row(node),
                    True,
                )
            )
            continue
        bases = _class_base_names(node)
        if "Model" in bases:  # Django model
            db_table = _django_meta_db_table(body)
            if db_table:
                records.append(
                    PersistenceRecord(
                        parsed.rel_path,
                        model_qn,
                        db_table,
                        "django",
                        "django",
                        parsed.language,
                        _row(node),
                        True,
                    )
                )
            else:
                records.append(
                    PersistenceRecord(
                        parsed.rel_path,
                        model_qn,
                        _text(name_node).lower(),
                        "django",
                        "django",
                        parsed.language,
                        _row(node),
                        False,
                    )
                )
    return records


# ---------------------------------------------------------------------------
# Java — JPA @Entity / @Table
# ---------------------------------------------------------------------------


def _java_annotations(node: Node) -> dict[str, Node]:
    """Map annotation name → its node, for a declaration's modifiers."""
    found: dict[str, Node] = {}
    for child in node.children:
        if child.type != "modifiers":
            continue
        for m in child.children:
            if m.type in ("annotation", "marker_annotation"):
                name = m.child_by_field_name("name")
                if name is not None:
                    found[_text(name)] = m
    return found


def _java_table_name(table_anno: Node) -> str | None:
    """The literal ``name="users"`` from an ``@Table(...)`` annotation, or ``None``."""
    args = table_anno.child_by_field_name("arguments")
    if args is None:
        return None
    for el in args.children:
        if el.type == "element_value_pair":
            key = el.child_by_field_name("key")
            val = el.child_by_field_name("value")
            if (
                key is not None
                and val is not None
                and _text(key) == "name"
                and val.type == "string_literal"
            ):
                return "".join(_text(c) for c in val.children if c.type == "string_fragment")
    return None


def _extract_java(parsed: ParsedFile) -> list[PersistenceRecord]:
    records: list[PersistenceRecord] = []
    for node in _iter(parsed.tree.root_node):
        if node.type != "class_declaration":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        annos = _java_annotations(node)
        if "Entity" not in annos:
            continue
        class_name = _text(name_node)
        table_anno = annos.get("Table")
        literal_name = _java_table_name(table_anno) if table_anno is not None else None
        if literal_name:
            records.append(
                PersistenceRecord(
                    parsed.rel_path,
                    class_name,
                    literal_name,
                    "jpa",
                    "jpa",
                    parsed.language,
                    _row(node),
                    True,
                )
            )
        else:
            records.append(
                PersistenceRecord(
                    parsed.rel_path,
                    class_name,
                    class_name,
                    "jpa",
                    "jpa",
                    parsed.language,
                    _row(node),
                    False,
                )
            )
    return records


_EXTRACTORS = {
    "python": _extract_python,
    "java": _extract_java,
}


def extract_persistence(parsed: ParsedFile) -> list[PersistenceRecord]:
    """Per-language ORM extraction. Empty for languages without a supported ORM
    shape. Sorted for determinism."""
    extractor = _EXTRACTORS.get(parsed.language)
    if extractor is None:
        return []
    records = extractor(parsed)
    records.sort(key=lambda r: (r.rel_path, r.model_qn_local, r.table_name, r.line))
    return records
