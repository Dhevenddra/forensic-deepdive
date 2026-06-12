"""Dependency-injection extraction (DEC-059, v0.5 Step 4 — the DI tail).

A sibling to :mod:`forensic_deepdive.static.inheritance`: it walks a parsed file and
emits one :class:`InjectionRecord` per injection site. The build phase resolves the
raw ``injected_type_name`` to an intra-repo Symbol using the same same-file → import
→ cross-file ladder inheritance uses, then applies the **Spring resolution ladder**
(DEC-059): a concrete type → EXTRACTED ``INJECTS``; an interface with exactly one
intra-repo implementation → INFERRED (resolved to the impl); an interface with
several impls → AMBIGUOUS-all (one ``INJECTS`` per candidate, mirroring Spring's
``NoUniqueBeanDefinitionException`` fail-closed posture).

Shapes (research §4):
- **Spring (Java)** — ``@Autowired`` field; constructor injection on a class with a
  Spring stereotype (``@Service``/``@Component``/``@Repository``/``@Controller``/
  ``@RestController``/``@Configuration``) or an ``@Autowired`` constructor (Spring
  auto-wires the single public ctor).
- **FastAPI (Python)** — ``def handler(db = Depends(get_db))`` and
  ``Annotated[T, Depends(get_db)]`` — the provider callable is the injected Symbol.

Deferred (DEC-059): NestJS/Angular/Guice/Dagger; ``@Qualifier``/``@Primary``
disambiguation (multi-impl stays AMBIGUOUS-all); ``@Configuration``/``@Bean`` factory
providers; the ``PROVIDES`` inverse edge (redundant with IMPLEMENTS / the resolved
INJECTS — it adds no new traceability).
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from forensic_deepdive.static.parse import ParsedFile

# Java class-level annotations that make a constructor's params auto-wired.
_SPRING_STEREOTYPES = frozenset(
    {"Component", "Service", "Repository", "Controller", "RestController", "Configuration"}
)


@dataclass(frozen=True, slots=True)
class InjectionRecord:
    """One injection site. ``injector_qn_local`` is the dotted local qn of the
    class (Spring) or function (FastAPI) that depends on ``injected_type_name``
    (the raw type/provider name as written — resolved to a Symbol at build time)."""

    rel_path: str
    injector_qn_local: str
    injected_type_name: str
    kind: str  # "autowired-field" | "ctor" | "depends"
    language: str
    line: int


def _row(node: Node) -> int:
    point = node.start_point
    return point.row if hasattr(point, "row") else point[0]


def _text(node: Node) -> str:
    return node.text.decode("utf-8", "replace")


def _rightmost_type_name(node: Node) -> str | None:
    """The resolvable name of a type node: ``OwnerRepository`` from a
    ``type_identifier``; the base of a ``generic_type`` (``List<Owner>`` → ``List``,
    not useful but harmless); the rightmost segment of a ``scoped_type_identifier``
    (``a.b.Owner`` → ``Owner``). ``None`` for primitives/unhandled shapes."""
    t = node.type
    if t == "type_identifier":
        return _text(node)
    if t == "generic_type":
        for c in node.children:
            if c.type in ("type_identifier", "scoped_type_identifier"):
                return _rightmost_type_name(c)
        return None
    if t == "scoped_type_identifier":
        last = None
        for c in node.children:
            if c.type == "type_identifier":
                last = c
        return _text(last) if last is not None else None
    return None


# ---------------------------------------------------------------------------
# Python — FastAPI Depends
# ---------------------------------------------------------------------------


def _python_fn_qn(node: Node) -> str:
    """Dotted qn_local of a Python ``function_definition`` (enclosing classes +
    the function name), matching the DEC-023 def-Tag convention."""
    chain: list[str] = []
    cur: Node | None = node
    while cur is not None:
        if cur.type in ("class_definition", "function_definition"):
            name_node = cur.child_by_field_name("name")
            if name_node is not None:
                chain.append(_text(name_node))
        cur = cur.parent
    chain.reverse()
    return ".".join(chain)


def _depends_provider(value: Node) -> str | None:
    """The provider name inside a ``Depends(get_db)`` call, or ``None``. Accepts a
    bare ``Depends(...)`` call and the ``Annotated[T, Depends(...)]`` form."""

    def from_call(call: Node) -> str | None:
        fn = call.child_by_field_name("function")
        if fn is None:
            return None
        fn_name = fn if fn.type == "identifier" else fn.child_by_field_name("attribute")
        if fn_name is None or _text(fn_name) != "Depends":
            return None
        args = call.child_by_field_name("arguments")
        if args is None:
            return None
        for arg in args.children:
            if arg.type == "identifier":
                return _text(arg)
            if arg.type == "attribute":  # module.get_db → rightmost
                attr = arg.child_by_field_name("attribute")
                return _text(attr) if attr is not None else None
        return None

    if value.type == "call":
        got = from_call(value)
        if got is not None:
            return got
    # Annotated[T, Depends(...)] (or a ``type``-wrapped generic) → find the inner
    # Depends call anywhere under this node.
    for desc in _iter(value):
        if desc.type == "call":
            got = from_call(desc)
            if got is not None:
                return got
    return None


def _iter(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def _extract_python(parsed: ParsedFile) -> list[InjectionRecord]:
    records: list[InjectionRecord] = []
    for node in _iter(parsed.tree.root_node):
        if node.type != "function_definition":
            continue
        params = node.child_by_field_name("parameters")
        if params is None:
            continue
        injector = _python_fn_qn(node)
        seen: set[str] = set()
        for param in params.children:
            # ``db = Depends(get_db)`` / ``db: T = Depends(get_db)`` — the default value.
            value = (
                param.child_by_field_name("value")
                if param.type in ("default_parameter", "typed_default_parameter")
                else None
            )
            # ``db: Annotated[T, Depends(get_db)]`` — the type annotation.
            type_node = (
                param.child_by_field_name("type")
                if param.type in ("typed_parameter", "typed_default_parameter")
                else None
            )
            for candidate in (value, type_node):
                if candidate is None:
                    continue
                provider = _depends_provider(candidate)
                if provider is not None and provider not in seen:
                    seen.add(provider)
                    records.append(
                        InjectionRecord(
                            rel_path=parsed.rel_path,
                            injector_qn_local=injector,
                            injected_type_name=provider,
                            kind="depends",
                            language=parsed.language,
                            line=_row(node),
                        )
                    )
    return records


# ---------------------------------------------------------------------------
# Java — Spring @Autowired field + constructor injection
# ---------------------------------------------------------------------------


def _java_annotation_names(node: Node) -> set[str]:
    """Annotation names (``Autowired``/``Service``…) on a declaration's modifiers."""
    names: set[str] = set()
    for child in node.children:
        if child.type != "modifiers":
            continue
        for m in child.children:
            if m.type in ("annotation", "marker_annotation"):
                name = m.child_by_field_name("name")
                if name is not None:
                    names.add(_text(name))
    return names


