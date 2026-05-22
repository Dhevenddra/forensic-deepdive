"""AGENT_BRIEF.md emitter — the headline artifact for AI coding agents.

Hard ≤5 KB cap (CLAUDE.md "Sacred abstractions"): beyond it, instruction
following degrades. Sections are packed in priority order; whatever does not
fit overflows into AGENT_BRIEF_DEEP.md. v0.1 derives only ``EXTRACTED`` rules.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from forensic_deepdive.emit.common import (
    AGENT_BRIEF_BYTE_CAP,
    RepoFacts,
    byte_len,
    footer,
    humanize_age,
    humanize_int,
    primary_language,
    ranked_files,
)

_OVERFLOW_POINTER = (
    "\n> ⚠ Truncated to fit the 5 KB cap — the rest is in **AGENT_BRIEF_DEEP.md**.\n"
)


def render_agent_brief(
    facts: RepoFacts,
    *,
    byte_cap: int = AGENT_BRIEF_BYTE_CAP,
) -> tuple[str, str | None]:
    """Render AGENT_BRIEF.md, returning ``(brief, deep_or_None)``.

    The brief is guaranteed to be ``<= byte_cap`` bytes as long as the header
    fits. Any section that does not fit is moved, in order, into the optional
    AGENT_BRIEF_DEEP.md overflow document.
    """
    header = _header(facts)
    sections = _sections(facts)
    tail = "\n\n" + footer(facts) + "\n"
    budget = byte_cap - byte_len(tail) - byte_len(_OVERFLOW_POINTER)

    kept = [header]
    overflow: list[str] = []
    used = byte_len(header)
    for section in sections:
        chunk = "\n\n" + section
        if overflow or used + byte_len(chunk) > budget:
            overflow.append(section)  # once one section spills, keep order intact
        else:
            kept.append(section)
            used += byte_len(chunk)

    brief = "\n\n".join(kept)
    deep: str | None = None
    if overflow:
        brief += _OVERFLOW_POINTER
        deep = "\n\n".join([_deep_header(facts), *overflow]) + tail
    brief += tail
    return brief, deep


def _header(facts: RepoFacts) -> str:
    return "\n".join(
        [
            f"# AGENT_BRIEF — {facts.repo_name}",
            "",
            "> Forensic brief for AI coding agents. **Read this first.**",
            "> Every rule is `EXTRACTED` — deterministic from AST and git (DEC-007).",
            "> Full detail: `MAP.md`, `HOTPATHS.md`, `ARCHAEOLOGY.md`, `MENTAL_MODEL.md`.",
        ]
    )


def _deep_header(facts: RepoFacts) -> str:
    return "\n".join(
        [
            f"# AGENT_BRIEF_DEEP — {facts.repo_name}",
            "",
            "> Overflow from `AGENT_BRIEF.md` — sections that did not fit the "
            "5 KB cap. Lower priority, same `EXTRACTED` confidence.",
        ]
    )


def _sections(facts: RepoFacts) -> list[str]:
    """Section bodies in priority order — earlier survives truncation."""
    return [
        _what_this_is(facts),
        _rules(facts),
        _central_files(facts),
        _where_things_live(facts),
    ]


def _what_this_is(facts: RepoFacts) -> str:
    bits = [
        f"A **{primary_language(facts)}** codebase, {humanize_int(facts.file_count)} source file(s)"
    ]
    if facts.test_file_count:
        bits.append(f"{humanize_int(facts.test_file_count)} test file(s)")
    if facts.history.is_git_repo:
        bits.append(f"{humanize_int(len(facts.history.contributors))} contributor(s)")
        bits.append(humanize_age(facts.history.first_commit, facts.history.last_commit) + " old")
    return "## What this is\n\n" + ", ".join(bits) + "."


def _rules(facts: RepoFacts) -> str:
    always, never = _derive_rules(facts)
    lines = ["## Rules", "", "### Always", ""]
    lines += [f"- {rule} `[EXTRACTED]`" for rule in always] or ["- _(none derived)_"]
    lines += ["", "### Never", ""]
    lines += [f"- {rule} `[EXTRACTED]`" for rule in never] or ["- _(none derived)_"]
    return "\n".join(lines)


def _derive_rules(facts: RepoFacts) -> tuple[list[str], list[str]]:
    """Turn deterministic facts into assertive Always / Never directives."""
    always: list[str] = []
    never: list[str] = []
    ranked = ranked_files(facts)

    if ranked:
        top_file = ranked[0][0]
        in_edges = facts.symbol_graph.graph.in_degree(top_file)
        always.append(
            f"Treat `{top_file}` as load-bearing — it is the most depended-on "
            f"file ({in_edges} inbound dependency edges); changes there ripple "
            f"widely"
        )
    if facts.ranked.definitions:
        top = facts.ranked.definitions[0]
        always.append(
            f"Expect `{top.name}` (in `{top.rel_path}`) to be central — it "
            f"carries the most dependency weight"
        )

    if facts.history.is_git_repo and facts.history.churn:
        hottest = facts.history.churn[0]
        never.append(
            f"Never assume `{hottest.path}` is stable — it is the repo's "
            f"biggest churn point ({hottest.commits} commits)"
        )
    risky = _risky_files(facts)
    if risky:
        listed = ", ".join(f"`{path}`" for path in risky[:3])
        never.append(f"Never edit {listed} casually — they are both highly central and high-churn")
    if not facts.history.is_git_repo:
        never.append("Never rely on git history here — this directory is not a git repository")
    return always, never


def _risky_files(facts: RepoFacts, window: int = 20) -> list[str]:
    """Files in both the top-centrality and top-churn windows."""
    if not facts.history.is_git_repo:
        return []
    churn_paths = {churn.path for churn in facts.history.churn[:window]}
    return [path for path, _ in ranked_files(facts)[:window] if path in churn_paths]


def _central_files(facts: RepoFacts, limit: int = 5) -> str:
    ranked = ranked_files(facts)
    lines = ["## Most central files", ""]
    if ranked:
        lines += [
            f"{rank}. `{path}`" for rank, (path, _score) in enumerate(ranked[:limit], start=1)
        ]
    else:
        lines.append("_No symbol graph._")
    return "\n".join(lines)


def _where_things_live(facts: RepoFacts, limit: int = 6) -> str:
    dir_counts: Counter[str] = Counter()
    for path in facts.symbol_graph.files:
        parts = PurePosixPath(path).parts
        dir_counts[parts[0] if len(parts) > 1 else "(repo root)"] += 1
    top = sorted(dir_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    lines = ["## Where things live", ""]
    lines += [f"- `{name}` — {count} file(s)" for name, count in top] or ["- _(flat layout)_"]
    return "\n".join(lines)
