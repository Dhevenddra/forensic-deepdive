"""AGENT_BRIEF.md emitter — the headline artifact for AI coding agents.

Hard ≤5 KB cap (CLAUDE.md "Sacred abstractions"): beyond it, instruction
following degrades. Sections are packed in priority order; whatever does not
fit overflows into AGENT_BRIEF_DEEP.md. DEC-015: each rule in the list
carries its own confidence tag — git-fact rules stay ``EXTRACTED`` while
ranking-derived rules (PageRank centrality, top-called symbol, co-change
pairs) are ``INFERRED``.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from forensic_deepdive.emit.common import (
    AGENT_BRIEF_BYTE_CAP,
    EXTRACTED,
    INFERRED,
    RepoFacts,
    byte_len,
    confidence_tag,
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
            "> Each rule carries a confidence tag (DEC-015): `[EXTRACTED]` "
            "from AST/git, `[INFERRED]` from a ranking or heuristic.",
            "> Full detail: `MAP.md`, `HOTPATHS.md`, `ARCHAEOLOGY.md`, `MENTAL_MODEL.md`.",
        ]
    )


def _deep_header(facts: RepoFacts) -> str:
    return "\n".join(
        [
            f"# AGENT_BRIEF_DEEP — {facts.repo_name}",
            "",
            "> Overflow from `AGENT_BRIEF.md` — sections that did not fit the "
            "5 KB cap. Lower priority, same per-rule confidence tags.",
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
    if always:
        lines += [f"- {rule} {confidence_tag(level)}" for rule, level in always]
    else:
        lines += ["- _(none derived)_"]
    lines += ["", "### Never", ""]
    if never:
        lines += [f"- {rule} {confidence_tag(level)}" for rule, level in never]
    else:
        lines += ["- _(none derived)_"]
    return "\n".join(lines)


def _derive_rules(
    facts: RepoFacts,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Turn deterministic facts into assertive Always / Never directives,
    each paired with its honest DEC-015 confidence level.

    Per DEC-015: PageRank-derived rankings, heuristic interpretations, and
    co-change derivations are INFERRED. Raw git counts and the literal
    "not a git repo" claim are EXTRACTED.

    DEC-030: in graph mode, the "load-bearing file" + "central symbol"
    rules promote to a single "load-bearing SYMBOL" rule grounded in
    real CALLS counts. That rule is still INFERRED — the count is a fact
    but the framing as "load-bearing" is the derivation."""
    always: list[tuple[str, str]] = []
    never: list[tuple[str, str]] = []
    ranked = ranked_files(facts)

    graph_call_rules = _graph_call_rules(facts)
    graph_co_change_rules = _graph_co_change_rules(facts)

    if graph_call_rules:
        always.extend(graph_call_rules)
    else:
        # NetworkX fallback — PageRank rankings are INFERRED (DEC-015).
        if ranked:
            top_file = ranked[0][0]
            in_edges = facts.symbol_graph.graph.in_degree(top_file)
            always.append(
                (
                    f"Treat `{top_file}` as load-bearing — it is the most "
                    f"depended-on file ({in_edges} inbound dependency edges); "
                    "changes there ripple widely",
                    INFERRED,
                )
            )
        if facts.ranked.definitions:
            top = facts.ranked.definitions[0]
            always.append(
                (
                    f"Expect `{top.name}` (in `{top.rel_path}`) to be central — "
                    "it carries the most dependency weight",
                    INFERRED,
                )
            )
    always.extend(graph_co_change_rules)

    if facts.history.is_git_repo and facts.history.churn:
        hottest = facts.history.churn[0]
        never.append(
            (
                f"Never assume `{hottest.path}` is stable — it is the repo's "
                f"biggest churn point ({hottest.commits} commits)",
                EXTRACTED,
            )
        )
    risky = _risky_files(facts)
    if risky:
        listed = ", ".join(f"`{path}`" for path in risky[:3])
        never.append(
            (
                f"Never edit {listed} casually — they are both highly central and high-churn",
                INFERRED,
            )
        )
    if not facts.history.is_git_repo:
        never.append(
            (
                "Never rely on git history here — this directory is not a git repository",
                EXTRACTED,
            )
        )
    return always, never


def _graph_call_rules(facts: RepoFacts) -> list[tuple[str, str]]:
    """DEC-029 + DEC-015. Top-called symbol from the LadybugDB CALLS graph.
    Returned as an INFERRED rule — the count is EXTRACTED but the
    "load-bearing" framing is a ranking interpretation."""
    if facts.graph_db_path is None:
        return []
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                    "RETURN callee.qualified_name, count(r) AS inbound "
                    "ORDER BY inbound DESC, callee.qualified_name LIMIT 1"
                )
            )
    except Exception:  # pragma: no cover
        return []
    if not rows or int(rows[0][1]) < 2:
        return []
    qn, inbound = rows[0]
    short = qn.rsplit("::", 1)[-1]
    return [
        (
            f"Treat `{short}` as the most-called symbol "
            f"({int(inbound)} inbound calls per the DEC-025 resolver) — "
            "signature changes touch every caller",
            INFERRED,
        )
    ]


def _graph_co_change_rules(facts: RepoFacts) -> list[tuple[str, str]]:
    """DEC-029 + DEC-015. Tightest co-change pair from CO_CHANGES_WITH.
    Always INFERRED per DEC-027 — the count is a git fact, the
    "should change together" implication is the derivation."""
    if facts.graph_db_path is None:
        return []
    from forensic_deepdive.graph import LadybugStore

    try:
        with LadybugStore(facts.graph_db_path) as store:
            rows = list(
                store.query(
                    "MATCH (a:File)-[r:CO_CHANGES_WITH]->(b:File) "
                    "RETURN a.path, b.path, r.frequency "
                    "ORDER BY r.frequency DESC, a.path, b.path LIMIT 1"
                )
            )
    except Exception:  # pragma: no cover
        return []
    if not rows:
        return []
    a, b, freq = rows[0]
    return [
        (
            f"When you touch `{a}`, also check `{b}` — they co-change in "
            f"{int(freq)} shared commit(s) per the DEC-027 join",
            INFERRED,
        )
    ]


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