def _extract_java(parsed: ParsedFile) -> list[InjectionRecord]:
    records: list[InjectionRecord] = []
    for node in _iter(parsed.tree.root_node):
        if node.type != "class_declaration":
            continue
        name_node = node.child_by_field_name("name")
        body = node.child_by_field_name("body")
        if name_node is None or body is None:
            continue
        class_name = _text(name_node)
        is_stereotype = bool(_java_annotation_names(node) & _SPRING_STEREOTYPES)
        for member in body.children:
            # @Autowired field injection.
            if member.type == "field_declaration" and "Autowired" in _java_annotation_names(member):
                type_node = member.child_by_field_name("type")
                tname = _rightmost_type_name(type_node) if type_node is not None else None
                if tname is not None:
                    records.append(
                        InjectionRecord(
                            parsed.rel_path,
                            class_name,
                            tname,
                            "autowired-field",
                            parsed.language,
                            _row(member),
                        )
                    )
            # Constructor injection (stereotype class or @Autowired ctor).
            elif member.type == "constructor_declaration" and (
                is_stereotype or "Autowired" in _java_annotation_names(member)
            ):
                ctor_params = member.child_by_field_name("parameters")
                if ctor_params is None:
                    continue
                for p in ctor_params.children:
                    if p.type != "formal_parameter":
                        continue
                    type_node = p.child_by_field_name("type")
                    tname = _rightmost_type_name(type_node) if type_node is not None else None
                    if tname is not None:
                        records.append(
                            InjectionRecord(
                                parsed.rel_path,
                                class_name,
                                tname,
                                "ctor",
                                parsed.language,
                                _row(member),
                            )
                        )
    return records


_EXTRACTORS = {
    "python": _extract_python,
    "java": _extract_java,
}


def extract_injection(parsed: ParsedFile) -> list[InjectionRecord]:
    """Per-language DI extraction. Empty for languages without a supported DI
    shape. Sorted for determinism."""
    extractor = _EXTRACTORS.get(parsed.language)
    if extractor is None:
        return []
    records = extractor(parsed)
    records.sort(
        key=lambda r: (r.rel_path, r.injector_qn_local, r.injected_type_name, r.kind, r.line)
    )
    return records
