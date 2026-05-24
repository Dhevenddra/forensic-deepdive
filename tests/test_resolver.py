"""Unit tests for the CALLS resolver (DEC-025).

In-memory source samples per language. The resolver is the load-bearing
algorithm for the v0.2 graph — every step (same-file lexical scope,
import-graph walk, cross-file fallback) is covered here, plus the
confidence assignments and caller-attribution semantics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.imports import extract_imports
from forensic_deepdive.static.parse import ParsedFile, parse_source
from forensic_deepdive.static.resolver import (
    MODULE_SCOPE,
    ResolvedCall,
    resolve_calls,
)
from forensic_deepdive.static.tags import extract_tags


def _parse(language: str, rel_path: str, src: bytes) -> ParsedFile:
    return ParsedFile(
        path=Path(rel_path),
        rel_path=rel_path,
        language=language,
        source=src,
        tree=parse_source(src, language),
    )


def _resolve(files: dict[str, tuple[str, bytes]]) -> list[ResolvedCall]:
    """files: {rel_path: (language, source)}. Returns all ResolvedCalls."""
    tags: list = []
    imports: list = []
    source_files: dict[str, str] = {}
    for rel, (lang, src) in files.items():
        parsed = _parse(lang, rel, src)
        tags.extend(extract_tags(parsed))
        imports.extend(extract_imports(parsed))
        source_files[rel] = lang
    return resolve_calls(tags, imports, source_files)


def _calls(resolved: list[ResolvedCall]) -> set[tuple[str, str, str]]:
    """Project to (caller, callee, confidence) tuples for assertions."""
    return {(r.caller_qn, r.callee_qn, str(r.confidence)) for r in resolved}


# ---------------------------------------------------------------------------
# Step 1 — same-file lexical scope (EXTRACTED)
# ---------------------------------------------------------------------------


def test_same_file_function_to_function_python() -> None:
    src = b"def helper(): pass\ndef caller(): helper()\n"
    resolved = _resolve({"a.py": ("python", src)})
    assert _calls(resolved) == {
        ("a.py::caller", "a.py::helper", "EXTRACTED"),
    }


def test_same_file_method_calls_sibling_method() -> None:
    src = b"""
class C:
    def helper(self): pass
    def caller(self):
        self  # not a call
        helper()
"""
    resolved = _resolve({"a.py": ("python", src)})
    # `helper()` inside C.caller resolves to C.helper (enclosing-class
    # scope), NOT top-level (there is no top-level helper).
    assert ("a.py::C.caller", "a.py::C.helper", "EXTRACTED") in _calls(resolved)


def test_same_file_method_calls_top_level_when_class_lacks_member() -> None:
    src = b"""
def helper(): pass

class C:
    def caller(self):
        helper()
