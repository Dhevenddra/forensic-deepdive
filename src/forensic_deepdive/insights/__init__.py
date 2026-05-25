"""Agent-insight layer (DEC-019).

The persistent agent-memory surface. When an AI agent verifies a hypothesis,
fixes a bug, or notices a pattern in this codebase, ``record_insight``
appends a durable record; ``recall_insights`` surfaces relevant prior
learnings on subsequent sessions.

Two backends:

- :class:`JsonlInsightStore` is the always-available default. Persists
  to ``<repo>/.deepdive/insights.jsonl`` — zero dependencies, git-friendly,
  hand-editable.
- :class:`GraphitiInsightStore` is opt-in via the ``[graphiti]`` PyPI
  extra. Constructed only when ``open_insight_store(prefer_graphiti=True)``
  is called AND the DEC-005 2-of-5 threshold passes AND ``graphiti-core``
  imports cleanly. Falls through to JSONL on any failure.

Use :func:`open_insight_store` rather than constructing the backends
directly — it applies the DEC-019 fallthrough rules.
"""

from __future__ import annotations

from forensic_deepdive.insights.factory import open_insight_store
from forensic_deepdive.insights.jsonl_store import JsonlInsightStore
from forensic_deepdive.insights.store import Insight, InsightStore, VerifiedBy
from forensic_deepdive.insights.threshold import ThresholdResult, compute_thresholds

__all__ = [
    "Insight",
    "InsightStore",
    "JsonlInsightStore",
    "ThresholdResult",
    "VerifiedBy",
    "compute_thresholds",
    "open_insight_store",
]
