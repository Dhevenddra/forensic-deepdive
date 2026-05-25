"""Tests for the DEC-005 2-of-5 threshold computation (DEC-019)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from forensic_deepdive.history.git_archaeology import (
    Contributor,
    GitHistory,
    GitHubStats,
)
from forensic_deepdive.insights import compute_thresholds
from forensic_deepdive.insights.threshold import compute_thresholds_from_repo
from forensic_deepdive.inventory import Inventory, SourceFile


def _make_inventory_with_loc(tmp_path: Path, total_loc: int) -> Inventory:
    """Create a single-file Inventory with the requested LOC count."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = tmp_path / "big.py"
    src.write_text("\n" * total_loc, encoding="utf-8")
    return Inventory(
        repo_path=tmp_path,
        files=[
            SourceFile(
                path=src,
                rel_path="big.py",
                language="python",
                role="source",
            )
        ],
        language_breakdown={"python": 1},
    )


def _make_history(
    *,
    is_git: bool = True,
    first_commit: datetime | None = None,
    contributors: int = 0,
    github: GitHubStats | None = None,
) -> GitHistory:
    return GitHistory(
        repo_path=Path("."),
        is_git_repo=is_git,
        total_commits=0,
        first_commit=first_commit,
        last_commit=None,
        contributors=[Contributor(f"u{i}", f"u{i}@x.com", 1) for i in range(contributors)],
        churn=[],
        github=github,
    )


def test_threshold_loc_50k_boundary(tmp_path: Path) -> None:
    """50,000 LOC passes; 49,999 fails."""
    inv_pass = _make_inventory_with_loc(tmp_path / "pass", 50_000)
    res_pass = compute_thresholds(inv_pass, _make_history())
    assert res_pass.loc_50k is True

    inv_fail = _make_inventory_with_loc(tmp_path / "fail", 49_999)
    res_fail = compute_thresholds(inv_fail, _make_history())
    assert res_fail.loc_50k is False


def test_threshold_contributors_25_boundary(tmp_path: Path) -> None:
    inv = _make_inventory_with_loc(tmp_path, 0)
    res_pass = compute_thresholds(inv, _make_history(contributors=25))
    assert res_pass.contributors_25 is True
    res_fail = compute_thresholds(inv, _make_history(contributors=24))
    assert res_fail.contributors_25 is False


def test_threshold_age_18m_boundary(tmp_path: Path) -> None:
    inv = _make_inventory_with_loc(tmp_path, 0)
    # 18 months = 540 days per DEC-005's threshold constant.
    eighteen_months_ago = datetime.now(UTC) - timedelta(days=540)
    one_day_short = datetime.now(UTC) - timedelta(days=539)
    res_pass = compute_thresholds(inv, _make_history(first_commit=eighteen_months_ago))
    assert res_pass.age_18m is True
    res_fail = compute_thresholds(inv, _make_history(first_commit=one_day_short))
    assert res_fail.age_18m is False


def test_threshold_no_git_repo_means_zero_age_and_contributors(tmp_path: Path) -> None:
    """Defensive default: a non-git directory fails contributor / age
    sub-conditions regardless of file count."""
    inv = _make_inventory_with_loc(tmp_path, 100_000)  # loc passes
    res = compute_thresholds(inv, _make_history(is_git=False))
    assert res.contributors == 0
    assert res.age_days == 0
    assert res.loc_50k is True
    assert res.contributors_25 is False
    assert res.age_18m is False


def test_threshold_github_missing_fails_pr_and_issue_closed(tmp_path: Path) -> None:
    """fetch_github=False (no GitHubStats) → PRs/issues counts are 0 →
    those sub-conditions fail closed."""
    inv = _make_inventory_with_loc(tmp_path, 0)
    res = compute_thresholds(inv, _make_history(github=None))
    assert res.prs_last_12mo == 0
    assert res.issues_last_12mo == 0
    assert res.prs_200 is False
    assert res.issues_100 is False


def test_threshold_2_of_5_aggregate(tmp_path: Path) -> None:
    """Exactly 2 sub-conditions passing → ``passes_2_of_5`` True."""
    inv = _make_inventory_with_loc(tmp_path, 50_000)  # loc passes
    eighteen_months_ago = datetime.now(UTC) - timedelta(days=540)
    history = _make_history(
        first_commit=eighteen_months_ago,  # age passes
        contributors=10,  # fails
    )
    res = compute_thresholds(inv, history)
    assert res.loc_50k is True
    assert res.age_18m is True
    assert res.contributors_25 is False
    assert res.passing_count == 2
    assert res.passes_2_of_5 is True


def test_threshold_1_of_5_does_not_pass(tmp_path: Path) -> None:
    inv = _make_inventory_with_loc(tmp_path, 50_000)  # only loc passes
    res = compute_thresholds(inv, _make_history())
    assert res.passing_count == 1
    assert res.passes_2_of_5 is False


def test_threshold_0_of_5_does_not_pass(tmp_path: Path) -> None:
    inv = _make_inventory_with_loc(tmp_path, 0)
    res = compute_thresholds(inv, _make_history())
    assert res.passing_count == 0
    assert res.passes_2_of_5 is False


def test_compute_thresholds_from_repo_invokes_inventory_and_history(
    tmp_path: Path,
) -> None:
    """The standalone variant wires inventory + history phases and
    produces the same result as the explicit form."""
    inv = _make_inventory_with_loc(tmp_path, 50_000)
    history = _make_history(contributors=30)
    # take_inventory and analyze_history are lazily imported inside the
    # function — patch them at their source modules.
    with (
        patch("forensic_deepdive.inventory.take_inventory", return_value=inv),
        patch(
            "forensic_deepdive.history.git_archaeology.analyze_history",
            return_value=history,
        ),
    ):
        res = compute_thresholds_from_repo(tmp_path)
    assert res.loc_50k is True
    assert res.contributors_25 is True
    assert res.passes_2_of_5 is True
