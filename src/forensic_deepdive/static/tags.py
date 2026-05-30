"""Symbol extraction via Tree-sitter tag queries.

The ``.scm`` queries follow the ``tags.scm`` convention used by the tree-sitter
project, nvim-treesitter, and Aider: a capture named ``name.definition.<kind>``
marks where a symbol is *defined*, and ``name.reference.<kind>`` marks where one
is *used*. The queries here were authored against the grammars bundled in
``tree-sitter-language-pack`` 1.8.x (see the ``_fd_introspect`` AST dumps used
during development) and adapted from those public-domain / MIT / Apache-2.0
upstream ``tags.scm`` files. See NOTICE.

To add a language: add an entry to ``TAGS_SCM`` here and a matching extension to
``parse.LANG_BY_EXT``, then add a ``tests/fixtures/<lang>_sample/`` fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language

from forensic_deepdive.static.parse import ParsedFile

# --- tags.scm queries ------------------------------------------------------

# References capture bare-identifier calls only — NOT attribute/method calls
# (`obj.method()`). A method name belongs to the receiver's type, which
# name-based analysis cannot resolve; capturing it produces false edges (e.g.
# `digest.update()` colliding with an unrelated top-level `update`). See DEC-012.
_PYTHON_TAGS = """\
(class_definition
  name: (identifier) @name.definition.class) @definition.class

(function_definition
  name: (identifier) @name.definition.function) @definition.function

(call
  function: (identifier) @name.reference.call) @reference.call
"""

_C_TAGS = """\
(struct_specifier
  name: (type_identifier) @name.definition.class
  body: (field_declaration_list)) @definition.class

(enum_specifier
  name: (type_identifier) @name.definition.type) @definition.type

(type_definition
  declarator: (type_identifier) @name.definition.type) @definition.type

(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name.definition.function)) @definition.function

(declaration
  declarator: (function_declarator
    declarator: (identifier) @name.definition.function)) @definition.function

(call_expression
  function: (identifier) @name.reference.call) @reference.call
"""

# Dart's grammar exposes no clean "call" node — calls are an identifier followed
# by a separate `selector` sibling. We therefore capture every identifier as a
# reference; the defines-intersect-references step in graph.py filters the noise
# (only identifiers that are also defined somewhere create edges), and the
# definition's own name node is removed by the def/ref de-dup in extract_tags.
#
# DEC-012 follow-up (Omi finding #1/#2): the catch-all also picked up the
# method name in dotted calls (`obj.fromJson(json)` referenced `fromJson`),
# which produced false cross-file edges on common Dart names. The
# `_drop_method` capture marks identifiers inside an
# `unconditional_assignable_selector` (the `.foo` after a dot); the
# extractor honors the `_`-prefix convention and excludes those node ids
# from the reference set. Bare-call references (`foo()`, `Foo()`) are
# unaffected.
_DART_TAGS = """\
(class_definition
  name: (identifier) @name.definition.class) @definition.class

(function_signature
  name: (identifier) @name.definition.function) @definition.function

((identifier) @name.reference.call)

(unconditional_assignable_selector
  (identifier) @_drop_method)

