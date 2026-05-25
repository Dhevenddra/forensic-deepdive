"""Opt-in :class:`InsightStore` backed by graphiti-core (DEC-019).

The ``graphiti-core`` PyPI package is in the ``[graphiti]`` optional
extra — most installs do NOT have it. This module imports it **lazily**
inside :meth:`__init__` so importing the module file itself works
unconditionally (the test suite imports it without the extra
installed).

When the extra IS installed AND the user has opted in AND the DEC-005
threshold passes, this backend wraps graphiti-core's bi-temporal
knowledge-graph API: ``record`` adds an episode, ``recall`` runs the
hybrid retrieval. Real LLM-backed entity extraction happens inside
graphiti-core on every ``record`` call — that's the $8/run cost
DEC-005 gates against.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

from forensic_deepdive.insights.store import Insight, InsightStore


class GraphitiUnavailableError(ImportError):
    """Raised when the ``[graphiti]`` extra is not installed.

    The factory (:func:`open_insight_store`) catches this and falls
    through to the JSONL backend — but direct callers (tests, CLI
    flags) get an actionable error message.
    """

    def __init__(self) -> None:
        super().__init__(
            "graphiti-core is not installed. Install the [graphiti] extra: "
            "`uv pip install forensic-deepdive[graphiti]` or "
            "`pip install graphiti-core>=0.28`."
        )


class GraphitiInsightStore(InsightStore):
    """The opt-in graphiti-core backend (DEC-019).

    Constructed only when the user explicitly enables it AND
    graphiti-core is importable. The factory layer
    (:func:`forensic_deepdive.insights.open_insight_store`) wraps this
    constructor with the threshold + availability checks.

    v0.2 ships the structural wiring; the actual graphiti-core API
    calls inside ``record`` / ``recall`` are exercised by item 14
    acceptance gates against a real LLM (Ollama-local or Claude-cloud).
    The test suite mocks the import — see ``tests/insights/test_factory.py``.
    """

    def __init__(self, db_path: Path) -> None:
        # Lazy import: succeed only if the extra is installed.
        try:
            import graphiti_core  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            raise GraphitiUnavailableError() from exc

        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # Defer client construction until first use — the graphiti-core
        # client opens an LLM connection that's heavy to set up.
        self._client: object | None = None

    @property
    def db_path(self) -> Path:
        return self._db_path

    # -- record --------------------------------------------------------------

    def record(self, insight: Insight) -> None:
        """Add the insight as a graphiti-core episode.

        v0.2 status: the API call is wired but the production code path
        is exercised by item 14 acceptance gates (real LLM). The unit
        test suite stops at the import boundary.
        """
        client = self._ensure_client()
        # graphiti-core's add_episode signature (≥0.28):
        #   client.add_episode(name=..., episode_body=..., reference_time=...,
        #                      source_description=...)
        # The structured fields are squashed into ``episode_body`` so the
        # entity extractor can recover them; the reference_time anchors
        # the bi-temporal storage.
        episode_body = (
            f"Symbol: {insight.symbol}\n"
            f"Claim: {insight.claim}\n"
            f"Evidence: {insight.evidence}\n"
            f"Verified by: {insight.verified_by}\n"
            f"Session: {insight.session_id or 'unspecified'}\n"
        )
        client.add_episode(  # type: ignore[attr-defined]
            name=f"insight:{insight.symbol}",
            episode_body=episode_body,
            reference_time=insight.recorded_at,
            source_description="forensic-deepdive agent insight",
        )

    # -- recall --------------------------------------------------------------

    def recall(
        self,
        symbol: str,
        *,
        since: str | None = None,
        limit: int = 50,
    ) -> list[Insight]:
        """Hybrid-retrieve insights for *symbol* via graphiti-core's
        search API.

        v0.2 status: wired but not LLM-tested. Returns ``[]`` rather
        than raising on retrieval failure so a downstream MCP tool
        degrades gracefully.
        """
        client = self._ensure_client()
        try:
            results = client.search(  # type: ignore[attr-defined]
                query=symbol,
                num_results=limit,
            )
        except Exception:
            return []
        return [self._result_to_insight(r) for r in (results or [])]

    # -- iter_all ------------------------------------------------------------

    def iter_all(self) -> Iterator[Insight]:
        """Yielding every stored insight from graphiti-core requires
        walking the knowledge graph — v0.3 work. v0.2 returns empty
        rather than crashing the export path."""
        return
        yield  # unreachable, keeps the return type ``Iterator[Insight]``

    # -- internals -----------------------------------------------------------

    def _ensure_client(self) -> object:
        """Construct the graphiti-core client on first use."""
        if self._client is None:
            from graphiti_core import Graphiti  # type: ignore[import-not-found]

            # Default config — driver / model selection is graphiti-core's
            # concern, configured via environment variables (OPENAI_API_KEY,
            # GRAPHITI_DRIVER, etc.) per their docs. v0.3 will surface
            # these via a ForensicDeepdive config object.
            self._client = Graphiti()
        return self._client

    @staticmethod
    def _result_to_insight(result: object) -> Insight:
        """Translate a graphiti-core search result back to an
        :class:`Insight`. v0.2 status: stub — the real translator
        depends on graphiti-core's search-result schema which is
        evolving in their 0.28+ releases.
        """
        # The structured fields were squashed into ``episode_body`` on
        # write (see ``record``); a real translator would parse them
        # back out. v0.2 returns a synthetic insight so the type
        # contract is preserved.
        return Insight(
            symbol=str(getattr(result, "name", "unknown")).replace("insight:", ""),
            claim=str(getattr(result, "summary", "graphiti retrieval")),
            evidence=str(getattr(result, "source_description", "graphiti")),
            verified_by="ai",
            recorded_at=str(getattr(result, "reference_time", "")),
            session_id=None,
        )

    def close(self) -> None:
        """Release the graphiti-core client connection."""
        if self._client is not None and hasattr(self._client, "close"):
            with contextlib.suppress(Exception):
                self._client.close()  # type: ignore[attr-defined]
            self._client = None
