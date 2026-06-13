"""CALLS resolver — turn reference Tags into CallsEdges with confidence.

DEC-025, REMAINING.md item 8b step 3. This is the v0.2 algorithmic
core that elevates the graph from "we have files and symbols" to
"we know which symbol called which symbol." The MCP ``impact(symbol)``
tool (DEC-016, planned) depends entirely on this.

Algorithm (per ref Tag ``r`` in file ``F``):

1. **Same-file lexical scope.** Walk the enclosing-class chain stored
   in ``r.enclosing_scope`` (innermost first), then top-level. The
   first defining qn that matches ``r.name`` resolves locally.
   Confidence: ``EXTRACTED``. Implements DEC-012's local-shadowing rule
   at symbol granularity.

2. **Import-graph walk.** Walk ``F``'s :class:`Import` records. If any
   import's ``imported_names`` carries an :class:`ImportedName` whose
   ``name`` or ``alias`` matches ``r.name``, resolve the import to its
   intra-repo source file (per-language module-path resolution) and look
   up the matching top-level symbol there. Confidence: ``EXTRACTED``
   when exactly one intra-repo candidate exists, ``INFERRED`` when the
   imported name's source is ambiguous (re-exports, default exports).
   External imports (no intra-repo file match) are dropped — the
   already-emitted IMPORTS edge captures the dependency.

3. **(Receiver-type inference — deferred.)** Our queries exclude dotted
   method calls (``obj.foo()``) via ``_drop_method`` per DEC-012, so the
   ref set contains bare-name calls and constructors only. Receiver-type
   inference would let us capture dotted calls without false edges; PRD
   §10 future work tracks it.

4. **Cross-file same-name fallback.** When 1-2 don't resolve and at
   least one *same-language* file elsewhere in the repo defines a
   top-level symbol matching ``r.name``: emit an edge per candidate.
   Confidence: ``INFERRED`` when exactly one same-language candidate
   exists, ``AMBIGUOUS`` (with every candidate surfaced) otherwise.
   Matches DEC-012's same-language scoping and DEC-015's AMBIGUOUS
   surfacing semantics.

Caller attribution:
- ``r.enclosing_scope`` (from :func:`tags._enclosing_scope_qn`) provides
  the immediate caller's qn_local — e.g. ``"Greeter.greet"`` for a ref
  inside ``def greet`` inside ``class Greeter``.
- Refs at module level (``enclosing_scope == ""``) attribute to a
  synthetic ``<file>::<module>`` Symbol that the build phase emits
  per source file. This makes module-load-time calls (e.g. Python
  ``app = create_app()`` at top of file) first-class edges rather
  than dropped data.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.imports import Import
from forensic_deepdive.static.method_calls import MethodCall
from forensic_deepdive.static.tags import Tag

MODULE_SCOPE = "<module>"
"""Synthetic qn_local for the file-level scope. The build phase emits a
``Symbol(qualified_name=f"{rel_path}::<module>", kind=MODULE)`` per source
file so module-level refs have a valid caller endpoint."""


@dataclass(frozen=True, slots=True)
class ResolvedCall:
    """One CallsEdge produced by the resolver, ready for the LadybugStore."""

    caller_qn: str  # f"{rel_path}::{qn_local-or-<module>}"
    callee_qn: str  # f"{rel_path}::{qn_local}"
    confidence: Confidence
    evidence: str  # "same-file" | "import" | "name-fallback" | ...
    ref_line: int  # source line of the originating ref tag
    via: str = "bare"  # DEC-037 resolution channel (self|this|ctor|static|module|bare)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def resolve_calls(
    tags: Iterable[Tag],
    imports: Iterable[Import],
    source_files_by_path: dict[str, str],
) -> list[ResolvedCall]:
    """Run the 4-step CALLS resolver.

    Args:
        tags: every Tag from extract_tags (defs + refs). Refs without
            an enclosing scope attribute to ``<module>``.
        imports: every Import from extract_imports.
        source_files_by_path: ``{rel_path: language}`` for every source
            file in the repo. Used both to filter refs (we only resolve
            refs whose file is in this set) and as the corpus for the
            import-walk and cross-file fallback.

    Returns ResolvedCall records in deterministic order
    ``(caller_qn, callee_qn, ref_line)``.
    """
    tags_list = list(tags)
    imports_list = list(imports)

    # Index defs by (file, qn_local) for same-file lookups.
    defs_by_file: dict[str, dict[str, Tag]] = defaultdict(dict)
    # Index defs by (file, bare_name) -> list of qn_local. Multiple
    # methods named "name" in two classes in one file produce two
    # entries here (one per class qn_local).
    defs_by_file_bare: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    # Cross-file fallback: language -> bare_name -> list of (file, qn_local).
    defs_by_lang_bare: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for tag in tags_list:
        if tag.kind != "def":
            continue
        if tag.rel_path not in source_files_by_path:
            continue
        qn_local = f"{tag.parent}.{tag.name}" if tag.parent else tag.name
        # Only keep the first def per (file, qn_local) — duplicates would
        # be PK collisions on the symbol side (and BuildGraphPhase dedups
        # there too).
        defs_by_file[tag.rel_path].setdefault(qn_local, tag)
        defs_by_file_bare[tag.rel_path][tag.name].append(qn_local)
        defs_by_lang_bare[tag.language][tag.name].append((tag.rel_path, qn_local))

    imports_by_file: dict[str, list[Import]] = defaultdict(list)
    for imp in imports_list:
        if imp.rel_path in source_files_by_path:
            imports_by_file[imp.rel_path].append(imp)

    resolved: list[ResolvedCall] = []

    for tag in tags_list:
        if tag.kind != "ref":
            continue
        if tag.rel_path not in source_files_by_path:
            continue

        caller_qn = _caller_qn(tag)

        # Step 1: same-file lexical scope.
        same_file = _resolve_same_file(tag, defs_by_file[tag.rel_path])
        if same_file:
            for callee_qn in same_file:
                resolved.append(
                    ResolvedCall(
                        caller_qn=caller_qn,
                        callee_qn=callee_qn,
                        confidence=Confidence.EXTRACTED,
                        evidence="same-file",
                        ref_line=tag.line,
                    )
                )
            continue

        # Step 2: import-graph walk.
        from_imports = _resolve_via_imports(
            tag, imports_by_file[tag.rel_path], defs_by_file, source_files_by_path
        )
        if from_imports:
            for callee_qn, conf in from_imports:
                resolved.append(
                    ResolvedCall(
                        caller_qn=caller_qn,
                        callee_qn=callee_qn,
                        confidence=conf,
                        evidence="import",
                        ref_line=tag.line,
                    )
                )
            continue

        # Step 4: cross-file same-name fallback.
        fallback = _resolve_cross_file_fallback(tag, defs_by_lang_bare[tag.language])
        if fallback:
            conf = Confidence.INFERRED if len(fallback) == 1 else Confidence.AMBIGUOUS
            for callee_qn in fallback:
                resolved.append(
                    ResolvedCall(
                        caller_qn=caller_qn,
                        callee_qn=callee_qn,
                        confidence=conf,
                        evidence="name-fallback",
                        ref_line=tag.line,
                    )
                )
            # else: unresolved — silently drop.

    resolved.sort(key=lambda r: (r.caller_qn, r.callee_qn, r.ref_line))
    return resolved


# ---------------------------------------------------------------------------
# Receiver-type method-call resolver (DEC-037, v0.3 Item C)
# ---------------------------------------------------------------------------


def resolve_method_calls(
    method_calls: Iterable[MethodCall],
    tags: Iterable[Tag],
    imports: Iterable[Import],
    source_files_by_path: dict[str, str],
) -> list[ResolvedCall]:
    """Resolve dotted ``receiver.method()`` calls by inferring the receiver's
    type (DEC-037). Every edge is tagged **INFERRED** (the receiver type is
    inferred, not proven) or **AMBIGUOUS** (a cross-file static call with
    multiple candidate owners). Rules, in priority order:

    1. ``self.m()`` / ``this.m()`` → resolve ``m`` against the **enclosing
       class's** members (the class is the prefix of the caller's scope).
       ``via="self"`` / ``via="this"``.
    2. ``Foo.m()`` where ``Foo`` is a known intra-repo **type** → resolve ``m``
       against ``Foo``'s members (same file first, then same-language repo-wide;
       multiple owners ⇒ AMBIGUOUS). ``via="static"``.
    3. ``mod.m()`` where ``mod`` matches an **import alias** → resolve ``m``
       against the imported file's top-level symbols. ``via="module"``.

    Anything else — a complex receiver (``a.b.c()``, ``foo().bar()``), an
    unknown local variable (no constructor-binding inference in v0.3 — that is
    the deferred rule 2, a documented DEC-037 follow-on), or a name that matches
    nothing — is **dropped**, NOT emitted as AMBIGUOUS-to-every-homonym.
    Flooding the graph with one AMBIGUOUS edge per same-named method is exactly
    the noise Item C exists to remove (a deliberate divergence from PRD §4.3's
    "default keep AMBIGUOUS"; see DEC-037). A dropped call is honestly "type
    unknown" — the same outcome as v0.2, but now the resolvable majority become
    precise INFERRED edges.
    """
    method_calls_list = list(method_calls)

    # Member-existence index: file -> set of qn_local (defs). And a same-language
    # member index: language -> qn_local -> sorted list of files defining it.
    defs_by_file: dict[str, set[str]] = defaultdict(set)
    member_by_lang: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for tag in tags:
        if tag.kind != "def" or tag.rel_path not in source_files_by_path:
            continue
        qn_local = f"{tag.parent}.{tag.name}" if tag.parent else tag.name
        if qn_local in defs_by_file[tag.rel_path]:
            continue  # first def wins (PK dedup, mirrors resolve_calls)
        defs_by_file[tag.rel_path].add(qn_local)
        member_by_lang[tag.language][qn_local].append(tag.rel_path)

    imports_by_file: dict[str, list[Import]] = defaultdict(list)
    for imp in imports:
        if imp.rel_path in source_files_by_path:
            imports_by_file[imp.rel_path].append(imp)

    resolved: list[ResolvedCall] = []
    for mc in method_calls_list:
        if mc.rel_path not in source_files_by_path:
            continue
        caller_qn = f"{mc.rel_path}::{mc.enclosing_scope or MODULE_SCOPE}"
        for callee_qn, conf, via in _resolve_one_method(
            mc, defs_by_file, member_by_lang, imports_by_file, source_files_by_path
        ):
            resolved.append(
                ResolvedCall(
                    caller_qn=caller_qn,
                    callee_qn=callee_qn,
                    confidence=conf,
                    evidence=f"receiver-{via}",
                    ref_line=mc.line,
                    via=via,
                )
            )

    resolved.sort(key=lambda r: (r.caller_qn, r.callee_qn, r.via, r.ref_line))
    return resolved


def _resolve_one_method(
    mc: MethodCall,
    defs_by_file: dict[str, set[str]],
    member_by_lang: dict[str, dict[str, list[str]]],
    imports_by_file: dict[str, list[Import]],
    source_files_by_path: dict[str, str],
) -> list[tuple[str, Confidence, str]]:
    """Return ``(callee_qn, confidence, via)`` tuples for one method call, or
    an empty list when the receiver type can't be inferred."""
    receiver, method, file, language = mc.receiver, mc.method, mc.rel_path, mc.language

    # Rule 1: self / this → enclosing class's member.
    if receiver in ("self", "this"):
        scope = mc.enclosing_scope
        enclosing_class = scope.rsplit(".", 1)[0] if "." in scope else ""
        if enclosing_class:
            member_qn = f"{enclosing_class}.{method}"
            if member_qn in defs_by_file.get(file, set()):
                return [(_qualify(file, member_qn), Confidence.INFERRED, receiver)]
        return []  # self/this outside a resolvable class member → drop

    # Only simple single-identifier receivers can be inferred. Complex receivers
    # (a.b.c(), foo().bar(), x[i].m()) need dataflow we don't do in v0.3.
    if not receiver.isidentifier():
        return []

    # Rule 2: static / class-qualified — receiver is a known type; resolve the
    # method against that type's members.
    member_qn = f"{receiver}.{method}"
    if member_qn in defs_by_file.get(file, set()):
        return [(_qualify(file, member_qn), Confidence.INFERRED, "static")]
    cross = [f for f in member_by_lang.get(language, {}).get(member_qn, []) if f != file]
    if cross:
        conf = Confidence.INFERRED if len(cross) == 1 else Confidence.AMBIGUOUS
        return [(_qualify(f, member_qn), conf, "static") for f in sorted(cross)]

    # Rule 3: module / import-alias-qualified — resolve the import to a file and
    # look up the method as a top-level symbol there.
    for imp in imports_by_file.get(file, []):
        if not _import_alias_matches(imp, receiver):
            continue
        target = _resolve_import_to_file(imp, source_files_by_path)
        if target is not None and method in defs_by_file.get(target, set()):
            return [(_qualify(target, method), Confidence.INFERRED, "module")]

    return []


