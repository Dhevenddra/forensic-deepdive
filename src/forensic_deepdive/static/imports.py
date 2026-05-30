"""Per-language import extraction (DEC-024, REMAINING.md item 8b step 2).

Each language has its own AST shape for ``import`` (and Python / JS have
several shapes per language). Rather than hand-roll one Tree-sitter query
per language to express every form, we capture import-statement nodes via
a simple walk and decode their structure in Python — much more
maintainable than fighting Tree-sitter query predicates for things like
``from X import Y as A, Z``.

The :class:`Import` dataclass is the output unit. One per source-level
``import`` / ``from … import …`` / ``#include`` / ``require(…)`` /
``library_import`` / etc.

Module-path normalization (per language):
- **Python** — dotted name (``os.path``) or relative form (``.``, ``.pkg``).
- **TypeScript / TSX / JavaScript** — the bare string contents (``./y``,
  ``react``). Includes ``require('./y')`` for legacy CommonJS.
- **Java** — fully-qualified dotted name (``java.util.List``,
  ``java.util.*`` preserved as ``java.util.*``).
- **Go** — the quoted string contents (``fmt``, ``log/slog``).
- **Dart** — the URI contents (``package:foo/bar.dart``,
  ``dart:io``, ``./local.dart``). ``export`` statements are *also*
  captured as imports — both create a File→Module dependency.
- **Swift** — dotted name (``Foundation``, ``Foo.Bar``).
- **C** — include path. Local ``"foo.h"`` → ``foo.h``; system
  ``<stdio.h>`` → ``<stdio.h>`` (angle brackets preserved so consumers
  can distinguish system from project).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tree_sitter import Node

from forensic_deepdive.static.parse import ParsedFile


@dataclass(frozen=True, slots=True)
class ImportedName:
    """One symbol imported via ``from X import name`` / ``import {name}``
    / ``import { name as alias }``. ``alias`` is empty when there is none."""

    name: str
    alias: str = ""


@dataclass(frozen=True, slots=True)
class Import:
    """One import / include / require statement.

    Fields:
        rel_path: importing file's repo-relative posix path.
        module_path: normalized module path (see module-level doc).
        language: tree-sitter grammar id.
        line: 0-based start row of the statement.
        module_alias: for ``import X as A`` (Python) / ``import * as Y``
            (TS / JS) / ``import './x' as ns`` (Dart). Empty otherwise.
        imported_names: for ``from X import a, b as B`` (Python) and
            ``import { Z, W as A } from "./y"`` (TS / JS). Empty for
            plain ``import X`` / ``import {default}`` forms.
        is_reexport: True for Dart ``export 'pkg/y.dart';``. Treated as
            an IMPORTS edge in v0.2 but flagged so v0.3 can distinguish.
    """

    rel_path: str
    module_path: str
    language: str
    line: int
    module_alias: str = ""
    imported_names: tuple[ImportedName, ...] = ()
    is_reexport: bool = False


# ---------------------------------------------------------------------------
# Per-language node-type set: walk the tree and dispatch on these.
# ---------------------------------------------------------------------------

_IMPORT_NODE_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"import_statement", "import_from_statement"}),
    "typescript": frozenset({"import_statement"}),
    "tsx": frozenset({"import_statement"}),
    "javascript": frozenset({"import_statement"}),  # plus require() (handled separately)
    "java": frozenset({"import_declaration"}),
    "go": frozenset({"import_declaration"}),
    "dart": frozenset({"library_import", "library_export"}),
    "swift": frozenset({"import_declaration"}),
    "c": frozenset({"preproc_include"}),
    "rust": frozenset({"use_declaration"}),  # DEC-040
}


def _row(node: Node) -> int:
    point = node.start_point
    return point.row if hasattr(point, "row") else point[0]


def _text(node: Node) -> str:
    return node.text.decode("utf-8", "replace")


def _strip_quotes(s: str) -> str:
    """Strip a single pair of leading/trailing string-quote characters."""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"', "`"):
        return s[1:-1]
    return s


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def _extract_python_import(rel_path: str, language: str, node: Node) -> list[Import]:
    line = _row(node)
    if node.type == "import_statement":
        # `import a, b as B, c.d`. Children after `import` are either
        # `dotted_name` or `aliased_import`.
        results: list[Import] = []
        for child in node.children:
            if child.type == "dotted_name":
                results.append(
                    Import(
                        rel_path=rel_path,
                        module_path=_text(child),
                        language=language,
                        line=line,
                    )
                )
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                alias = child.child_by_field_name("alias")
                results.append(
                    Import(
                        rel_path=rel_path,
                        module_path=_text(name) if name is not None else "",
                        language=language,
                        line=line,
                        module_alias=_text(alias) if alias is not None else "",
                    )
                )
        return results

    # import_from_statement: `from M import a, b as B`
    module_node = node.child_by_field_name("module_name")
    if module_node is None:
        return []
    module = _text(module_node)
    # Imported names come after the `import` keyword. Each is either a
    # `dotted_name` (`a`) or an `aliased_import` (`b as B`). A bare `*`
    # appears as `wildcard_import` for `from X import *`.
    names: list[ImportedName] = []
    seen_import_kw = False
    for child in node.children:
        if child.type == "import":
            seen_import_kw = True
            continue
        if not seen_import_kw:
            continue
        if child.type == "dotted_name":
            names.append(ImportedName(name=_text(child)))
        elif child.type == "aliased_import":
            n = child.child_by_field_name("name")
            a = child.child_by_field_name("alias")
            names.append(
                ImportedName(
                    name=_text(n) if n is not None else "",
                    alias=_text(a) if a is not None else "",
                )
            )
        elif child.type == "wildcard_import":
            names.append(ImportedName(name="*"))
    return [
        Import(
            rel_path=rel_path,
            module_path=module,
            language=language,
            line=line,
            imported_names=tuple(names),
        )
    ]


# ---------------------------------------------------------------------------
# TypeScript / TSX / JavaScript
# ---------------------------------------------------------------------------


def _extract_ts_js_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handles ``import_statement`` for both TS/TSX and JS. JS's
    ``require('x')`` is covered by the second-pass walk in
    :func:`extract_imports`."""
    line = _row(node)
    # The module path lives on the trailing `string` node.
    module = ""
    for child in node.children:
        if child.type == "string":
            module = _strip_quotes(_text(child))
            break
    if not module:
        return []

    # Find the optional import_clause to extract named imports / alias.
    module_alias = ""
    imported_names: list[ImportedName] = []
    for child in node.children:
        if child.type != "import_clause":
            continue
        for clause_child in child.children:
            if clause_child.type == "identifier":
                # `import Y from "./y"` — default import binds to Y.
                imported_names.append(ImportedName(name="default", alias=_text(clause_child)))
            elif clause_child.type == "namespace_import":
                # `import * as Y from "./y"`
                for nic in clause_child.children:
                    if nic.type == "identifier":
                        module_alias = _text(nic)
            elif clause_child.type == "named_imports":
                # `import { Z, W as A } from "./y"`
                for spec in clause_child.children:
                    if spec.type != "import_specifier":
                        continue
                    name_node = spec.child_by_field_name("name")
                    alias_node = spec.child_by_field_name("alias")
                    if name_node is None:
                        # Fall back to first identifier child.
                        for sc in spec.children:
                            if sc.type == "identifier":
                                name_node = sc
                                break
                    if name_node is not None:
                        imported_names.append(
                            ImportedName(
                                name=_text(name_node),
                                alias=_text(alias_node) if alias_node is not None else "",
                            )
                        )
        break  # one import_clause per statement

    return [
        Import(
            rel_path=rel_path,
            module_path=module,
            language=language,
            line=line,
            module_alias=module_alias,
            imported_names=tuple(imported_names),
        )
    ]


