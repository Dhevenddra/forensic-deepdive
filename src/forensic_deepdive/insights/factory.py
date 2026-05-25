"""Factory: :func:`open_insight_store` (DEC-019).

Picks the right backend based on three conditions:

1. ``prefer_graphiti`` — the user has opted in explicitly.
2. ``threshold`` — DEC-005 2-of-5 passes.
3. graphiti-core is importable.

ALL THREE must be true to return :class:`GraphitiInsightStore`; any
failure falls through to :class:`JsonlInsightStore`. The fall-through
is silent (no warning) so default extracts on every repo size produce
a working insight store without surfacing implementation details to
the user.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.insights.jsonl_store import JsonlInsightStore
from forensic_deepdive.insights.store import InsightStore
from forensic_deepdive.insights.threshold import ThresholdResult

_DEFAULT_JSONL_SUBPATH = (".deepdive", "insights.jsonl")
_DEFAULT_GRAPHITI_SUBPATH = (".deepdive", "graphiti.lbug")


def open_insight_store(
    repo_path: Path,
    *,
    prefer_graphiti: bool = False,
    threshold: ThresholdResult | None = None,
    jsonl_path: Path | None = None,
    graphiti_path: Path | None = None,
) -> InsightStore:
    """Return the appropriate :class:`InsightStore` for *repo_path*.

    *prefer_graphiti* must be ``True`` AND *threshold* must pass
    DEC-005's 2-of-5 AND ``graphiti-core`` must be importable for the
    factory to return :class:`GraphitiInsightStore`. Any failure
    returns :class:`JsonlInsightStore` — the v0.2 floor that always
    works (DEC-009: pure-static must work end-to-end).
    """
    repo_path = Path(repo_path)
    jsonl_target = jsonl_path or repo_path.joinpath(*_DEFAULT_JSONL_SUBPATH)

    if prefer_graphiti and threshold is not None and threshold.passes_2_of_5:
        # Try Graphiti — fall through to JSONL on any failure.
        graphiti_target = graphiti_path or repo_path.joinpath(*_DEFAULT_GRAPHITI_SUBPATH)
        try:
            # Import here so the module file imports cleanly without the
            # [graphiti] extra installed.
            from forensic_deepdive.insights.graphiti_store import (
                GraphitiInsightStore,
                GraphitiUnavailableError,
            )

            return GraphitiInsightStore(graphiti_target)
        except (GraphitiUnavailableError, ImportError):
            pass
    return JsonlInsightStore(jsonl_target)
