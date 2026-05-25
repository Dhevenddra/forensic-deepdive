"""JSONL append-log :class:`InsightStore` (DEC-019 default).

Persists one JSON object per line in ``<repo>/.deepdive/insights.jsonl``.
Zero dependencies, hand-editable, git-friendly. Append-fsync on every
record so a process crash doesn't lose an insight. Corrupt single lines
are skipped on read — the rest of the file still parses.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

from forensic_deepdive.insights.store import Insight, InsightStore


class JsonlInsightStore(InsightStore):
    """The always-available default backend (DEC-019).

    Construction does NOT create the file or its parent directory —
    those happen lazily on the first :meth:`record` call so a freshly-
    opened-but-never-written store leaves no on-disk trace.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    # -- record --------------------------------------------------------------

    def record(self, insight: Insight) -> None:
        """Append *insight* and fsync. Creates the parent directory on
        first call; idempotent on subsequent calls."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(insight.to_dict(), ensure_ascii=False) + "\n"
        # Open in binary append mode so the encoding is explicit and the
        # write goes through one syscall. fsync after the write so a
        # process crash doesn't lose the insight.
        with open(self._path, "ab") as fh:
            fh.write(line.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())

    # -- recall --------------------------------------------------------------

    def recall(
        self,
        symbol: str,
        *,
        since: str | None = None,
        limit: int = 50,
    ) -> list[Insight]:
        """Return insights matching *symbol* (substring match, case-
        sensitive), newest-first, capped at *limit*. ``since`` is an ISO
        timestamp string — when provided, only insights with
        ``recorded_at >= since`` are kept.

        Symbol match is substring rather than exact because callers may
        pass either a qualified name (``greeter.py::Greeter.greet``) or
        a bare name (``greet``), and either should find the same
        insight. The MCP server's symbol-resolution helper does the
        canonicalization upstream — this is the storage-layer match.
        """
        if not self._path.exists():
            return []
        matches: list[Insight] = []
        for insight in self._iter_lines():
            if symbol not in insight.symbol:
                continue
            if since is not None and insight.recorded_at < since:
                continue
            matches.append(insight)
        # Newest-first. ISO timestamps with timezone offsets sort
        # lexically the same as chronologically.
        matches.sort(key=lambda i: i.recorded_at, reverse=True)
        return matches[:limit]

    # -- iter_all ------------------------------------------------------------

    def iter_all(self) -> Iterator[Insight]:
        if not self._path.exists():
            return
        yield from self._iter_lines()

    # -- internals -----------------------------------------------------------

    def _iter_lines(self) -> Iterator[Insight]:
        """Read line-by-line, skipping (silently) any line that fails to
        parse as JSON or to satisfy the :class:`Insight` contract.

        Skip-on-corrupt rather than raise because a single hand-edit
        with a syntax error shouldn't break every subsequent recall;
        the affected line is lost but the rest is recoverable.
        """
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    yield Insight.from_dict(data)
                except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                    continue