def _extract_js_require_call(rel_path: str, language: str, node: Node) -> list[Import]:
    """Recognize ``require('./y')`` as a CommonJS import."""
    # Shape: call_expression > [function: identifier 'require'] + [arguments: ('./y')]
    func = node.child_by_field_name("function")
    if func is None or func.type != "identifier" or _text(func) != "require":
        return []
    args = node.child_by_field_name("arguments")
    if args is None:
        return []
    for child in args.children:
        if child.type == "string":
            module = _strip_quotes(_text(child))
            if module:
                return [
                    Import(
                        rel_path=rel_path,
                        module_path=module,
                        language=language,
                        line=_row(node),
                    )
                ]
    return []


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------


def _extract_java_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handles ``import pkg.Class;``, ``import pkg.*;``, ``import static
    pkg.Class.MEMBER;``.

    Java imports embed the imported name in the dotted path itself —
    ``import com.x.Helper`` names exactly the symbol ``Helper``. We
    surface that in ``imported_names`` so the resolver can mark these
    EXTRACTED rather than falling through to the whole-module branch
    (which would be INFERRED).
    """
    line = _row(node)
    # The path is a scoped_identifier. ``import pkg.*`` puts the scoped_id
    # for the package and a separate `asterisk` sibling.
    scoped = None
    has_asterisk = False
    for child in node.children:
        if child.type == "scoped_identifier":
            scoped = child
        elif child.type == "asterisk":
            has_asterisk = True
    if scoped is None:
        return []
    module = _text(scoped)
    if has_asterisk:
        return [
            Import(
                rel_path=rel_path,
                module_path=module + ".*",
                language=language,
                line=line,
                imported_names=(ImportedName(name="*"),),
            )
        ]
    # `import pkg.Class` -> imported_names=[Class].
    # `import static pkg.Class.MEMBER` -> imported_names=[MEMBER].
    imported_name = module.rsplit(".", 1)[-1]
    return [
        Import(
            rel_path=rel_path,
            module_path=module,
            language=language,
            line=line,
            imported_names=(ImportedName(name=imported_name),),
        )
    ]


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------


def _extract_go_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Go's ``import "x"`` and grouped ``import (\n "a"\n alias "b"\n)``.
    Each ``import_spec`` produces one Import — the spec may carry an
    alias (``log "log/slog"``) or a blank-identifier side-effect import
    (``_ "side"``)."""
    line = _row(node)
    results: list[Import] = []

    def _emit_spec(spec: Node) -> None:
        module = ""
        alias = ""
        for child in spec.children:
            if child.type == "interpreted_string_literal":
                # Strip the surrounding quote chars.
                module = _strip_quotes(_text(child))
            elif child.type == "package_identifier":
                alias = _text(child)
            elif child.type == "blank_identifier":
                alias = "_"
        if module:
            results.append(
                Import(
                    rel_path=rel_path,
                    module_path=module,
                    language=language,
                    line=_row(spec),
                    module_alias=alias,
                )
            )

    for child in node.children:
        if child.type == "import_spec":
            _emit_spec(child)
        elif child.type == "import_spec_list":
            for sub in child.children:
                if sub.type == "import_spec":
                    _emit_spec(sub)
    # If we found no specs but had at least one child (rare), keep an empty
    # statement-level Import so call sites still see "an import happened".
    if not results:
        results.append(Import(rel_path=rel_path, module_path="", language=language, line=line))
        results.pop()  # actually no — silently drop malformed
    return results