"""
    resolved = _resolve({"a.py": ("python", src)})
    # C has no `helper` member; fall through to top-level def.
    assert ("a.py::C.caller", "a.py::helper", "EXTRACTED") in _calls(resolved)


def test_same_file_self_recursion() -> None:
    src = b"def fact(n): return fact(n - 1) if n > 1 else 1\n"
    resolved = _resolve({"a.py": ("python", src)})
    assert ("a.py::fact", "a.py::fact", "EXTRACTED") in _calls(resolved)


def test_same_file_resolution_is_extracted_for_every_language() -> None:
    """DEC-012's local-shadowing rule at symbol granularity — every
    language resolves a same-file call as EXTRACTED."""
    samples = {
        "python": (
            "a.py",
            b"def callee(): pass\ndef caller(): callee()\n",
            ("a.py::caller", "a.py::callee"),
        ),
        "typescript": (
            "a.ts",
            b"function callee() {}\nfunction caller() { callee(); }\n",
            ("a.ts::caller", "a.ts::callee"),
        ),
        "javascript": (
            "a.js",
            b"function callee() {}\nfunction caller() { callee(); }\n",
            ("a.js::caller", "a.js::callee"),
        ),
        "java": (
            "A.java",
            b"class A { void callee() {} void caller() { callee(); } }\n",
            ("A.java::A.caller", "A.java::A.callee"),
        ),
        "go": (
            "a.go",
            b"package main\nfunc callee() {}\nfunc caller() { callee() }\n",
            ("a.go::caller", "a.go::callee"),
        ),
        "c": (
            "a.c",
            b"void callee() {}\nvoid caller() { callee(); }\n",
            ("a.c::caller", "a.c::callee"),
        ),
    }
    for lang, (rel, src, (caller, callee)) in samples.items():
        resolved = _resolve({rel: (lang, src)})
        assert (caller, callee, "EXTRACTED") in _calls(resolved), lang


# ---------------------------------------------------------------------------
# Step 2 — import-graph walk
# ---------------------------------------------------------------------------


def test_explicit_named_import_python_extracted() -> None:
    files = {
        "lib.py": ("python", b"def helper(): pass\n"),
        "app.py": ("python", b"from lib import helper\ndef use(): helper()\n"),
    }
    resolved = _resolve(files)
    assert ("app.py::use", "lib.py::helper", "EXTRACTED") in _calls(resolved)


def test_aliased_named_import_python_extracted() -> None:
    files = {
        "lib.py": ("python", b"def helper(): pass\n"),
        "app.py": ("python", b"from lib import helper as H\ndef use(): H()\n"),
    }
    resolved = _resolve(files)
    # Caller refs `H` but resolver maps to lib.py's `helper`.
    assert ("app.py::use", "lib.py::helper", "EXTRACTED") in _calls(resolved)


def test_typescript_named_import_extracted() -> None:
    files = {
        "lib.ts": ("typescript", b"export function helper() {}\n"),
        "app.ts": (
            "typescript",
            b'import { helper } from "./lib";\nfunction use() { helper(); }\n',
        ),
    }
    resolved = _resolve(files)
    assert ("app.ts::use", "lib.ts::helper", "EXTRACTED") in _calls(resolved)


def test_typescript_index_resolution() -> None:
    """TS / JS resolver tries `<dir>/index.ts` when the import is a
    bare relative directory path."""
    files = {
        "lib/index.ts": ("typescript", b"export function helper() {}\n"),
        "app.ts": (
            "typescript",
            b'import { helper } from "./lib";\nfunction use() { helper(); }\n',
        ),
    }
    resolved = _resolve(files)
    assert (
        "app.ts::use",
        "lib/index.ts::helper",
        "EXTRACTED",
    ) in _calls(resolved)


def test_java_import_extracted() -> None:
    files = {
        "com/x/Helper.java": (
            "java",
            b"package com.x;\npublic class Helper {\n  public static void run() {}\n}\n",
        ),
        "com/y/Main.java": (
            "java",
            b"package com.y;\nimport com.x.Helper;\n"
            b"class Main { void use() { Helper x = new Helper(); } }\n",
        ),
    }
    resolved = _resolve(files)
    # `new Helper()` -> object_creation_expression -> reference.class
    assert (
        "com/y/Main.java::Main.use",
        "com/x/Helper.java::Helper",
        "EXTRACTED",
    ) in _calls(resolved)


def test_dart_relative_import_resolves_as_inferred() -> None:
    """Dart's bare ``import './x.dart'`` brings ALL public symbols from
    the target into scope (no `show`/`hide` combinator). The resolver
    marks calls resolving via such whole-module imports INFERRED — the
    source didn't promise this name came from this module. With a
    ``show helper`` combinator the same call would be EXTRACTED."""
    files = {
        "lib/helper.dart": ("dart", b"void helper() {}\n"),
        "lib/app.dart": (
            "dart",
            b"import './helper.dart';\nvoid use() { helper(); }\n",
        ),
    }
    resolved = _resolve(files)
    assert (
        "lib/app.dart::use",
        "lib/helper.dart::helper",
        "INFERRED",
    ) in _calls(resolved)


def test_c_include_resolves_as_inferred() -> None:
    """C ``#include`` brings everything from the header into scope but
    doesn't name a specific symbol — resolver marks the resulting call
    INFERRED to reflect that the source code didn't promise this name
    came from this include."""
    files = {
        "lib.h": ("c", b"void helper(void);\n"),
        "lib.c": ("c", b"void helper() {}\n"),
        "main.c": (
            "c",
            b'#include "lib.h"\nvoid main(void) { helper(); }\n',
        ),
    }
    resolved = _resolve(files)
    confidences = {
        (r.caller_qn, r.callee_qn): r.confidence
        for r in resolved
        if r.caller_qn.startswith("main.c::") and r.callee_qn.endswith("::helper")
    }
    # main.c's call to helper resolves via the #include of lib.h.
    assert ("main.c::main", "lib.h::helper") in confidences
    assert confidences[("main.c::main", "lib.h::helper")] == Confidence.INFERRED


def test_external_import_does_not_resolve() -> None:
    """`import os` (Python stdlib) is external — no intra-repo file
    matches, so the resolver drops the call. The IMPORTS edge File→Module
    captures the dependency separately."""
    files = {
        "a.py": ("python", b"import os\ndef use(): os.path.join('a', 'b')\n"),
    }
    resolved = _resolve(files)
    # `os.path.join` is a dotted call (excluded from refs by tags.py).
    # There are no bare refs to resolve. Result: no calls.
    assert resolved == []


# ---------------------------------------------------------------------------
# Step 4 — cross-file same-name fallback
# ---------------------------------------------------------------------------


def test_cross_file_fallback_inferred_when_unique() -> None:
    """When step 1 and 2 don't resolve and exactly ONE same-language
    file elsewhere defines a top-level symbol with the matching name,
    the resolver emits an INFERRED edge."""
    files = {
        "a.py": ("python", b"def helper(): pass\n"),
        "b.py": ("python", b"def use(): helper()\n"),  # no import
    }
    resolved = _resolve(files)
    assert ("b.py::use", "a.py::helper", "INFERRED") in _calls(resolved)


def test_cross_file_fallback_ambiguous_when_multiple() -> None:
    """Multiple same-language top-level defs with the matching name
    produce AMBIGUOUS edges to EVERY candidate (DEC-015)."""
    files = {
        "a.py": ("python", b"def helper(): pass\n"),
        "b.py": ("python", b"def helper(): pass\n"),
        "c.py": ("python", b"def use(): helper()\n"),
    }
    resolved = _resolve(files)
    calls = _calls(resolved)
    assert ("c.py::use", "a.py::helper", "AMBIGUOUS") in calls
    assert ("c.py::use", "b.py::helper", "AMBIGUOUS") in calls


def test_cross_file_fallback_is_language_scoped() -> None:
    """DEC-012's language scoping: cross-file fallback does not cross
    language boundaries. Python ``foo`` and Go ``foo`` are two
    different things."""
    files = {
        "a.py": ("python", b"def helper(): pass\n"),
        "b.go": ("go", b"package main\nfunc use() { helper() }\n"),
    }
    resolved = _resolve(files)
    # b.go's call to helper finds NO same-language def.
    callees = {r.callee_qn for r in resolved if r.caller_qn == "b.go::use"}
    assert "a.py::helper" not in callees


def test_cross_file_fallback_skips_class_members() -> None:
    """Top-level fallback only — methods (qn with a dot) aren't valid
    cross-file fallback targets. A method ``foo`` in another class
    shouldn't be a fallback for a bare ``foo()`` call elsewhere."""
    files = {
        "a.py": ("python", b"class C:\n    def helper(self): pass\n"),
        "b.py": ("python", b"def use(): helper()\n"),
    }
    resolved = _resolve(files)
    # No match — C.helper is not a fallback target.
    callees = {r.callee_qn for r in resolved if r.caller_qn == "b.py::use"}
    assert callees == set()


