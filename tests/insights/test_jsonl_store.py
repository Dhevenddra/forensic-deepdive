"""Tests for :class:`JsonlInsightStore` (DEC-019 default backend)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from forensic_deepdive.insights import Insight, JsonlInsightStore


def test_record_creates_file_lazily(tmp_path: Path) -> None:
    """Construction does NOT touch the filesystem — only ``record``
    creates the file (and its parent dir)."""
    target = tmp_path / "subdir" / "insights.jsonl"
    store = JsonlInsightStore(target)
    assert not target.exists()
    assert not target.parent.exists()
    store.record(Insight.now("s", "c", "e", "human"))
    assert target.exists()
    assert target.parent.is_dir()


def test_record_is_append_only(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    store.record(Insight.now("s1", "c1", "e1", "human"))
    store.record(Insight.now("s2", "c2", "e2", "static"))
    lines = (tmp_path / "insights.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    # Each line is valid JSON.
    [json.loads(line) for line in lines]


def test_recall_returns_newest_first(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    store.record(Insight.now("greeter.py::greet", "first", "e", "human"))
    time.sleep(0.001)  # ensure microsecond timestamps differ
    store.record(Insight.now("greeter.py::greet", "second", "e", "human"))
    time.sleep(0.001)
    store.record(Insight.now("greeter.py::greet", "third", "e", "human"))
    matches = store.recall("greet")
    assert [m.claim for m in matches] == ["third", "second", "first"]


def test_recall_filters_by_substring(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    store.record(Insight.now("greeter.py::Greeter.greet", "g claim", "e", "human"))
    store.record(Insight.now("storage.py::Storage.save", "s claim", "e", "human"))
    matches = store.recall("Greet")
    assert len(matches) == 1
    assert matches[0].claim == "g claim"


def test_recall_with_since_filter(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    store.record(Insight.now("s", "old", "e", "human"))
    time.sleep(0.01)
    cutoff_insight = Insight.now("s", "cutoff", "e", "human")
    store.record(cutoff_insight)
    time.sleep(0.01)
    store.record(Insight.now("s", "new", "e", "human"))
    matches = store.recall("s", since=cutoff_insight.recorded_at)
    claims = {m.claim for m in matches}
    # cutoff_insight is included (>=) and "new" is included.
    assert "old" not in claims
    assert "cutoff" in claims
    assert "new" in claims


def test_recall_respects_limit(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    for n in range(20):
        store.record(Insight.now("s", f"claim {n}", "e", "human"))
        time.sleep(0.0001)
    matches = store.recall("s", limit=5)
    assert len(matches) == 5


def test_recall_returns_empty_when_file_missing(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "nope.jsonl")
    assert store.recall("anything") == []


def test_corrupt_line_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "insights.jsonl"
    store = JsonlInsightStore(path)
    store.record(Insight.now("s", "good", "e", "human"))
    # Corrupt the file by appending invalid JSON in the middle.
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("not-json-at-all\n")
        fh.write('{"missing": "fields"}\n')
    store.record(Insight.now("s", "after", "e", "human"))
    matches = store.recall("s")
    claims = {m.claim for m in matches}
    assert "good" in claims
    assert "after" in claims
    # Corrupt lines silently skipped.
    assert len(matches) == 2


def test_iter_all_yields_in_insertion_order(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "insights.jsonl")
    for n in range(3):
        store.record(Insight.now("s", f"claim {n}", "e", "human"))
        time.sleep(0.0001)
    listed = list(store.iter_all())
    assert [m.claim for m in listed] == ["claim 0", "claim 1", "claim 2"]


def test_iter_all_on_missing_file_yields_nothing(tmp_path: Path) -> None:
    store = JsonlInsightStore(tmp_path / "missing.jsonl")
    assert list(store.iter_all()) == []


def test_store_as_context_manager(tmp_path: Path) -> None:
    """ABC default close() is a no-op for JSONL but the context-manager
    sugar should still work."""
    with JsonlInsightStore(tmp_path / "insights.jsonl") as store:
        store.record(Insight.now("s", "c", "e", "human"))
        assert len(store.recall("s")) == 1