def _import_alias_matches(imp: Import, receiver: str) -> bool:
    """True when *receiver* is the name an import is bound to: an explicit
    ``import x as R`` / ``import * as R`` alias, or — for plain ``import os`` —
    the last segment of the module path."""
    if imp.module_alias and imp.module_alias == receiver:
        return True
    if not imp.module_alias and imp.module_path:
        last = imp.module_path.replace("/", ".").rstrip(".").split(".")[-1]
        return last == receiver
    return False


# ---------------------------------------------------------------------------
# Caller attribution
# ---------------------------------------------------------------------------


def _caller_qn(tag: Tag) -> str:
    """Build the caller's full qualified_name. Refs without an enclosing
    scope attribute to the file's synthetic ``<module>`` Symbol."""
    scope = tag.enclosing_scope or MODULE_SCOPE
    return f"{tag.rel_path}::{scope}"


# ---------------------------------------------------------------------------
# Step 1: same-file lexical scope
# ---------------------------------------------------------------------------


def _resolve_same_file(tag: Tag, defs_in_file: dict[str, Tag]) -> list[str]:
    """Try every enclosing-class scope (innermost first), then top-level,
    for a matching def. Returns 0-or-1 callee qn (same-file is
    unambiguous by Symbol PK)."""
    # Enclosing-class chain from tag.enclosing_scope.
    #   "Greeter.greet"        → chain = ["Greeter"]
    #   "Outer.Inner.method"   → chain = ["Outer.Inner", "Outer"]  (innermost-first)
    #   "Greeter"              → chain = []  (class-body scope; no class to look inside of)
    #   ""                     → chain = []  (module scope)
    chain: list[str] = []
    scope_parts = tag.enclosing_scope.split(".") if tag.enclosing_scope else []
    # Drop the last part (the function/method itself) to get the
    # enclosing-class chain. Then innermost-first means longest first.
    for i in range(len(scope_parts) - 1, 0, -1):
        chain.append(".".join(scope_parts[:i]))

    rel = tag.rel_path

    # Try enclosing classes innermost-first.
    for class_qn in chain:
        candidate = f"{class_qn}.{tag.name}"
        if candidate in defs_in_file:
            return [_qualify(rel, candidate)]

    # Top-level.
    if tag.name in defs_in_file:
        return [_qualify(rel, tag.name)]

    return []


