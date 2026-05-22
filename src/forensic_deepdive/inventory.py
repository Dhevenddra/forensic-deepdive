"""Repository inventory — the first pipeline stage.

Walks a repo, skipping VCS / vendored / build directories, and classifies each
file by tree-sitter language. Produces the source-file list the static layer
parses and the language breakdown the emitters report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A repo file with a recognized tree-sitter language."""

    path: Path  # absolute
    rel_path: str  # repo-relative, posix-style
    language: str


@dataclass(frozen=True, slots=True)
class Inventory:
    """The result of walking a repository."""

    repo_path: Path
    source_files: list[SourceFile]
    language_breakdown: dict[str, int]  # language -> file count

    @property
    def file_count(self) -> int:
        return len(self.source_files)


def take_inventory(
    repo_path: Path,
    *,
    ignore_dirs: frozenset[str] = DEFAULT_IGNORE_DIRS,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Inventory:
    """Walk *repo_path* and return its :class:`Inventory` of source files."""
    repo_path = Path(repo_path).resolve()
    source_files: list[SourceFile] = []

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
            source_files.append(
                SourceFile(
                    path=abs_path,
                    rel_path=abs_path.relative_to(repo_path).as_posix(),
                    language=language,
                )
            )

    source_files.sort(key=lambda item: item.rel_path)
    breakdown: dict[str, int] = {}
    for item in source_files:
        breakdown[item.language] = breakdown.get(item.language, 0) + 1
    return Inventory(
        repo_path=repo_path,
        source_files=source_files,
        language_breakdown=breakdown,
    )