# ---------------------------------------------------------------------------
# Caller attribution
# ---------------------------------------------------------------------------


def test_module_level_ref_attributes_to_synthetic_module() -> None:
    """Refs at module level have no enclosing function — the resolver
    attributes them to the synthetic ``<module>`` Symbol per file."""
    files = {
        "a.py": ("python", b"def helper(): pass\nhelper()\n"),
    }
    resolved = _resolve(files)
    caller_qns = {r.caller_qn for r in resolved}
    assert f"a.py::{MODULE_SCOPE}" in caller_qns


def test_nested_method_caller_qn_includes_class_chain() -> None:
    src = b"""
class Outer:
    class Inner:
        def deep(self):
            helper()

def helper(): pass
"""
    resolved = _resolve({"a.py": ("python", src)})
    callers = {r.caller_qn for r in resolved if r.callee_qn == "a.py::helper"}
    assert "a.py::Outer.Inner.deep" in callers


def test_go_method_caller_uses_receiver_type() -> None:
    src = b"""
package main

type Greeter struct{}
func helper() {}
func (g *Greeter) Greet() {
    helper()
}
"""
    resolved = _resolve({"a.go": ("go", src)})
    assert ("a.go::Greeter.Greet", "a.go::helper", "EXTRACTED") in _calls(resolved)


# ---------------------------------------------------------------------------
# Determinism + filtering
# ---------------------------------------------------------------------------


def test_resolved_calls_are_sorted_for_determinism() -> None:
    src = b"def b(): pass\ndef a(): pass\ndef caller(): a(); b()\n"
    resolved = _resolve({"a.py": ("python", src)})
    assert resolved == sorted(resolved, key=lambda r: (r.caller_qn, r.callee_qn, r.ref_line))


@pytest.mark.parametrize(
    "lang,src",
    [
        ("python", b"x = 1\n"),
        ("typescript", b"const x = 1;\n"),
        ("java", b"package x;\nclass C {}\n"),
        ("go", b"package main\nvar x = 1\n"),
    ],
)
def test_no_refs_means_no_calls(lang: str, src: bytes) -> None:
    rel = f"a.{lang}" if lang != "java" else "C.java"
    resolved = _resolve({rel: (lang, src)})
    assert resolved == []
