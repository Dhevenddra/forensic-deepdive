"""MENTAL_MODEL.md emitter — how to think about the codebase.

v0.1 emits a deterministic skeleton from structure and history; v0.2 will
enrich it with LLM synthesis (DEC-009). One of the five contract artifacts.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from forensic_deepdive.emit.common import (
    INFERRED,
    RepoFacts,
    confidence_banner,
    confidence_note,
    footer,
    humanize_age,
    humanize_int,
    md_table,
    primary_language,
    ranked_files,
)

# Filename stems that conventionally mark a program entry point.
_ENTRY_STEMS = frozenset({"main", "app", "cli", "index", "__main__", "server", "run", "manage"})


def render_mental_model(facts: RepoFacts) -> str:
    """Render the full MENTAL_MODEL.md document."""
    lines = [
        f"# MENTAL_MODEL — {facts.repo_name}",
        "",
        "> How to think about this codebase. v0.1 emits a deterministic "
        "skeleton from structure and history; v0.2 will enrich it with LLM "
        "synthesis.",
        confidence_banner(),
        "",
        *_at_a_glance(facts),
        *_entry_points(facts),
        *_core_modules(facts),
        *_layers(facts),
        footer(facts),
    ]
    return "\n".join(lines) + "\n"


def _at_a_glance(facts: RepoFacts) -> list[str]:
    out = [
        "## At a glance",
        "",
        f"- A **{primary_language(facts)}** codebase of "
        f"{humanize_int(facts.file_count)} source file(s).",
    ]
    if facts.history.is_git_repo:
        contributors = humanize_int(len(facts.history.contributors))
        age = humanize_age(facts.history.first_commit, facts.history.last_commit)
        out.append(f"- {contributors} contributor(s) over {age}.")
    out.append("")
    return out


def _entry_points(facts: RepoFacts) -> list[str]:
    entries = sorted(
        path
        for path in facts.symbol_graph.files
        if PurePosixPath(path).stem.lower() in _ENTRY_STEMS
    )
    out = ["## Likely entry points", "", confidence_note(INFERRED), ""]
    if entries:
        out.append(
            "Files whose names conventionally mark an entry point "
            "(stem matches `main` / `app` / `cli` / `index` / `__main__` / "
            "`server` / `run` / `manage`):"
        )
        out.append("")
        out += [f"- `{path}`" for path in entries]
    else:
        out.append("_No obvious entry-point file names detected._")
    out.append("")
    return out


def _core_modules(facts: RepoFacts, limit: int = 8) -> list[str]:
    ranked = ranked_files(facts)
    out = [
        "## Core modules",
        "",
        confidence_note(INFERRED),
        "",
        "The load-bearing files — highest dependency centrality (PageRank over the symbol graph):",
        "",
    ]
    if ranked:
        out += [
            f"{rank}. `{path}` (centrality {score:.4f})"
            for rank, (path, score) in enumerate(ranked[:limit], start=1)
        ]
    else:
        out.append("_No symbol graph available._")
    out.append("")
    return out


def _layers(facts: RepoFacts) -> list[str]:
    dir_counts: Counter[str] = Counter()
    for path in facts.symbol_graph.files:
        parts = PurePosixPath(path).parts
        dir_counts[parts[0] if len(parts) > 1 else "(repo root)"] += 1
    rows = [
        [f"`{name}`", humanize_int(count)]
        for name, count in sorted(dir_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return [
        "## Layers",
        "",
        "Top-level directories by analyzed-file count:",
        "",
        md_table(["Directory", "Files"], rows),
        "",
    ]
