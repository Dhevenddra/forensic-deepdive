"""Shared helpers and the data contract for the artifact emitters.

Every emitter consumes one :class:`RepoFacts` bundle and returns markdown.
``RepoFacts`` is the contract between the (forthcoming) extract pipeline and
the emit layer.

Confidence taxonomy (DEC-007): every emitted fact carries a confidence level.
v0.1 produces only ``EXTRACTED`` facts (deterministic from AST / git), so the
four long-form artifacts state this once in a banner rather than tagging every
line, and ``AGENT_BRIEF`` tags each rule explicitly. v0.2 introduces
``INFERRED`` / ``AMBIGUOUS`` per item.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from forensic_deepdive import __version__
from forensic_deepdive.flatten.repomix_backend import FlattenResult
from forensic_deepdive.history.git_archaeology import GitHistory
from forensic_deepdive.static.graph import SymbolGraph
from forensic_deepdive.static.pagerank import RankedRepo
from forensic_deepdive.static.tags import Tag

# The five-artifact contract — names, count, and order are the public API
# (CLAUDE.md "Sacred abstractions"). AGENT_BRIEF_DEEP is the overflow target.
ARTIFACT_NAMES: tuple[str, ...] = (
    "MAP",
    "HOTPATHS",
    "ARCHAEOLOGY",
    "MENTAL_MODEL",
    "AGENT_BRIEF",
)
AGENT_BRIEF_DEEP_NAME = "AGENT_BRIEF_DEEP"

# AGENT_BRIEF.md hard cap — 5 KB. Beyond this, instruction-following degrades.
AGENT_BRIEF_BYTE_CAP = 5120

# Confidence levels (DEC-007, taxonomy adopted from Graphify).
EXTRACTED = "EXTRACTED"
INFERRED = "INFERRED"
AMBIGUOUS = "AMBIGUOUS"

_LANG_DISPLAY = {"python": "Python", "c": "C", "dart": "Dart", "swift": "Swift"}


@dataclass(frozen=True, slots=True)
class RepoFacts:
    """Everything the emitters need to know about one repository."""

    repo_path: Path
    repo_name: str
    generated_at: datetime
    file_count: int  # production source files (DEC-012)
    language_breakdown: dict[str, int]  # grammar name -> source-file count
    tags: list[Tag]
    symbol_graph: SymbolGraph
    ranked: RankedRepo
    history: GitHistory
    flatten: FlattenResult | None = None
    test_file_count: int = 0  # test files — inventoried, excluded from the graph
    fixture_file_count: int = 0  # fixture files — inventoried, excluded
    vendored_file_count: int = 0  # DEC-021 — inventoried, excluded
    generated_file_count: int = 0  # DEC-021 — inventoried, excluded
    # DEC-029: when the BuildGraphPhase ran, the LadybugDB graph lives
    # here and emitters can query it for symbol-level / call-graph /
    # co-change content. ``None`` when graph mode is off — emitters fall
    # back to file-level NetworkX (v0.1 behavior).
    graph_db_path: Path | None = None


def language_label(grammar: str) -> str:
    """Return a human-readable name for a tree-sitter grammar id."""
    return _LANG_DISPLAY.get(grammar, grammar.replace("_", " ").title())


def primary_language(facts: RepoFacts) -> str:
    """Return the label of the most common language, or a neutral fallback."""
    if not facts.language_breakdown:
        return "multi-language"
    top = max(facts.language_breakdown.items(), key=lambda kv: (kv[1], kv[0]))
    return language_label(top[0])


def byte_len(text: str) -> int:
    """Return the UTF-8 byte length of *text* (what the 5 KB cap measures)."""
    return len(text.encode("utf-8"))


def humanize_int(value: int) -> str:
    """Format an integer with thousands separators."""
    return f"{value:,}"


def humanize_age(first: datetime | None, last: datetime | None) -> str:
    """Render the span between two commit dates as a rough human duration."""
    if first is None or last is None:
        return "unknown age"
    days = (last - first).days
    if days < 0:
        return "unknown age"
    if days >= 365:
        return f"~{days / 365.25:.1f} years"
    if days >= 60:
        return f"~{days // 30} months"
    if days >= 1:
        return f"{days} days"
    return "under a day"


def fmt_date(value: datetime | None) -> str:
    """Render a date as ``YYYY-MM-DD``, or ``unknown``."""
    return value.strftime("%Y-%m-%d") if value is not None else "unknown"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavored markdown table; ``_None._`` when there are no rows."""
    if not rows:
        return "_None._"
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{head}\n{rule}\n{body}"


def confidence_banner(level: str = EXTRACTED) -> str:
    """Return the one-line confidence banner placed under each artifact title."""
    if level == EXTRACTED:
        return (
            "> **Confidence:** every fact below is `EXTRACTED` — deterministic "
            "from Tree-sitter AST and git history (DEC-007)."
        )
    return f"> **Confidence:** `{level}` (DEC-007)."


def footer(facts: RepoFacts) -> str:
    """Return the standard generated-artifact footer."""
    return (
        "---\n\n"
        f"*Generated by forensic-deepdive {__version__} on "
        f"{fmt_date(facts.generated_at)}. Regenerate with `forensic update` — "
        "do not hand-edit.*"
    )


def ranked_files(facts: RepoFacts) -> list[tuple[str, float]]:
    """Return (file, PageRank score) pairs, most central first, deterministic."""
    return sorted(facts.ranked.file_rank.items(), key=lambda kv: (-kv[1], kv[0]))
