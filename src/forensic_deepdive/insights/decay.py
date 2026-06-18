"""Stdlib recency decay for insight recall (DEC-075, v0.7 Step 4).

Lane-(iii) memory follow-on. A learning recorded last week is usually more relevant than
one from a year ago, so recall applies an **Ebbinghaus / half-life** recency weight to the
fuzzy (BM25 + semantic) recall tail — a slightly-less-relevant but much-newer insight can
then outrank an old one. Pure stdlib (``datetime`` + ``math``) — **no** ``py-fsrs`` dep, no
LLM, the pure-static floor holds (DEC-009). The symbol-substring precise-lookup path is
**not** decayed (it is already the exact-match contract, newest-first).
"""

from __future__ import annotations

from datetime import UTC, datetime

# 90 days: a learning is worth half as much after a quarter. A neutral default; the recall
# backend exposes it so a caller can widen/narrow the window.
DEFAULT_HALF_LIFE_DAYS = 90.0


def _parse_iso(recorded_at: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(recorded_at)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def decay_weight(
    recorded_at: str,
    *,
    now: datetime | None = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """A recency weight in ``(0, 1]``: ``0.5 ** (age_days / half_life_days)``.

    A just-recorded insight weighs ~1.0; one a half-life old weighs ~0.5; older decays
    toward 0 (never reaching it). **Fail-open:** a non-positive *half_life_days* or an
    unparseable / future *recorded_at* returns ``1.0`` (no decay) — recency must never
    *suppress* an insight, only gently reorder by it.
    """
    if half_life_days <= 0:
        return 1.0
    recorded = _parse_iso(recorded_at)
    if recorded is None:
        return 1.0
    reference = now if now is not None else datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    age_days = (reference - recorded).total_seconds() / 86400.0
    if age_days <= 0:  # future / just now → no decay
        return 1.0
    return 0.5 ** (age_days / half_life_days)
