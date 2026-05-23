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
}


# --- extraction ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Tag:
    """One defined or referenced symbol located in a source file."""

    rel_path: str
    name: str
    kind: str  # "def" | "ref"
    category: str  # e.g. "class", "function", "type", "interface", "call"
    line: int  # 0-based start row
    language: str  # tree-sitter grammar of the source file (DEC-012)


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
            tags.append(
                Tag(
                    rel_path=parsed.rel_path,
                    name=node.text.decode("utf-8", "replace"),
                    kind=kind,
                    category=category,
                    line=_row(node),
                    language=parsed.language,
                )
            )

    tags.sort(key=lambda t: (t.line, t.kind, t.name))
    return tags