# ---------------------------------------------------------------------------
# Step 2: import-graph walk
# ---------------------------------------------------------------------------


def _resolve_via_imports(
    tag: Tag,
    imports: list[Import],
    defs_by_file: dict[str, dict[str, Tag]],
    source_files_by_path: dict[str, str],
) -> list[tuple[str, Confidence]]:
    """Try every import for *tag*'s file. Yields (callee_qn, confidence)
    pairs.

    A ref to name ``N`` matches an import whose ``imported_names`` contains
    an :class:`ImportedName` with ``name == N`` (and no alias) OR
    ``alias == N``. The resolved target name is always the *original*
    name (alias is only how the importer wrote it).
    """
    if not imports:
        return []

    results: list[tuple[str, Confidence]] = []
    for imp in imports:
        target_file = _resolve_import_to_file(imp, source_files_by_path)
        if target_file is None:
            continue  # external — IMPORTS edge already captures the dep
        target_defs = defs_by_file.get(target_file, {})

        # Three resolution modes per import:
        #
        # (a) Explicit named import — ``from X import foo`` / ``import {
        #     foo } from "./x"`` — match the ref's name to one of
        #     ``imp.imported_names`` and resolve to that exact name in
        #     the target file. EXTRACTED when the target file defines it,
        #     INFERRED for re-exports.
        # (b) Wildcard import — ``from X import *`` (Python) — the
        #     extractor surfaces this as ``ImportedName(name="*")``. Try
        #     the ref's bare name as a top-level def in the target file.
        #     INFERRED (the import doesn't name the symbol explicitly).
        # (c) Whole-module import — ``#include "x.h"`` (C), ``import
        #     "fmt"`` (Go), Dart's bare ``import 'x.dart'`` — the import
        #     has ``imported_names == ()`` and brings everything into
        #     scope. Look up the ref's bare name in the target file.
        #     INFERRED — the source code didn't promise this name came
        #     from this module.

        # Mode (a)
        explicit_target = None
        for ime in imp.imported_names:
            if ime.name == "*":
                continue  # mode (b), handled below
            ref_matches_alias = ime.alias != "" and ime.alias == tag.name
            ref_matches_name = ime.alias == "" and ime.name == tag.name
            if ref_matches_alias or ref_matches_name:
                explicit_target = ime.name
                break
        if explicit_target is not None:
            if explicit_target in target_defs:
                conf = Confidence.INFERRED if imp.is_reexport else Confidence.EXTRACTED
                results.append((_qualify(target_file, explicit_target), conf))
            continue

        # Mode (b): wildcard import
        has_wildcard = any(ime.name == "*" for ime in imp.imported_names)
        if has_wildcard:
            if tag.name in target_defs:
                results.append((_qualify(target_file, tag.name), Confidence.INFERRED))
            continue

        # Mode (c): whole-module import (no imported_names at all)
        if not imp.imported_names and tag.name in target_defs:
            results.append((_qualify(target_file, tag.name), Confidence.INFERRED))

    return results