# ---------------------------------------------------------------------------
# Dart
# ---------------------------------------------------------------------------


def _extract_dart_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handles Dart's ``library_import`` and ``library_export``. The URI
    lives under ``configurable_uri > uri > string_literal``; aliases via
    ``as`` come as a sibling ``identifier``."""
    line = _row(node)
    is_reexport = node.type == "library_export"

    uri_text = ""
    alias = ""
    # library_import → import_specification → ... ;  for imports;
    # library_export keeps a flatter shape.
    # Walk recursively for the configurable_uri.
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur.type == "configurable_uri":
            for sub in cur.children:
                if sub.type == "uri":
                    for s in sub.children:
                        if s.type == "string_literal":
                            uri_text = _strip_quotes(_text(s))
                            break
            break
        stack.extend(cur.children)

    # Find an alias if present. The `as <identifier>` pattern lives at
    # the import_specification level alongside the configurable_uri.
    spec = node
    for child in node.children:
        if child.type == "import_specification":
            spec = child
            break
    saw_as = False
    for child in spec.children:
        if child.type == "as":
            saw_as = True
            continue
        if saw_as and child.type == "identifier":
            alias = _text(child)
            break

    if not uri_text:
        return []
    return [
        Import(
            rel_path=rel_path,
            module_path=uri_text,
            language=language,
            line=line,
            module_alias=alias,
            is_reexport=is_reexport,
        )
    ]


# ---------------------------------------------------------------------------
# Swift
# ---------------------------------------------------------------------------


def _extract_swift_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handles ``import Foundation``, ``import struct Foo.Bar``,
    ``@testable import Foo``. The ``identifier`` child carries the module
    name as a dotted form."""
    line = _row(node)
    for child in node.children:
        if child.type == "identifier":
            # The identifier may itself contain simple_identifier dots
            # (``Foo.Bar``). The raw text is the right shape.
            module = _text(child)
            if module:
                return [
                    Import(
                        rel_path=rel_path,
                        module_path=module,
                        language=language,
                        line=line,
                    )
                ]
    return []


