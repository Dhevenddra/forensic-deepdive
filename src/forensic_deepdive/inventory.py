"""Repository inventory — the first pipeline stage.

Walks a repo, skipping VCS / vendored / build directories, classifies each file
by tree-sitter language, and assigns a **role** — source, test, fixture,
vendored, or generated — so later stages can keep non-production code out of
the symbol graph (DEC-012 → DEC-021).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from forensic_deepdive.static.parse import detect_language

# Directory names never worth walking into. Any dot-prefixed directory is also
# skipped (see take_inventory) — this set covers the non-dotted ones.
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "venv",
        "env",
        "__pycache__",
        "dist",
        "build",
        "target",
        "out",
        "vendor",
        "site-packages",
    }
)

# Files larger than this are skipped from parsing (minified bundles, blobs).
DEFAULT_MAX_FILE_BYTES = 1_048_576

# How many bytes to sniff for a "GENERATED — DO NOT EDIT" marker. The first
# half-KB covers virtually every generator's preamble (protoc, freezed,
# build_runner, openapi-generator, swagger-codegen, prost, ts-proto, ...).
_GENERATED_SNIFF_BYTES = 512

# File roles (DEC-012, widened by DEC-021, DEC-049).
ROLE_SOURCE = "source"
ROLE_TEST = "test"
ROLE_FIXTURE = "fixture"
ROLE_VENDORED = "vendored"  # DEC-021
ROLE_GENERATED = "generated"  # DEC-021
ROLE_EXAMPLE = "example"  # DEC-049 — in the graph, but demoted in ranking + query

# DEC-049 example/tutorial path-segment markers. Unlike the excluded roles,
# example files stay in the graph (demoted), so they're matched conservatively.
_EXAMPLE_SEGMENTS = frozenset(
    {
        "examples",
        "example",
        "docs_src",
        "samples",
        "sample",
        "tutorials",
        "tutorial",
        "demo",
        "demos",
    }
)

_FIXTURE_SEGMENTS = frozenset(
    {"fixtures", "fixture", "testdata", "test-data", "__fixtures__", "snapshots", "golden"}
)
_TEST_SEGMENTS = frozenset({"tests", "test", "__tests__", "spec", "specs", "e2e"})
_TEST_NAME_RE = re.compile(r"^test_|_test$|\.test$|\.spec$|^conftest$")

# DEC-021 vendored path-segment markers. `vendor/` and `node_modules/` are
# already pruned by DEFAULT_IGNORE_DIRS so they never reach classify_role.
_VENDORED_SEGMENTS = frozenset(
    {"third_party", "third-party", "thirdparty", "bundled", "external", "_vendor", "vendored"}
)
# Embedded version strings in path segments, e.g. `opus-1.3.1/celt/...`. A
# segment is "looks vendored" when it matches `<name>-<semver>` with an
# optional pre-release tag.
_EMBEDDED_VERSION_RE = re.compile(r"^[A-Za-z0-9_]+-\d+\.\d+(\.\d+)?([-+][\w.]+)?$")

# DEC-054 finding. Inside a JVM source root the path segments after it are Java
# *package* names, where ``samples`` / ``example`` / ``demo`` are ubiquitous
# (``org.springframework.samples.petclinic``, ``com.example.demo`` — the default
# Spring Initializr package) and must NOT trigger the ``example`` role. Only an
# example *directory* before the source root counts (``examples/app/src/main/...``).
_JVM_SOURCE_ROOT_RE = re.compile(r"(?:^|/)src/(?:main|test)/(?:java|kotlin|scala|groovy)/")

# DEC-021 generated-file filename patterns. Augment as new generators surface.
_GENERATED_NAME_RE = re.compile(
    r"""
    \.g\.dart$                 # build_runner / freezed
    | \.freezed\.dart$         # freezed
    | \.gr\.dart$              # auto_route
    | \.pb\.dart$              # dart-protoc
    | _pb\.py$                 # google protoc python
    | _pb2\.py$                # google protoc python (newer)
    | _pb2_grpc\.py$           # grpc python
    | \.pb\.go$                # go protoc
    | _pb\.go$                 # go protoc (alt)
    | \.pb\.cc$                # c++ protoc
    | \.pb\.h$                 # c++ protoc
    | \.generated\.            # ubiquitous suffix
    | \.gen\.                  # alt
    | _generated\.py$          # python convention
    | \.eg\.dart$              # equatable-gen
    """,
    re.VERBOSE,
)
# Cheap content sniff for the "GENERATED — DO NOT EDIT" marker. Case-
# insensitive because every generator capitalizes differently. Anchored to
# the start of the file so we don't false-positive on the words appearing in
# normal code comments mid-file.
_GENERATED_MARKER_RE = re.compile(
    rb"(?i)\b(?:auto[-\s]?generated|generated\s+(?:by|file|code)|do\s+not\s+edit)\b"
)


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A repo file with a recognized tree-sitter language and a role."""

    path: Path  # absolute
    rel_path: str  # repo-relative, posix-style
    language: str
    role: str  # ROLE_SOURCE | ROLE_TEST | ROLE_FIXTURE | ROLE_VENDORED | ROLE_GENERATED


