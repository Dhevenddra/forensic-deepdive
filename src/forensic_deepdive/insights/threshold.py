"""DEC-005 threshold computation: 2-of-5 gate for Graphiti opt-in.

The five sub-conditions:

1. ``loc_50k`` — total LOC across production source files ≥ 50,000.
2. ``contributors_25`` — distinct human contributors (post-mailmap,
   bots excluded per DEC-022) ≥ 25.
3. ``age_18m`` — first commit ≥ 18 months ago.
4. ``prs_200`` — closed PRs in the last 12 months ≥ 200. Requires
   ``fetch_github=True``; 0 otherwise (fails closed).
5. ``issues_100`` — closed issues with ≥ 1 comment (any "discussion")
   in the last 12 months ≥ 100. Same fetch_github requirement.

The aggregate ``passes_2_of_5`` is True when ≥ 2 sub-conditions hold.

Conservative-by-default: when GitHub data is unavailable, ``prs_200``
and ``issues_100`` resolve to ``False``, biasing the threshold against
opting into a $8/run Graphiti session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.history.git_archaeology import GitHistory
from forensic_deepdive.inventory import Inventory

# DEC-005 threshold constants — frozen by the active decision.
_LOC_THRESHOLD = 50_000
_CONTRIBUTORS_THRESHOLD = 25
_AGE_DAYS_THRESHOLD = 18 * 30  # 18 months ≈ 540 days
_PRS_THRESHOLD = 200
_ISSUES_THRESHOLD = 100


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    """Per-condition booleans + the aggregate pass/fail (DEC-005)."""

    loc: int
    contributors: int
    age_days: int
    prs_last_12mo: int
    issues_last_12mo: int

    loc_50k: bool
    contributors_25: bool
    age_18m: bool
    prs_200: bool
    issues_100: bool

    @property
    def passes_2_of_5(self) -> bool:
        return (
            int(self.loc_50k)
            + int(self.contributors_25)
            + int(self.age_18m)
            + int(self.prs_200)
            + int(self.issues_100)
        ) >= 2

    @property
    def passing_count(self) -> int:
        return (
            int(self.loc_50k)
            + int(self.contributors_25)
            + int(self.age_18m)
            + int(self.prs_200)
            + int(self.issues_100)
        )


def _compute_loc(inventory: Inventory) -> int:
    """Sum the line count across production source files. One pass,
    binary-mode count of ``\\n`` bytes per file. Files that fail to
    open contribute 0 (matches the BuildGraphPhase ``_source_to_file``
    behavior — degrade defensively, never abort the whole computation).
    """
    total = 0
    for sf in inventory.source_files:
        try:
            data = sf.path.read_bytes()
        except OSError:
            continue
        total += data.count(b"\n")
        # Add 1 if the file is non-empty AND its last byte isn't a newline,
        # so a single-line file with no trailing newline still counts as 1.
        if data and not data.endswith(b"\n"):
            total += 1
    return total


def _compute_age_days(history: GitHistory) -> int:
    """Days between the first commit and now. ``0`` when no history
    (degrades the ``age_18m`` condition to False)."""
    if not history.is_git_repo or history.first_commit is None:
        return 0
    now = datetime.now(UTC)
    delta = now - history.first_commit
    return max(0, delta.days)


def _compute_prs_last_12mo(history: GitHistory) -> int:
    """Closed PRs in the last 12 months. Requires GitHub data.

    v0.2 caveat: ``GitHubStats`` carries only the aggregate ``open_issues``
    count, not a windowed PR count. Until we extend the GitHub
    integration to fetch a windowed list (v0.3 work, tracked in
    REMAINING.md item 14 acceptance gates), this returns 0 — the
    threshold fails closed.
    """
    if history.github is None:
        return 0
    return 0  # v0.3: extend GitHubStats with prs_last_12mo


def _compute_issues_last_12mo(history: GitHistory) -> int:
    """Closed issues with discussion in the last 12 months. Same v0.3
    caveat as :func:`_compute_prs_last_12mo` — returns 0 until the
    GitHub integration is extended."""
    if history.github is None:
        return 0
    return 0  # v0.3: extend GitHubStats with closed_issues_with_discussion_last_12mo


def compute_thresholds(
    inventory: Inventory,
    history: GitHistory,
) -> ThresholdResult:
    """Compute the DEC-005 2-of-5 threshold from existing facts.

    Inputs come from the existing inventory + history phases — no extra
    repo walk. Below-threshold repos use this to short-circuit the
    Graphiti opt-in path; above-threshold repos surface the result to
    the user so they can choose to enable Graphiti consciously.
    """
    loc = _compute_loc(inventory)
    contributors = len(history.contributors) if history.is_git_repo else 0
    age_days = _compute_age_days(history)
    prs = _compute_prs_last_12mo(history)
    issues = _compute_issues_last_12mo(history)
    return ThresholdResult(
        loc=loc,
        contributors=contributors,
        age_days=age_days,
        prs_last_12mo=prs,
        issues_last_12mo=issues,
        loc_50k=loc >= _LOC_THRESHOLD,
        contributors_25=contributors >= _CONTRIBUTORS_THRESHOLD,
        age_18m=age_days >= _AGE_DAYS_THRESHOLD,
        prs_200=prs >= _PRS_THRESHOLD,
        issues_100=issues >= _ISSUES_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Standalone variant — for callers that only have a repo path
# ---------------------------------------------------------------------------


def compute_thresholds_from_repo(
    repo_path: Path,
    *,
    fetch_github: bool = False,
    github_token: str | None = None,
) -> ThresholdResult:
    """Run inventory + history phases from a repo path and compute the
    threshold. Used by the CLI / MCP layers that may not have a
    :class:`RepoFacts` bundle at hand."""
    from forensic_deepdive.history.git_archaeology import analyze_history
    from forensic_deepdive.inventory import take_inventory

    inventory = take_inventory(repo_path)
    history = analyze_history(
        repo_path,
        fetch_github=fetch_github,
        github_token=github_token,
    )
    return compute_thresholds(inventory, history)