(type_identifier) @name.reference.class
"""

_SWIFT_TAGS = """\
(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

(protocol_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

(function_declaration
  name: (simple_identifier) @name.definition.function) @definition.function

(call_expression
  (simple_identifier) @name.reference.call) @reference.call
"""

# --- DEC-020: TypeScript / JavaScript / Java / Go ---------------------------
#
# Each query follows the DEC-012 + Dart-fix precision discipline:
# - Capture bare-name call/reference targets only.
# - Mark dotted callees (`obj.foo()`, `Cls.foo()`) under `@_drop_*` so the
#   shared `_`-prefix-as-exclusion logic in `extract_tags()` removes them.
# - Capture constructor invocations (`new Greeter(...)`) so the class name
#   becomes a reference.

# TypeScript: covers `.ts` source. The `tsx` grammar (`.tsx`) reuses the
# same query — its node set is a JSX-aware superset of TypeScript's.
_TYPESCRIPT_TAGS = """\
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

(interface_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

(type_alias_declaration
  name: (type_identifier) @name.definition.type) @definition.type

(method_definition
  name: (property_identifier) @name.definition.method) @definition.method

(call_expression
  function: (identifier) @name.reference.call) @reference.call

(new_expression
  constructor: (identifier) @name.reference.class) @reference.class

; Dotted callees: `obj.method(...)` — drop the method name. The bare
; receiver identifier (`obj`) is still captured separately when it is itself
; a top-level reference.
(member_expression
  property: (property_identifier) @_drop_method)
"""

# JavaScript: same shape as TypeScript minus the type-system declarations.
# Treats `.js`, `.mjs`, `.cjs`, and `.jsx`.
_JAVASCRIPT_TAGS = """\
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(class_declaration
  name: (identifier) @name.definition.class) @definition.class

(method_definition
  name: (property_identifier) @name.definition.method) @definition.method

(call_expression
  function: (identifier) @name.reference.call) @reference.call

(new_expression
  constructor: (identifier) @name.reference.class) @reference.class

(member_expression
  property: (property_identifier) @_drop_method)
"""

# Java: method-invocation discrimination is the DEC-012 hotspot. Bare calls
# (`format(x)`) want to reference `format`; dotted calls (`Formatter.format(x)`)
# do not — they're routed through an object. We capture every
# method_invocation.name as a reference, then exclude those whose
# method_invocation node also has an `object:` field.
_JAVA_TAGS = """\
(class_declaration
  name: (identifier) @name.definition.class) @definition.class

(interface_declaration
  name: (identifier) @name.definition.interface) @definition.interface

(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

(method_declaration
  name: (identifier) @name.definition.method) @definition.method

(constructor_declaration
  name: (identifier) @name.definition.method) @definition.method

(method_invocation
  name: (identifier) @name.reference.call) @reference.call

(object_creation_expression
  type: (type_identifier) @name.reference.class) @reference.class

; Dotted method invocations (`Receiver.method(...)`) — drop the method name.
(method_invocation
  object: (_)
  name: (identifier) @_drop_method)

; Field accesses like `Receiver.field` shouldn't yield a `field` reference.
(field_access
  field: (identifier) @_drop_method)
"""

# Go: methods bind via receiver, so a bare-name reference is a top-level
# function. `selector_expression` is Go's `pkg.Foo` / `obj.Foo` — drop the
# right-hand identifier so `fmt.Println(...)` does not produce a `Println`
# reference.
_GO_TAGS = """\
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

(method_declaration
  name: (field_identifier) @name.definition.method) @definition.method

(type_spec
  name: (type_identifier) @name.definition.type) @definition.type

(call_expression
  function: (identifier) @name.reference.call) @reference.call

; Drop the right-hand side of any selector expression: pkg.Foo / obj.Foo.
(selector_expression
  field: (field_identifier) @_drop_method)
"""


# Rust (DEC-040, v0.3 Item D). Free functions, structs, traits, enums are
# definitions; `impl` methods are also `function_item` and become methods via
# the receiver-style parent binding in `_parent_chain` (the impl's `type:`
# field — non-lexical, like Go). Bare calls (`helper()`) reference; struct
# construction (`Greeter { .. }`) references the type. Dotted (`g.greet()`) and
# associated (`Greeter::new()`) calls are NOT captured here — they go through
# `method_calls.py` + the DEC-037 receiver resolver. `mod` and `macro_rules!`
# are not symbolized in v0.3 (namespaces / metaprogramming — deferred).
_RUST_TAGS = """\
(function_item
  name: (identifier) @name.definition.function) @definition.function

(struct_item
  name: (type_identifier) @name.definition.struct) @definition.struct

(trait_item
  name: (type_identifier) @name.definition.interface) @definition.interface

(enum_item
  name: (type_identifier) @name.definition.enum) @definition.enum

(call_expression
  function: (identifier) @name.reference.call) @reference.call

(struct_expression
  name: (type_identifier) @name.reference.class) @reference.class
"""


TAGS_SCM: dict[str, str] = {
    "python": _PYTHON_TAGS,
    "c": _C_TAGS,
    "dart": _DART_TAGS,
    "swift": _SWIFT_TAGS,
    # DEC-020
    "typescript": _TYPESCRIPT_TAGS,
    "tsx": _TYPESCRIPT_TAGS,  # tsx grammar accepts the same query as typescript
    "javascript": _JAVASCRIPT_TAGS,
    "java": _JAVA_TAGS,
    "go": _GO_TAGS,
    # DEC-040
    "rust": _RUST_TAGS,
}


# --- extraction ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Tag:
    """One defined or referenced symbol located in a source file.

    DEC-023: for definition tags, ``parent`` is the dotted chain of enclosing
    parent definitions (outermost-to-innermost), e.g. ``"Outer.Inner"`` for a
    method ``method`` nested in ``Outer.Inner``. Empty string for top-level
    definitions and for reference tags.

    DEC-025: for reference tags, ``enclosing_scope`` is the dotted
    qualified-local name of the nearest enclosing named function / method
    / class — i.e. the *caller's* qn_local. A bare-call ``foo()`` inside
    ``class Greeter > def greet`` has ``enclosing_scope="Greeter.greet"``.
    Empty for refs at module-level scope. Empty for definition tags.
    """

    rel_path: str
    name: str
    kind: str  # "def" | "ref"
    category: str  # e.g. "class", "function", "type", "interface", "call"
    line: int  # 0-based start row
    language: str  # tree-sitter grammar of the source file (DEC-012)
    parent: str = ""  # dotted parent-definition chain (DEC-023)
    enclosing_scope: str = ""  # dotted qn_local of enclosing caller (DEC-025)


# DEC-023 — node types that count as "parent definitions" for the walk-up
# pass. A method/field/inner-class's qualified name prepends the names of
# every ancestor of one of these types. The set is intentionally per-language
# (not language-family) because grammar names diverge.
#
# Go is special: methods don't lexically nest in their type — they bind via
# a receiver parameter list. ``_parent_chain`` special-cases it; the entry
# stays empty here.
_PARENT_DEF_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"class_definition"}),
    "c": frozenset(),  # no methods / nested types worth chaining in v0.2
    "dart": frozenset({"class_definition", "mixin_declaration", "extension_declaration"}),
    "swift": frozenset(
        {
            "class_declaration",
            "protocol_declaration",
            "struct_declaration",
            "enum_declaration",
        }
    ),
    "typescript": frozenset({"class_declaration", "interface_declaration"}),
    "tsx": frozenset({"class_declaration", "interface_declaration"}),
    "javascript": frozenset({"class_declaration"}),
    "java": frozenset({"class_declaration", "interface_declaration", "enum_declaration"}),
    "go": frozenset(),  # see Go branch in _parent_chain
    "rust": frozenset(),  # see Rust branch in _parent_chain (impl/trait binding)
}

# DEC-025 — node types that count as "enclosing scopes" for a reference.
# A ref inside one of these ancestors has the ancestor as its caller. The
# walk-up looks for the NEAREST such ancestor and skips intermediate
# anonymous functions (arrow_function, lambda, function_expression,
# function_literal, etc.) so calls inside an inline closure attribute to
# the outer named function.
#
# Includes parent-def types because a ref at class-body scope (e.g.
# Python ``class Foo: x = bar()``) is genuinely scoped to the class —
# the class body executes at class-definition time and bar() is part of
# that execution.
_SCOPE_DEF_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"function_definition", "class_definition"}),
    "c": frozenset({"function_definition"}),
    # Dart's function_body is the AST sibling of its function_signature
    # (NOT a child), so refs inside the body never walk up to the
    # signature. Including ``function_body`` here lets the walker stop
    # there; ``_scope_name_node`` then bridges to the preceding signature.
    "dart": frozenset(
        {"function_signature", "method_signature", "class_definition", "function_body"}
    ),
    "swift": frozenset(
        {
            "function_declaration",
            "class_declaration",
            "protocol_declaration",
            "struct_declaration",
            "enum_declaration",
        }
    ),
    "typescript": frozenset(
        {
            "function_declaration",
            "method_definition",
            "class_declaration",
            "interface_declaration",
        }
    ),
    "tsx": frozenset(
        {
            "function_declaration",
            "method_definition",
            "class_declaration",
            "interface_declaration",
        }
    ),
    "javascript": frozenset({"function_declaration", "method_definition", "class_declaration"}),
    "java": frozenset(
        {
            "method_declaration",
            "constructor_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
        }
    ),
    "go": frozenset({"function_declaration", "method_declaration"}),
    # Rust: refs live inside `function_item` bodies (free fns + impl methods).
    "rust": frozenset({"function_item"}),
}


@cache
def _query_for(language: str) -> Query | None:
    """Return a cached compiled tag query for *language*, or None if absent."""
    scm = TAGS_SCM.get(language)
    if scm is None:
        return None
    return Query(get_language(language), scm)


def _row(node: Node) -> int:
    """Return the 0-based start row of *node* (handles Point or tuple)."""
    point = node.start_point
    return point.row if hasattr(point, "row") else point[0]


def _go_method_receiver_type(method_decl: Node) -> str:
    """Read the receiver-type name from a Go ``method_declaration``.

    Go method shape::

        method_declaration
          parameter_list             ← receiver list (always the FIRST one)
            parameter_declaration
              identifier             ← receiver var (g)
              [pointer_type            ← optional
                type_identifier]    ← the parent type
              type_identifier        ← also valid (value receiver)
          field_identifier           ← method name
          parameter_list             ← actual parameters
          ...

    Returns the parent type's name (``"Greeter"`` for either
    ``func (g *Greeter) M()`` or ``func (g Greeter) M()``), or empty string
    if the receiver shape is unfamiliar.
    """
    for child in method_decl.children:
        if child.type != "parameter_list":
            continue
        # First parameter_list is the receiver.
        for param in child.children:
            if param.type != "parameter_declaration":
                continue
            for grandchild in param.children:
                if grandchild.type == "type_identifier":
                    return grandchild.text.decode("utf-8", "replace")
                if grandchild.type == "pointer_type":
                    for ggc in grandchild.children:
                        if ggc.type == "type_identifier":
                            return ggc.text.decode("utf-8", "replace")
        return ""
    return ""


def _scope_name_node(scope_node: Node, language: str) -> Node | None:
    """Return the identifier node holding the *name* of a scope-defining
    AST node. Most languages use the ``name:`` field, but several
    require per-language bridging:

    * **C** — ``function_definition``'s name is nested inside
      ``function_declarator``; walk in through nested declarators until
      we hit the identifier. Pointer-returning functions wrap with
      ``pointer_declarator``.
    * **Dart** — ``function_body`` (which IS in the walked-up chain) is
      the AST *sibling* of its ``function_signature`` (which holds the
      name). Bridge by stepping to the preceding signature.
    """
    if language == "c" and scope_node.type == "function_definition":
        decl = scope_node.child_by_field_name("declarator")
        while decl is not None:
            if decl.type == "identifier":
                return decl
            decl = decl.child_by_field_name("declarator")
        return None

    if language == "dart" and scope_node.type == "function_body":
        # Look at the function_body's preceding siblings for a signature.
        sibling = scope_node.prev_sibling
        while sibling is not None:
            if sibling.type in ("function_signature", "method_signature"):
                # method_signature wraps function_signature, which holds
                # the identifier under field ``name`` (or as a direct
                # ``identifier`` child).
                sig = sibling
                if sig.type == "method_signature":
                    for c in sig.children:
                        if c.type == "function_signature":
                            sig = c
                            break
                name_node = sig.child_by_field_name("name")
                if name_node is not None:
                    return name_node
                for c in sig.children:
                    if c.type == "identifier":
                        return c
                return None
            sibling = sibling.prev_sibling
        return None

    return scope_node.child_by_field_name("name")


def _enclosing_scope_qn(ref_node: Node, language: str) -> str:
    """Return the dotted qn_local of the nearest enclosing named scope
    that contains *ref_node* (DEC-025).

    Walks up from the ref's node looking for the FIRST ancestor whose
    type is in ``_SCOPE_DEF_TYPES[language]`` AND has an identifiable
    name. Anonymous scopes (arrow_function, function_expression,
    lambda_expression, function_literal) are skipped — calls inside an
    inline closure attribute to the outer named function.

    For the found scope node, returns ``f"{parent_chain}.{name}"`` —
    using :func:`_parent_chain` to compose the dotted qn so a method's
    enclosing scope is ``Class.method``, a nested class's class-body
    ref is ``Outer.Inner``, and a Go method gets its receiver type
    prepended.

    Returns ``""`` for refs at module-level scope (no enclosing named
    function/class found).
    """
    scope_types = _SCOPE_DEF_TYPES.get(language, frozenset())
    if not scope_types:
        return ""

    ancestor = ref_node.parent
    while ancestor is not None:
        if ancestor.type in scope_types:
            name_node = _scope_name_node(ancestor, language)
            if name_node is None:
                # Anonymous / unnamed — keep walking up.
                ancestor = ancestor.parent
                continue
            scope_name = name_node.text.decode("utf-8", "replace")
            # _parent_chain handles Go's receiver-based binding too — for
            # a method_declaration's name_node, it walks up to the
            # method_declaration and reads the receiver type.
            chain = _parent_chain(name_node, language)
            return f"{chain}.{scope_name}" if chain else scope_name
        ancestor = ancestor.parent
    return ""


def _parent_chain(name_node: Node, language: str) -> str:
    """Return the dotted parent-definition chain for *name_node* (DEC-023).

    For Go methods, reads the receiver type — the only language whose
    method-to-type binding is non-lexical. For every other language, walks
    up ``node.parent`` collecting names of enclosing nodes whose type is in
    ``_PARENT_DEF_TYPES[language]``. The walk collects innermost-first;
    the returned string is outermost-to-innermost joined by ``.``.

    Returns ``""`` for top-level definitions, for unsupported languages
    (``_PARENT_DEF_TYPES`` empty), and when the walk-up never hits a parent
    definition.
    """
    if language == "go":
        ancestor = name_node.parent
        while ancestor is not None:
            if ancestor.type == "method_declaration":
                return _go_method_receiver_type(ancestor)
            ancestor = ancestor.parent
        return ""

    if language == "rust":
        # Rust methods bind non-lexically: a `function_item` inside an
        # `impl_item` belongs to the impl's `type:` field (e.g. `impl Greeter`),
        # and `impl Trait for Greeter` still binds methods to `Greeter`. A
        # `function_signature_item` inside a `trait_item` binds to the trait
        # name. Walk up to the nearest such binder and read its type/name.
        ancestor = name_node.parent
        while ancestor is not None:
            if ancestor.type == "impl_item":
                type_node = ancestor.child_by_field_name("type")
                return type_node.text.decode("utf-8", "replace") if type_node is not None else ""
            if ancestor.type == "trait_item":
                name_field = ancestor.child_by_field_name("name")
                if name_field is not None and name_field.id != name_node.id:
                    return name_field.text.decode("utf-8", "replace")
            ancestor = ancestor.parent
        return ""

    parent_types = _PARENT_DEF_TYPES.get(language, frozenset())
    if not parent_types:
        return ""
    chain: list[str] = []
    ancestor = name_node.parent
    while ancestor is not None:
        if ancestor.type in parent_types:
            name_field = ancestor.child_by_field_name("name")
            # Skip the ancestor whose ``name:`` field IS the node we started
            # from — that ancestor IS the definition we're naming, not its
            # parent. A class's own identifier must not show the class as
            # its own parent.
            if name_field is not None and name_field.id != name_node.id:
                chain.append(name_field.text.decode("utf-8", "replace"))
        ancestor = ancestor.parent
    chain.reverse()
    return ".".join(chain)


def extract_tags(parsed: ParsedFile) -> list[Tag]:
    """Extract definition/reference tags from a parsed file.

    Returns an empty list for languages without a tag query. Tags are sorted by
    line for deterministic, golden-file-friendly output.
    """
    query = _query_for(parsed.language)
    if query is None:
        return []

    captures = QueryCursor(query).captures(parsed.tree.root_node)

    # Node ids that must NOT become references, for two reasons:
    # * A definition's own name node is often re-captured by a broad reference
    #   pattern (notably Dart's catch-all identifier rule); drop those so a
    #   symbol does not reference itself.
    # * Any capture whose name begins with ``_`` is treated as an exclusion
    #   set — a language query can mark "this looked like a reference, but it
    #   is not" by capturing the node under e.g. ``@_drop_method``. This is
    #   how Dart's dotted-call method names (``obj.foo()`` → ``foo``) are
    #   filtered out of the reference set (DEC-012 follow-up, Omi #1/#2).
    excluded_ref_node_ids: set[int] = set()
    for capture_name, nodes in captures.items():
        if capture_name.startswith("name.definition.") or capture_name.startswith("_"):
            excluded_ref_node_ids.update(node.id for node in nodes)

    tags: list[Tag] = []
    seen: set[tuple[str, int]] = set()
    for capture_name, nodes in captures.items():
        parts = capture_name.split(".")
        # Only the `name.*` captures pin the identifier; the bare
        # `@definition.*` / `@reference.*` captures mark the enclosing node.
        # Helper `_`-prefixed captures are pure metadata and never tagged.
        if len(parts) != 3 or parts[0] != "name":
            continue
        kind = "def" if parts[1] == "definition" else "ref"
        category = parts[2]
        for node in nodes:
            if kind == "ref" and node.id in excluded_ref_node_ids:
                continue
            key = (capture_name, node.id)
            if key in seen:
                continue
            seen.add(key)
            # DEC-023: definitions carry their dotted parent chain so the
            # graph build phase can write correct qualified names and
            # MEMBER_OF edges.
            # DEC-025: references carry the enclosing-scope qn_local so
            # the CALLS resolver can attribute the call to the right
            # caller Symbol.
            if kind == "def":
                parent = _parent_chain(node, parsed.language)
                enclosing_scope = ""
            else:
                parent = ""
                enclosing_scope = _enclosing_scope_qn(node, parsed.language)
            tags.append(
                Tag(
                    rel_path=parsed.rel_path,
                    name=node.text.decode("utf-8", "replace"),
                    kind=kind,
                    category=category,
                    line=_row(node),
                    language=parsed.language,
                    parent=parent,
                    enclosing_scope=enclosing_scope,
                )
            )

    tags.sort(key=lambda t: (t.line, t.kind, t.name, t.parent))
    return tags
