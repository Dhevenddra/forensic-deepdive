"""Tests for the :class:`Insight` dataclass + ABC contract (DEC-019)."""

from __future__ import annotations

import pytest

from forensic_deepdive.insights import Insight


def test_insight_now_stamps_microsecond_iso() -> None:
    insight = Insight.now("s", "claim", "evidence", "human")
    # ISO with timezone offset, microsecond precision.
    assert "T" in insight.recorded_at
    assert "+00:00" in insight.recorded_at or insight.recorded_at.endswith("Z")
    # Microsecond field present (6 digits after the seconds dot).
    assert "." in insight.recorded_at
    micros = insight.recorded_at.split(".", 1)[1].split("+", 1)[0]
    assert len(micros) == 6, f"expected 6-digit microseconds, got {micros!r}"


def test_insight_verified_by_must_be_valid() -> None:
    with pytest.raises(ValueError, match="verified_by must be one of"):
        Insight(
            symbol="s",
            claim="c",
            evidence="e",
            verified_by="bogus",
            recorded_at="2026-05-25T00:00:00+00:00",
        )


def test_insight_requires_non_empty_fields() -> None:
    for field in ("symbol", "claim", "evidence"):
        kwargs = dict(
            symbol="s",
            claim="c",
            evidence="e",
            verified_by="human",
            recorded_at="2026-05-25T00:00:00+00:00",
        )
        kwargs[field] = ""
        with pytest.raises(ValueError, match="must be non-empty"):
            Insight(**kwargs)  # type: ignore[arg-type]


def test_insight_is_frozen() -> None:
    insight = Insight.now("s", "c", "e", "human")
    with pytest.raises((AttributeError, Exception)):
        insight.claim = "mutated"  # type: ignore[misc]


def test_insight_to_from_dict_roundtrip() -> None:
    original = Insight.now("greeter.py::greet", "claim", "src/x.py:5", "static", "sess-1")
    data = original.to_dict()
    recovered = Insight.from_dict(data)
    assert recovered == original


def test_insight_from_dict_handles_null_session_id() -> None:
    data = {
        "symbol": "s",
        "claim": "c",
        "evidence": "e",
        "verified_by": "human",
        "recorded_at": "2026-05-25T00:00:00+00:00",
        "session_id": None,
    }
    insight = Insight.from_dict(data)
    assert insight.session_id is None
