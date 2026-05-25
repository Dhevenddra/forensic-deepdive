"""Tests for ``open_insight_store`` factory (DEC-019).

The factory picks ``GraphitiInsightStore`` only when all three
conditions hold: ``prefer_graphiti=True``, threshold ``passes_2_of_5``,
and ``graphiti-core`` is importable. Any failure falls through to
``JsonlInsightStore`` silently.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from forensic_deepdive.insights import (
    JsonlInsightStore,
    open_insight_store,
)
from forensic_deepdive.insights.threshold import ThresholdResult


def _passing_threshold() -> ThresholdResult:
    """A ThresholdResult that returns ``passes_2_of_5=True``."""
    return ThresholdResult(
        loc=50_000,
        contributors=30,
        age_days=540,
        prs_last_12mo=0,
        issues_last_12mo=0,
        loc_50k=True,
        contributors_25=True,
        age_18m=True,
        prs_200=False,
        issues_100=False,
    )


def _failing_threshold() -> ThresholdResult:
    return ThresholdResult(
        loc=100,
        contributors=2,
        age_days=10,
        prs_last_12mo=0,
        issues_last_12mo=0,
        loc_50k=False,
        contributors_25=False,
        age_18m=False,
        prs_200=False,
        issues_100=False,
    )


def test_default_chooses_jsonl(tmp_path: Path) -> None:
    """No args → always JSONL. The v0.2 floor."""
    store = open_insight_store(tmp_path)
    assert isinstance(store, JsonlInsightStore)


def test_threshold_failure_falls_through_to_jsonl(tmp_path: Path) -> None:
    """Even with ``prefer_graphiti=True``, a failing threshold returns
    the JSONL fallback — DEC-005 gate guards the $8/run cost."""
    store = open_insight_store(
        tmp_path,
        prefer_graphiti=True,
        threshold=_failing_threshold(),
    )
    assert isinstance(store, JsonlInsightStore)


def test_no_threshold_falls_through_to_jsonl(tmp_path: Path) -> None:
    """``prefer_graphiti=True`` with ``threshold=None`` is ambiguous;
    the factory treats it as a fail-closed and returns JSONL."""
    store = open_insight_store(tmp_path, prefer_graphiti=True, threshold=None)
    assert isinstance(store, JsonlInsightStore)


def test_graphiti_unavailable_falls_through_to_jsonl(tmp_path: Path) -> None:
    """When ``graphiti-core`` cannot be imported, even an opted-in
    above-threshold caller gets the JSONL fallback. No warning, no
    error — matches DEC-009 honest-mode silent-degrade."""
    # Hide any installed graphiti-core so the lazy import raises.
    with patch.dict(sys.modules, {"graphiti_core": None}):
        store = open_insight_store(
            tmp_path,
            prefer_graphiti=True,
            threshold=_passing_threshold(),
        )
    assert isinstance(store, JsonlInsightStore)


def test_graphiti_chosen_when_all_conditions_pass(tmp_path: Path) -> None:
    """With ``prefer_graphiti=True``, threshold passing, and a mocked
    graphiti_core module: the factory returns the Graphiti backend
    (NOT the JSONL fallback)."""
    fake_module = type(sys)("graphiti_core")

    class _FakeGraphiti:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def close(self) -> None:
            pass

    fake_module.Graphiti = _FakeGraphiti  # type: ignore[attr-defined]
    with patch.dict(sys.modules, {"graphiti_core": fake_module}):
        store = open_insight_store(
            tmp_path,
            prefer_graphiti=True,
            threshold=_passing_threshold(),
        )
    # The defining condition for "we got Graphiti, not the fallback":
    # not a JsonlInsightStore. Direct class identity comparison is the
    # cleanest signal — isinstance has tripped on module-reimport
    # subtleties in similar tests historically.
    assert not isinstance(store, JsonlInsightStore)
    assert type(store).__name__ == "GraphitiInsightStore"
    assert type(store).__module__ == "forensic_deepdive.insights.graphiti_store"


def test_jsonl_default_path_under_deepdive(tmp_path: Path) -> None:
    """The default JSONL path is ``<repo>/.deepdive/insights.jsonl`` —
    next to the graph DB so a future migration can find both."""
    store = open_insight_store(tmp_path)
    assert isinstance(store, JsonlInsightStore)
    assert store.path == tmp_path / ".deepdive" / "insights.jsonl"


def test_jsonl_custom_path_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom" / "my-insights.jsonl"
    store = open_insight_store(tmp_path, jsonl_path=custom)
    assert isinstance(store, JsonlInsightStore)
    assert store.path == custom
