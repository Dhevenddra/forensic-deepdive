"""Repository inventory — the first pipeline stage.

Walks a repo, skipping VCS / vendored / build directories, classifies each file
by tree-sitter language, and assigns a **role** — source, test, or fixture — so
later stages can keep test scaffolding out of the production symbol graph
(DEC-012).
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

# File roles (DEC-012).
ROLE_SOURCE = "source"
ROLE_TEST = "test"
ROLE_FIXTURE = "fixture"

_FIXTURE_SEGMENTS = frozenset(
    {"fixtures", "fixture", "testdata", "test-data", "__fixtures__", "snapshots", "golden"}
)
_TEST_SEGMENTS = frozenset({"tests", "test", "__tests__", "spec", "specs", "e2e"})
_TEST_NAME_RE = re.compile(r"^test_|_test$|\.test$|\.spec$|^conftest$")


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A repo file with a recognized tree-sitter language and a role."""

    path: Path  # absolute
    rel_path: str  # repo-relative, posix-style
    language: str
    role: str  # ROLE_SOURCE | ROLE_TEST | ROLE_FIXTURE


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
    def file_count(self) -> int:
        """Total language-detected files, all roles."""
        return len(self.files)


def classify_role(rel_path: str) -> str:
    """Classify a repo-relative path as source, test, or fixture (DEC-012)."""
    pure = PurePosixPath(rel_path)
    segments = {part.lower() for part in pure.parts}
    if segments & _FIXTURE_SEGMENTS:
        return ROLE_FIXTURE
    if segments & _TEST_SEGMENTS or _TEST_NAME_RE.search(pure.stem.lower()):
        return ROLE_TEST
    return ROLE_SOURCE


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
            files.append(
                SourceFile(
                    path=abs_path,
                    rel_path=rel_path,
                    language=language,
                    role=classify_role(rel_path),
                )
            )

    files.sort(key=lambda item: item.rel_path)
    breakdown: dict[str, int] = {}
    for item in files:
        if item.role == ROLE_SOURCE:
            breakdown[item.language] = breakdown.get(item.language, 0) + 1
    return Inventory(repo_path=repo_path, files=files, language_breakdown=breakdown)
