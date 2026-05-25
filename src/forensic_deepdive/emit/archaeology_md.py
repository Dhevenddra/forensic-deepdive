"""ARCHAEOLOGY.md emitter — what git history reveals.

Age, contributors, and churn from the plain-git Layer-3 backend, plus optional
GitHub metadata. One of the five contract artifacts.
"""

from __future__ import annotations

from forensic_deepdive.emit.common import (
    INFERRED,
    RepoFacts,
    confidence_banner,
    confidence_note,
    fmt_date,
    footer,
    humanize_age,
    humanize_int,
    md_table,
)


def render_archaeology(facts: RepoFacts) -> str:
    """Render the full ARCHAEOLOGY.md document."""
    head = [
        f"# ARCHAEOLOGY — {facts.repo_name}",
        "",
        "> What git history reveals: age, contributors, and churn.",
        confidence_banner(),
        "",
    ]
    if not facts.history.is_git_repo:
        body = [
            "## History",
            "",
            "_This directory is not a git repository — no history available._",
            "",
        ]
    else:
        body = [
            *_timeline(facts),
            *_contributors(facts),
            *_automation(facts),
            *_changed_files(facts),
            *_github(facts),
        ]
    return "\n".join([*head, *body, footer(facts)]) + "\n"


def _timeline(facts: RepoFacts) -> list[str]:
    history = facts.history
    return [
        "## Timeline",
        "",
        f"- **First commit:** {fmt_date(history.first_commit)}",
        f"- **Latest commit:** {fmt_date(history.last_commit)}",
        f"- **Age:** {humanize_age(history.first_commit, history.last_commit)}",
        f"- **Total commits:** {humanize_int(history.total_commits)} (non-merge)",
        "",
    ]


def _contributors(facts: RepoFacts, limit: int = 15) -> list[str]:
    history = facts.history
    total = history.total_commits or 1
    rows: list[list[str]] = []
    for contributor in history.contributors[:limit]:
        share = 100.0 * contributor.commits / total
        rows.append([contributor.name, humanize_int(contributor.commits), f"{share:.1f}%"])
    return [
        "## Contributors",
        "",
        f"{humanize_int(len(history.contributors))} contributor(s) total.",
        "",
        md_table(["Contributor", "Commits", "Share"], rows),
        "",
    ]


def _automation(facts: RepoFacts, limit: int = 10) -> list[str]:
    """DEC-022. Render the bot-accounts section *only* when bots exist —
    the artifact stays clean for repos without automated commits."""
    bots = facts.history.bots
    if not bots:
        return []
    total = facts.history.total_commits or 1
    rows: list[list[str]] = []
    for bot in bots[:limit]:
        share = 100.0 * bot.commits / total
        rows.append([bot.name, humanize_int(bot.commits), f"{share:.1f}%"])
    return [
        "## Automation",
        "",
        confidence_note(INFERRED),
        "",
        f"{humanize_int(len(bots))} bot account(s) — separated from human "
        "attribution per DEC-022. Bot classification is a regex heuristic "
        "(`[bot]` suffix, `-bot` suffix, known infra emails); a human "
        "account that matches one of those patterns will appear here.",
        "",
        md_table(["Bot", "Commits", "Share"], rows),
        "",
    ]


def _changed_files(facts: RepoFacts, limit: int = 15) -> list[str]:
    rows = [
        [f"`{churn.path}`", humanize_int(churn.commits)] for churn in facts.history.churn[:limit]
    ]
    return [
        "## Most-changed files",
        "",
        "Files with the most commits across history — long-lived churn.",
        "",
        md_table(["File", "Commits"], rows),
        "",
    ]


def _github(facts: RepoFacts) -> list[str]:
    github = facts.history.github
    if github is None:
        return [
            "## GitHub",
            "",
            "_No GitHub remote detected (or metadata unavailable) — local history only._",
            "",
        ]
    out = [
        "## GitHub",
        "",
        f"- **Repository:** `{github.owner}/{github.name}`",
    ]
    if github.description:
        out.append(f"- **Description:** {github.description}")
    out += [
        f"- **Stars:** {humanize_int(github.stars)}",
        f"- **Open issues:** {humanize_int(github.open_issues)}",
        f"- **Default branch:** `{github.default_branch}`",
        f"- **Created:** {fmt_date(github.created_at)}",
        f"- **Last push:** {fmt_date(github.pushed_at)}",
        "",
    ]
    return out
