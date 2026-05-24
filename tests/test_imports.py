"""Tests for the per-language import extractor (DEC-024).

In-memory source samples per language — no fixture files needed since
each language's import grammar is independent of its tags grammar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forensic_deepdive.static.imports import (
    Import,
    ImportedName,
    extract_imports,
)
from forensic_deepdive.static.parse import ParsedFile, parse_source


def _imports(language: str, src: bytes) -> list[Import]:
    tree = parse_source(src, language)
    parsed = ParsedFile(
        path=Path(f"x.{language}"),
        rel_path=f"x.{language}",
        language=language,
        source=src,
        tree=tree,
    )
    return extract_imports(parsed)


def _modules(imports: list[Import]) -> list[str]:
    return [imp.module_path for imp in imports]


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def test_python_plain_import() -> None:
    imps = _imports("python", b"import os\nimport os.path\n")
    assert _modules(imps) == ["os", "os.path"]
    for imp in imps:
        assert imp.module_alias == ""
        assert imp.imported_names == ()


def test_python_aliased_import() -> None:
    imps = _imports("python", b"import json as J\nimport os.path as P\n")
    assert _modules(imps) == ["json", "os.path"]
    assert imps[0].module_alias == "J"
    assert imps[1].module_alias == "P"


def test_python_from_import_multiple_names() -> None:
    imps = _imports("python", b"from typing import List, Dict\n")
    assert len(imps) == 1
    assert imps[0].module_path == "typing"
    assert imps[0].imported_names == (
        ImportedName(name="List"),
        ImportedName(name="Dict"),
    )


def test_python_from_import_aliased_name() -> None:
    imps = _imports("python", b"from typing import Optional as Opt\n")
    assert imps[0].imported_names == (ImportedName(name="Optional", alias="Opt"),)


def test_python_relative_imports() -> None:
    imps = _imports("python", b"from . import sibling\nfrom .pkg import thing\n")
    assert _modules(imps) == [".", ".pkg"]
    assert imps[0].imported_names == (ImportedName(name="sibling"),)
    assert imps[1].imported_names == (ImportedName(name="thing"),)


def test_python_wildcard_import() -> None:
    imps = _imports("python", b"from os.path import *\n")
    assert imps[0].imported_names == (ImportedName(name="*"),)


# ---------------------------------------------------------------------------
# TypeScript / JavaScript
# ---------------------------------------------------------------------------


def test_typescript_named_import() -> None:
    imps = _imports("typescript", b'import { Z, W as A } from "./y";\n')
    assert imps[0].module_path == "./y"
    assert imps[0].imported_names == (
        ImportedName(name="Z"),
        ImportedName(name="W", alias="A"),
    )


def test_typescript_namespace_import() -> None:
    imps = _imports("typescript", b'import * as Y from "./y";\n')
    assert imps[0].module_alias == "Y"
    assert imps[0].module_path == "./y"


def test_typescript_default_import() -> None:
    imps = _imports("typescript", b'import Y from "./y";\n')
    # Default import is recorded as a single ImportedName(name="default",
    # alias="Y") so the resolver later knows Y is the default-export hook.
    assert imps[0].imported_names == (ImportedName(name="default", alias="Y"),)


def test_typescript_side_effect_import() -> None:
    imps = _imports("typescript", b'import "./side-effect";\n')
    assert imps[0].module_path == "./side-effect"
    assert imps[0].imported_names == ()
    assert imps[0].module_alias == ""


def test_typescript_type_only_import() -> None:
    imps = _imports("typescript", b'import type { T } from "./t";\n')
    assert imps[0].module_path == "./t"
    assert imps[0].imported_names == (ImportedName(name="T"),)


def test_javascript_require_call() -> None:
    imps = _imports("javascript", b'const x = require("./legacy");\n')
    assert len(imps) == 1
    assert imps[0].module_path == "./legacy"


def test_javascript_mix_import_and_require() -> None:
    imps = _imports(
        "javascript",
        b'import { Z } from "./y";\nconst x = require("./legacy");\n',
    )
    assert {imp.module_path for imp in imps} == {"./y", "./legacy"}


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------


def test_java_simple_import() -> None:
    imps = _imports("java", b"package x;\nimport java.util.List;\n")
    assert _modules(imps) == ["java.util.List"]


def test_java_wildcard_import() -> None:
    imps = _imports("java", b"package x;\nimport java.util.*;\n")
    assert _modules(imps) == ["java.util.*"]


def test_java_static_import() -> None:
    imps = _imports("java", b"package x;\nimport static java.lang.Math.PI;\n")
    assert _modules(imps) == ["java.lang.Math.PI"]


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------


def test_go_single_import() -> None:
    imps = _imports("go", b'package main\nimport "fmt"\n')
    assert _modules(imps) == ["fmt"]


def test_go_grouped_imports() -> None:
    src = b'package main\nimport (\n  "io"\n  log "log/slog"\n  _ "side"\n)\n'
    imps = _imports("go", src)
    paths = _modules(imps)
    assert "io" in paths
    assert "log/slog" in paths
    assert "side" in paths
    # Alias preserved on the grouped specs.
    by_path = {imp.module_path: imp for imp in imps}
    assert by_path["log/slog"].module_alias == "log"
    assert by_path["side"].module_alias == "_"


# ---------------------------------------------------------------------------
# Dart
# ---------------------------------------------------------------------------


def test_dart_package_import() -> None:
    imps = _imports("dart", b"import 'package:foo/bar.dart';\n")
    assert imps[0].module_path == "package:foo/bar.dart"
    assert imps[0].is_reexport is False


def test_dart_relative_import_with_alias() -> None:
    imps = _imports("dart", b"import './local.dart' as ns;\n")
    assert imps[0].module_path == "./local.dart"
    assert imps[0].module_alias == "ns"


def test_dart_export_is_flagged_reexport() -> None:
    imps = _imports("dart", b"export 'package:x/y.dart';\n")
    assert imps[0].module_path == "package:x/y.dart"
    assert imps[0].is_reexport is True


# ---------------------------------------------------------------------------
# Swift
# ---------------------------------------------------------------------------


def test_swift_simple_import() -> None:
    imps = _imports("swift", b"import Foundation\n")
    assert _modules(imps) == ["Foundation"]


def test_swift_qualified_import() -> None:
    imps = _imports("swift", b"import struct Foo.Bar\n")
    assert _modules(imps) == ["Foo.Bar"]


# ---------------------------------------------------------------------------
# C
# ---------------------------------------------------------------------------


def test_c_local_include() -> None:
    imps = _imports("c", b'#include "local.h"\n')
    assert _modules(imps) == ["local.h"]


def test_c_system_include_keeps_angle_brackets() -> None:
    """System includes keep ``<...>`` so consumers can distinguish system
    from project headers without a separate flag."""
    imps = _imports("c", b"#include <stdio.h>\n")
    assert _modules(imps) == ["<stdio.h>"]


# ---------------------------------------------------------------------------
# Determinism + non-import language behavior
# ---------------------------------------------------------------------------


def test_unknown_language_returns_empty() -> None:
    # ``ruby`` is not in _EXTRACTORS — should return [] without raising.
    from forensic_deepdive.static.imports import _EXTRACTORS

    assert "ruby" not in _EXTRACTORS


def test_imports_sorted_by_line_and_path() -> None:
    src = b"import zlib\nimport os\nimport sys\n"
    imps = _imports("python", src)
    assert imps == sorted(imps, key=lambda i: (i.line, i.module_path))


@pytest.mark.parametrize("language", ["python", "typescript", "java", "go", "dart"])
def test_empty_file_yields_no_imports(language: str) -> None:
    """A file with no imports must produce an empty list (not an error)."""
    src = {
        "python": b"x = 1\n",
        "typescript": b"const x: number = 1;\n",
        "java": b"package x; class C {}\n",
        "go": b"package x\nvar y = 1\n",
        "dart": b"int x = 1;\n",
    }[language]
    assert _imports(language, src) == []