# ---------------------------------------------------------------------------
# C
# ---------------------------------------------------------------------------


def _extract_c_include(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handles ``#include "x"`` (local) and ``#include <x>`` (system)."""
    line = _row(node)
    for child in node.children:
        if child.type == "string_literal":
            # `#include "foo.h"` — strip quotes.
            module = _strip_quotes(_text(child))
            if module:
                return [
                    Import(
                        rel_path=rel_path,
                        module_path=module,
                        language=language,
                        line=line,
                    )
                ]
        elif child.type == "system_lib_string":
            # `#include <stdio.h>` — keep the angle brackets so consumers
            # can distinguish system from project headers without a
            # separate flag.
            return [
                Import(
                    rel_path=rel_path,
                    module_path=_text(child),
                    language=language,
                    line=line,
                )
            ]
    return []


# ---------------------------------------------------------------------------
# Rust (DEC-040)
# ---------------------------------------------------------------------------


def _extract_rust_import(rel_path: str, language: str, node: Node) -> list[Import]:
    """Handle ``use a::b::C;`` / ``use crate::x::y;`` / ``use a as b;``.

    ``module_path`` keeps the raw ``::`` path so the resolver's Rust branch can
    tell ``crate::``/``self::``/``super::`` (intra-crate, suffix-matchable) from
    ``std::``/external-crate paths. For a scoped path the leaf segment is the
    imported symbol (so the bare-name import walk can resolve ``y()``)."""
    line = _row(node)
    arg = node.child_by_field_name("argument")
    if arg is None:
        return []
    # `use a as b` — resolve against the underlying path; alias is how it's
    # referenced (module_alias).
    alias = ""
    if arg.type == "use_as_clause":
        path_node = arg.child_by_field_name("path")
        alias_node = arg.child_by_field_name("alias")
        alias = _text(alias_node) if alias_node is not None else ""
        arg = path_node if path_node is not None else arg
    module = _text(arg).replace("\n", "").replace(" ", "")
    if not module:
        return []
    names: tuple[ImportedName, ...] = ()
    if arg.type == "scoped_identifier":
        name_node = arg.child_by_field_name("name")
        if name_node is not None:
            names = (ImportedName(name=_text(name_node)),)
    elif arg.type == "identifier":
        names = (ImportedName(name=module),)
    return [
        Import(
            rel_path=rel_path,
            module_path=module,
            language=language,
            line=line,
            module_alias=alias,
            imported_names=names,
        )
    ]


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------


_EXTRACTORS: dict[str, Callable[[str, str, Node], list[Import]]] = {
    "python": _extract_python_import,
    "typescript": _extract_ts_js_import,
    "tsx": _extract_ts_js_import,
    "javascript": _extract_ts_js_import,
    "java": _extract_java_import,
    "go": _extract_go_import,
    "dart": _extract_dart_import,
    "swift": _extract_swift_import,
    "c": _extract_c_include,
    "rust": _extract_rust_import,
}


def extract_imports(parsed: ParsedFile) -> list[Import]:
    """Walk the AST and produce one :class:`Import` per import statement.

    Returns an empty list for languages without an extractor. Imports are
    sorted by ``(line, module_path)`` for deterministic output.
    """
    extractor = _EXTRACTORS.get(parsed.language)
    if extractor is None:
        return []
    types = _IMPORT_NODE_TYPES.get(parsed.language, frozenset())
    imports: list[Import] = []

    # DFS over the tree. We do not descend into import-statement nodes
    # themselves (their inner structure is consumed by the extractor).
    stack: list[Node] = [parsed.tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in types:
            imports.extend(extractor(parsed.rel_path, parsed.language, node))
            continue
        # JavaScript / TSX / TypeScript also use require('x') in CommonJS
        # and dynamic-import call sites. Capture those by recognizing the
        # call_expression shape.
        if (
            parsed.language in ("javascript", "typescript", "tsx")
            and node.type == "call_expression"
        ):
            imports.extend(_extract_js_require_call(parsed.rel_path, parsed.language, node))
        # Continue descending into non-import nodes.
        stack.extend(node.children)

    imports.sort(key=lambda imp: (imp.line, imp.module_path))
    return imports