@dataclass(frozen=True, slots=True)
class Inventory:
    """The result of walking a repository."""

    repo_path: Path
    files: list[SourceFile]  # every language-detected file, any role
    language_breakdown: dict[str, int]  # production source files only

    @property
    def source_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_SOURCE]

    @property
    def test_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_TEST]

    @property
    def fixture_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_FIXTURE]

    @property
    def vendored_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_VENDORED]

    @property
    def generated_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_GENERATED]

    @property
    def example_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.role == ROLE_EXAMPLE]

    @property
    def graph_files(self) -> list[SourceFile]:
        """DEC-049: the files that feed the symbol graph — production source
        *and* example/tutorial code (the latter demoted in ranking + query, not
        excluded). The four excluded roles (test/fixture/vendored/generated)
        are not here."""
        return [item for item in self.files if item.role in (ROLE_SOURCE, ROLE_EXAMPLE)]

    @property
    def file_count(self) -> int:
        """Total language-detected files, all roles."""
        return len(self.files)


def classify_role(rel_path: str) -> str:
    """Classify a repo-relative path by role (DEC-012, DEC-021).

    Pure on the path string alone — does not open the file. Generated-file
    *content* detection happens in :func:`_looks_generated` and is wired
    into the role-assignment in :func:`take_inventory` for files that look
    like source by path alone.

    Precedence: vendored > fixture > test > generated (by filename) >
    example > source (DEC-049 — example sits below the excluded roles so
    `examples/test_foo.py` is TEST and `examples/foo.g.dart` is GENERATED).
    """
    pure = PurePosixPath(rel_path)
    segments_lower = [part.lower() for part in pure.parts]
    segments_set = set(segments_lower)

    if segments_set & _VENDORED_SEGMENTS or any(
        _EMBEDDED_VERSION_RE.match(part) for part in segments_lower
    ):
        return ROLE_VENDORED
    if segments_set & _FIXTURE_SEGMENTS:
        return ROLE_FIXTURE
    if segments_set & _TEST_SEGMENTS or _TEST_NAME_RE.search(pure.stem.lower()):
        return ROLE_TEST
    if _GENERATED_NAME_RE.search(pure.name.lower()):
        return ROLE_GENERATED
    # DEC-054: example-dir markers don't count as Java package components. Under a
    # JVM source root, only segments *before* the root may mark an example app.
    jvm = _JVM_SOURCE_ROOT_RE.search(rel_path.lower())
    example_segments = (
        {seg for seg in rel_path[: jvm.start()].lower().split("/") if seg}
        if jvm
        else segments_set
    )
    if example_segments & _EXAMPLE_SEGMENTS:
        return ROLE_EXAMPLE
    return ROLE_SOURCE


def _looks_generated(abs_path: Path) -> bool:
    """Cheap content sniff for the "DO NOT EDIT" marker (DEC-021).

    Reads the first ``_GENERATED_SNIFF_BYTES`` bytes once and matches a
    case-insensitive regex anchored on the early bytes. Any open / read
    error is treated as "not generated" — the file will land as source and
    failure to parse it later is handled by the static phase.
    """
    try:
        with abs_path.open("rb") as fh:
            head = fh.read(_GENERATED_SNIFF_BYTES)
    except OSError:
        return False
    return _GENERATED_MARKER_RE.search(head) is not None


def take_inventory(
    repo_path: Path,
    *,
    ignore_dirs: frozenset[str] = DEFAULT_IGNORE_DIRS,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Inventory:
    """Walk *repo_path* and return its :class:`Inventory` of classified files."""
    repo_path = Path(repo_path).resolve()
    files: list[SourceFile] = []

    for root, dirnames, filenames in os.walk(repo_path):
        # Prune in place: skip dot-dirs (.git, .venv, .forensic-deepdive, ...)
        # and the explicit vendored/build set.
        dirnames[:] = sorted(
            name for name in dirnames if name not in ignore_dirs and not name.startswith(".")
        )
        for name in sorted(filenames):
            abs_path = Path(root) / name
            language = detect_language(abs_path)
            if language is None:
                continue
            try:
                if abs_path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            rel_path = abs_path.relative_to(repo_path).as_posix()
            role = classify_role(rel_path)
            # DEC-021: marker sniff only runs for files that still look like
            # source after the path-based pass — i.e. when there's a chance
            # we'd mis-promote a generated file into the production graph.
            if role == ROLE_SOURCE and _looks_generated(abs_path):
                role = ROLE_GENERATED
            files.append(SourceFile(path=abs_path, rel_path=rel_path, language=language, role=role))

    files.sort(key=lambda item: item.rel_path)
    breakdown: dict[str, int] = {}
    for item in files:
        if item.role == ROLE_SOURCE:
            breakdown[item.language] = breakdown.get(item.language, 0) + 1
    return Inventory(repo_path=repo_path, files=files, language_breakdown=breakdown)
