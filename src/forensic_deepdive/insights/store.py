"""The :class:`InsightStore` ABC and :class:`Insight` dataclass (DEC-019).

Every backend implements the same four operations: ``record`` (append one
insight), ``recall`` (filter by symbol + recency), ``iter_all`` (full
scan, for export / migration), ``close`` (release resources). The shape
matches the MCP server's per-call store pattern from DEC-016 — stateless
between calls, opened-and-closed inside each tool invocation.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

# Allowed values for ``Insight.verified_by``. v0.2 ships these four; the
# string is validated at construction (rather than an Enum) so future
# verifier types extend without a schema migration.
_VERIFIED_BY_VALUES = frozenset({"human", "static", "test", "ai"})


VerifiedBy = str
"""Type alias for the verified_by string field — for readability at call
sites. Validation happens in :meth:`Insight.__post_init__`."""


@dataclass(frozen=True, slots=True)
class Insight:
    """One durable agent learning about this codebase.

    Frozen / hashable so insights can live in sets / dicts when callers
    dedup. Construction validates ``verified_by`` against the v0.2 enum.
    """

    symbol: str
    claim: str
    evidence: str
    verified_by: VerifiedBy
    recorded_at: str
    session_id: str | None = None

    def __post_init__(self) -> None:
        if self.verified_by not in _VERIFIED_BY_VALUES:
            raise ValueError(
                f"verified_by must be one of {sorted(_VERIFIED_BY_VALUES)}, "
                f"got {self.verified_by!r}"
            )
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.claim:
            raise ValueError("claim must be non-empty")
        if not self.evidence:
            raise ValueError("evidence must be non-empty")

    @classmethod
    def now(
        cls,
        symbol: str,
        claim: str,
        evidence: str,
        verified_by: VerifiedBy,
        session_id: str | None = None,
    ) -> Insight:
        """Convenience constructor that stamps ``recorded_at`` with the
        current UTC time in ISO format with **microsecond** precision.

        Microsecond precision matters: two ``record()`` calls in the
        same second (common in tests; possible in production batched
        writes) need to sort distinguishably — otherwise ``recall``'s
        newest-first ordering ties on identical timestamps and the
        wrong insight surfaces first.
        """
        return cls(
            symbol=symbol,
            claim=claim,
            evidence=evidence,
            verified_by=verified_by,
            recorded_at=datetime.now(UTC).isoformat(timespec="microseconds"),
            session_id=session_id,
        )

    def content_hash(self) -> str:
        """SHA-256 of the insight's *content* — ``symbol|claim|evidence|verified_by``
        (DEC-069, the DEC-036 ParseCache content-hash discipline). ``recorded_at`` /
        ``session_id`` are deliberately excluded so re-recording the same learning in a
        later session collapses to one entry in the recall index (dedup key)."""
        payload = f"{self.symbol}\x1f{self.claim}\x1f{self.evidence}\x1f{self.verified_by}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, str | None]:
        """Return a JSON-serializable mapping (used by the JSONL backend
        and by MCP tool responses)."""
        return {
            "symbol": self.symbol,
            "claim": self.claim,
            "evidence": self.evidence,
            "verified_by": self.verified_by,
            "recorded_at": self.recorded_at,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> Insight:
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Missing keys raise ``KeyError`` — corrupt insights should fail
        loudly at parse time so the caller can skip-the-line and move on.
        """
        return cls(
            symbol=str(data["symbol"]),
            claim=str(data["claim"]),
            evidence=str(data["evidence"]),
            verified_by=str(data["verified_by"]),
            recorded_at=str(data["recorded_at"]),
            session_id=(str(data["session_id"]) if data.get("session_id") is not None else None),
        )


class InsightStore(ABC):
    """Persistent agent-memory backend (DEC-019).

    Implementations are stateless between calls — every operation opens
    whatever resource it needs and closes when done. Matches the
    per-call ``LadybugStore`` pattern from DEC-016 (MCP server).
    """

    @abstractmethod
    def record(self, insight: Insight) -> None:
        """Append one insight. Implementations must be durable on return —
        no buffering past the call boundary."""

    @abstractmethod
    def recall(
        self,
        symbol: str,
        *,
        since: str | None = None,
        limit: int = 50,
    ) -> list[Insight]:
        """Return insights matching *symbol* (substring or exact qn),
        newest-first, capped at *limit*. ``since`` is an ISO timestamp;
        when provided, only insights with ``recorded_at >= since`` are
        returned."""

    @abstractmethod
    def iter_all(self) -> Iterator[Insight]:
        """Yield every stored insight in insertion order. Used for export
        / migration / debugging — not for normal MCP query paths."""

    def close(self) -> None:  # noqa: B027 — intentional no-op default
        """Release any held resources. Default no-op for stateless backends."""

    # Context-manager sugar so callers can ``with open_insight_store(...) as s``.

    def __enter__(self) -> InsightStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
