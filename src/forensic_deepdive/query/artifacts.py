"""Grep-based query over generated artifacts (v0.1).

A tiny substring search across the five (+ optional DEEP) contract artifacts
so users can ask ``forensic query "term"`` without opening every file.
v0.2 will replace this with MCP-style section extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Filenames searched, in the order results are reported.
ARTIFACT_FILENAMES: tuple[str, ...] = (
    "AGENT_BRIEF.md",
    "AGENT_BRIEF_DEEP.md",
    "MAP.md",
    "HOTPATHS.md",
    "ARCHAEOLOGY.md",
    "MENTAL_MODEL.md",
)


@dataclass(frozen=True, slots=True)
class QueryHit:
    """One matching line from one artifact."""

    file: str  # filename, not the full path
    line: int  # 1-based
    text: str  # the matching line, as-is
    context_before: list[str]
    context_after: list[str]


@dataclass(frozen=True, slots=True)
class QueryResult:
    """The outcome of one query."""

    artifacts_dir: Path
    term: str
    hits: list[QueryHit]
    files_searched: list[str]


def resolve_artifacts_dir(given: Path) -> Path:
    """Accept either an artifacts dir or a repo root.

    If *given* already contains ``AGENT_BRIEF.md`` it is used directly;
    otherwise ``<given>/docs/codebase`` is tried (the pipeline default).
    Returns the original path if neither holds, letting the caller raise.
    """
    given = Path(given)
    if (given / "AGENT_BRIEF.md").is_file():
        return given
    fallback = given / "docs" / "codebase"
    if (fallback / "AGENT_BRIEF.md").is_file():
        return fallback
    return given


def query_artifacts(
    artifacts_dir: Path,
    term: str,
    *,
    context: int = 2,
    case_sensitive: bool = False,
) -> QueryResult:
    """Search *artifacts_dir* for lines containing *term*.

    Args:
        artifacts_dir: Where the artifacts live; a repo root is also accepted
            (see :func:`resolve_artifacts_dir`).
        term: Substring to search for.
        context: Number of lines of context to keep before/after each hit.
        case_sensitive: Default False (the comfortable CLI default).

    Raises:
        NotADirectoryError: *artifacts_dir* does not exist as a directory.
    """
    artifacts_dir = resolve_artifacts_dir(artifacts_dir)
    if not artifacts_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {artifacts_dir}")

    needle = term if case_sensitive else term.lower()
    hits: list[QueryHit] = []
    searched: list[str] = []

    for name in ARTIFACT_FILENAMES:
        path = artifacts_dir / name
        if not path.is_file():
            continue
        searched.append(name)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            haystack = line if case_sensitive else line.lower()
            if needle not in haystack:
                continue
            start = max(0, idx - context)
            hits.append(
                QueryHit(
                    file=name,
                    line=idx + 1,
                    text=line,
                    context_before=lines[start:idx],
                    context_after=lines[idx + 1 : idx + 1 + context],
                )
            )

    return QueryResult(
        artifacts_dir=artifacts_dir,
        term=term,
        hits=hits,
        files_searched=searched,
    )