# ---------------------------------------------------------------------------
# Step 4: cross-file same-name fallback
# ---------------------------------------------------------------------------


def _resolve_cross_file_fallback(
    tag: Tag,
    defs_in_lang: dict[str, list[tuple[str, str]]],
) -> list[str]:
    """Look across all same-language defs for top-level symbols matching
    ``tag.name``. Excludes the ref's own file (step 1 covers it) and
    excludes class members (only top-level defs are valid fallback
    targets — methods need step 2's import-walk or step 3's receiver
    inference)."""
    candidates: list[str] = []
    for path, qn_local in defs_in_lang.get(tag.name, ()):
        if path == tag.rel_path:
            continue  # step 1 already had a shot
        # Top-level only: qn_local has no dot.
        if "." in qn_local:
            continue
        candidates.append(_qualify(path, qn_local))
    candidates.sort()
    return candidates


# ---------------------------------------------------------------------------
# Per-language module-path → intra-repo file resolution
# ---------------------------------------------------------------------------


def _resolve_import_to_file(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Dispatch to the per-language resolver. Returns the importing
    target's rel_path if it's an intra-repo source file; ``None`` if
    external (stdlib, package manager, system header)."""
    lang = imp.language
    if lang == "python":
        return _resolve_python_import(imp, source_files_by_path)
    if lang in ("typescript", "tsx", "javascript"):
        return _resolve_ts_js_import(imp, source_files_by_path)
    if lang == "java":
        return _resolve_java_import(imp, source_files_by_path)
    if lang == "dart":
        return _resolve_dart_import(imp, source_files_by_path)
    if lang == "c":
        return _resolve_c_include(imp, source_files_by_path)
    if lang == "rust":
        return _resolve_rust_import(imp, source_files_by_path)
    # Go and Swift module resolution requires project-build-system info
    # (go.mod for Go; SwiftPM/Xcode for Swift). v0.2 treats them as
    # external. v0.3 work tracks this.
    return None


def _resolve_python_import(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Map a Python module path to a repo file.

    Relative imports (``.``, ``.pkg``) resolve against the importing
    file's directory. Absolute imports are matched by suffix — without
    a setup.py/pyproject we don't know the package roots, so any
    intra-repo file whose path ends with ``pkg/mod.py`` (or
    ``pkg/mod/__init__.py``) is a candidate.
    """
    module = imp.module_path
    if not module:
        return None

    if module.startswith("."):
        # Relative import. Strip leading dots; each dot is one level up
        # from the importer's dir (the first dot stays at the dir itself).
        dots = 0
        while dots < len(module) and module[dots] == ".":
            dots += 1
        rest = module[dots:]
        importer = PurePosixPath(imp.rel_path).parent
        # `from . import x` → dots=1, look in importer's own dir
        # `from .. import x` → dots=2, one dir up
        for _ in range(dots - 1):
            importer = importer.parent

        base = importer / rest.replace(".", "/") if rest else importer

        for candidate in _python_module_candidates(base):
            if candidate in source_files_by_path:
                return candidate
        return None

    # Absolute: try direct + suffix matches.
    parts = module.split(".")
    base_str = "/".join(parts)
    for path in source_files_by_path:
        if path == base_str + ".py":
            return path
        if path == base_str + "/__init__.py":
            return path
    # Suffix match (covers `src/` and similar package roots).
    for path in source_files_by_path:
        if path.endswith("/" + base_str + ".py") or path.endswith("/" + base_str + "/__init__.py"):
            return path
    return None


def _python_module_candidates(base: PurePosixPath) -> list[str]:
    """For a Python module base path (no extension), the file candidates
    in lookup order."""
    s = base.as_posix()
    if s == ".":
        s = ""
    return [
        s + ".py" if s else "",
        (s + "/__init__.py").lstrip("/"),
    ]


_TS_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _resolve_ts_js_import(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Map a TS/JS import string to a repo file.

    Relative imports (``./y``, ``../foo``) resolve against the importer's
    directory and try the standard extension and ``/index.*`` candidates.
    Bare imports (``react``, ``lodash``) are external (npm) — drop.
    """
    module = imp.module_path
    if not module or not (module.startswith(".") or module.startswith("/")):
        return None  # bare or absolute-package — external

    importer_dir = PurePosixPath(imp.rel_path).parent
    raw = _normalize_relative(importer_dir, module)

    # Exact match first (some imports include the extension).
    if raw in source_files_by_path:
        return raw

    # Try each extension and the /index.* forms.
    for ext in _TS_JS_EXTS:
        cand = raw + ext
        if cand in source_files_by_path:
            return cand
    for ext in _TS_JS_EXTS:
        cand = raw + "/index" + ext
        if cand in source_files_by_path:
            return cand
    return None


def _resolve_java_import(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Java's ``import com.x.Y`` maps to a path ending in
    ``com/x/Y.java``. Wildcards (``import com.x.*``) and static
    member imports (``import static com.x.Y.MEMBER``) can't be
    cleanly mapped to a single file — drop."""
    module = imp.module_path
    if not module or module.endswith(".*"):
        return None
    # `import static com.x.Y.MEMBER` — the `.MEMBER` suffix isn't a
    # package component. We can't reliably distinguish that from
    # `import com.x.Y.NestedClass` without symbol info, so we try the
    # full path AND the path minus the last component.
    parts = module.split(".")
    candidates: list[str] = []
    for i in (len(parts), len(parts) - 1):
        if i < 1:
            continue
        candidates.append("/".join(parts[:i]) + ".java")
    for cand in candidates:
        for path in source_files_by_path:
            if path == cand or path.endswith("/" + cand):
                return path
    return None


def _resolve_dart_import(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Dart's ``import './x.dart'`` resolves against the importer's
    directory. ``package:`` / ``dart:`` URIs are external (need
    pubspec.yaml to resolve)."""
    module = imp.module_path
    if not module or module.startswith(("package:", "dart:")):
        return None
    importer_dir = PurePosixPath(imp.rel_path).parent
    candidate = _normalize_relative(importer_dir, module)
    if candidate in source_files_by_path:
        return candidate
    # If the module path didn't carry an extension, try .dart.
    if not candidate.endswith(".dart"):
        with_ext = candidate + ".dart"
        if with_ext in source_files_by_path:
            return with_ext
    return None


def _resolve_rust_import(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """Resolve ``use crate::a::b::Item`` to an intra-crate ``.rs`` file.

    Only ``crate::`` / ``self::`` / ``super::`` paths are intra-repo; ``std::``
    and bare-crate paths are external (need ``Cargo.toml`` — deferred to v0.6).
    Without crate-root info we suffix-match: try the full path and the
    path-minus-leaf (the leaf may be an imported *item*, not a module) as both
    ``a/b.rs`` and ``a/b/mod.rs``."""
    module = imp.module_path
    if not module:
        return None
    parts = module.split("::")
    if not parts or parts[0] not in ("crate", "self", "super"):
        return None  # std / external crate
    rest = [p for p in parts[1:] if p not in ("self", "super")]
    if not rest:
        return None
    for depth in (len(rest), len(rest) - 1):
        if depth < 1:
            continue
        base = "/".join(rest[:depth])
        for cand in (base + ".rs", base + "/mod.rs"):
            for path in source_files_by_path:
                if path == cand or path.endswith("/" + cand):
                    return path
    return None


def _resolve_c_include(imp: Import, source_files_by_path: dict[str, str]) -> str | None:
    """C's ``#include "x.h"`` resolves against the importer's directory.
    System includes (``<stdio.h>``, with angle brackets preserved by
    the extractor) are external."""
    module = imp.module_path
    if not module or module.startswith("<"):
        return None
    importer_dir = PurePosixPath(imp.rel_path).parent
    candidate = _normalize_relative(importer_dir, module)
    if candidate in source_files_by_path:
        return candidate
    # Many repos co-locate .c and .h files. If the include is X.h and
    # source_files contains X.c, those are different translation units
    # but the include is genuinely about the header. We only return the
    # header file if it's in the source set.
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_relative(base_dir: PurePosixPath, rel: str) -> str:
    """Join *rel* against *base_dir* and normalize ``.``/``..`` segments
    using POSIX path semantics."""
    if rel.startswith("/"):
        # Repo-rooted absolute (rare).
        result_parts: list[str] = []
        parts: list[str] = rel.split("/")
    else:
        result_parts = list(base_dir.parts)
        parts = rel.split("/")
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if result_parts:
                result_parts.pop()
            continue
        result_parts.append(part)
    return "/".join(result_parts)


def _qualify(rel_path: str, qn_local: str) -> str:
    """Schema convention for Symbol.qualified_name."""
    return f"{rel_path}::{qn_local}"


# ---------------------------------------------------------------------------
# Shared declaration-name resolver (DEC-028 ladder), reused by inheritance
# (EXTENDS/IMPLEMENTS), DI (INJECTS, DEC-059), and the Django route provider
# (DEC-065). Moved here from pipeline.phases so contract-layer extractors can
# reuse it without a phases import cycle.
# ---------------------------------------------------------------------------


def resolve_name_to_files(
    name: str,
    rel_path: str,
    language: str,
    imports: list[Import],
    defs_top_by_file: dict[str, set[str]],
    defs_top_by_lang: dict[str, dict[str, list[str]]],
    source_files_by_path: dict[str, str],
) -> tuple[list[str], Confidence] | None:
    """Resolve a raw type/provider *name* referenced in *rel_path* to the file(s)
    that define it, with confidence — the DEC-028 same-file → import → cross-file
    ladder, shared by inheritance (EXTENDS/IMPLEMENTS), DI (INJECTS), and Django
    route views. Returns ``None`` when the name is external / unresolvable (the
    caller drops it).

    Same-file or a matching import → ``EXTRACTED``; a unique cross-file
    same-language definition → ``INFERRED``; several → ``AMBIGUOUS`` (every file)."""
    if name in defs_top_by_file.get(rel_path, ()):
        return [rel_path], Confidence.EXTRACTED

    imp_matches: list[str] = []
    for imp in imports:
        if imp.rel_path != rel_path:
            continue
        for ime in imp.imported_names:
            if ime.name == name or ime.alias == name:
                tgt = _resolve_import_to_file(imp, source_files_by_path)
                if tgt is not None and name in defs_top_by_file.get(tgt, ()):
                    imp_matches.append(tgt)
                break
    if imp_matches:
        return imp_matches, Confidence.EXTRACTED
    candidates = [c for c in defs_top_by_lang.get(language, {}).get(name, []) if c != rel_path]
    if not candidates:
        return None
    target_files = sorted(candidates)
    return target_files, (Confidence.INFERRED if len(target_files) == 1 else Confidence.AMBIGUOUS)
