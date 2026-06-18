"""Memory lane-(iii) follow-ons (DEC-075, v0.7 Step 4).

Recency **decay** + opt-in **semantic** RRF fusion over the recall tail, and an **explicit**
shadow-ref **push**. All LLM-free: decay is stdlib, semantic reuses the DEC-042 ONNX extra
(no-op without it), push is git plumbing. The DEC-019/069 substring-first contract holds.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from forensic_deepdive.insights.decay import decay_weight
from forensic_deepdive.insights.jsonl_store import JsonlInsightStore
from forensic_deepdive.insights.recall_index import InsightRecallIndex, build_recall_index
from forensic_deepdive.insights.semantic_recall import (
    build_insight_semantic_index,
    ensure_insight_semantic_index,
    insight_semantic_available,
    insight_semantic_dir,
)
from forensic_deepdive.insights.shadow_ref import (
    SHADOW_REF,
    push_shadow_ref,
    save_to_shadow_ref,
)
from forensic_deepdive.insights.store import Insight


def _ins(symbol, claim, evidence, at):
    return Insight(symbol, claim, evidence, "ai", at)


# --- (b) decay --------------------------------------------------------------


def test_decay_weight_monotonic_and_half_life():
    now = datetime(2026, 6, 1, tzinfo=UTC)
    fresh = decay_weight((now - timedelta(days=1)).isoformat(), now=now, half_life_days=90)
    old = decay_weight((now - timedelta(days=365)).isoformat(), now=now, half_life_days=90)
    assert 0 < old < fresh <= 1.0
    # At exactly one half-life the weight is 0.5.
    half = decay_weight((now - timedelta(days=90)).isoformat(), now=now, half_life_days=90)
    assert abs(half - 0.5) < 1e-9


def test_decay_weight_fails_open():
    now = datetime(2026, 6, 1, tzinfo=UTC)
    assert decay_weight("not-a-timestamp", now=now) == 1.0  # unparseable → no decay
    assert decay_weight((now + timedelta(days=10)).isoformat(), now=now) == 1.0  # future
    assert decay_weight((now - timedelta(days=10)).isoformat(), now=now, half_life_days=0) == 1.0


def test_decay_reorders_recall_tail_by_recency(tmp_path):
    # Older insight is MORE lexically relevant ("alpha" twice); newer is less ("alpha" once).
    older = _ins("mod.py::old_fn", "alpha alpha beta gamma", "ev", "2020-01-01T00:00:00+00:00")
    newer = _ins("mod.py::new_fn", "alpha delta epsilon", "ev", "2025-12-01T00:00:00+00:00")
    idx = tmp_path / "insights.db"
    build_recall_index(idx, [older, newer])
    index = InsightRecallIndex(idx)
    # Without decay, BM25 relevance wins → the older (more-relevant) insight ranks first.
    no_decay = index.search("alpha", decay=False, semantic=False)
    assert [i.symbol for i in no_decay][:2] == ["mod.py::old_fn", "mod.py::new_fn"]
    # With decay, the much-newer insight outranks the slightly-more-relevant old one.
    decayed = index.search("alpha", decay=True, semantic=False)
    assert decayed[0].symbol == "mod.py::new_fn"


# --- substring-first contract preserved (DEC-019/069) -----------------------


def test_substring_match_still_first_and_undecayed(tmp_path):
    idx = tmp_path / "insights.db"
    build_recall_index(
        idx,
        [
            _ins(
                "api/models.py::Owner", "the owner model persists", "x", "2020-01-01T00:00:00+00:00"
            ),
            _ins(
                "unrelated::thing", "owner heuristics live here", "y", "2025-12-01T00:00:00+00:00"
            ),
        ],
    )
    # A symbol-substring hit ("Owner") is the precise lookup → first, even though it is the
    # OLDER insight (the substring path is never decayed).
    out = InsightRecallIndex(idx).search("Owner")
    assert out[0].symbol == "api/models.py::Owner"


# --- (a) semantic recall: opt-in, degrades cleanly --------------------------


def test_semantic_unavailable_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("FORENSIC_SEMANTIC_MODEL", raising=False)  # no model → semantic off
    idx = tmp_path / "insights.db"
    build_recall_index(
        idx,
        [
            _ins("a.py::f", "reconnect handler retries", "e", "2026-01-01T00:00:00+00:00"),
            _ins("b.py::g", "owner persistence layer", "e", "2026-02-01T00:00:00+00:00"),
        ],
    )
    assert not insight_semantic_available(insight_semantic_dir(idx))
    index = InsightRecallIndex(idx)
    # semantic=True must be a no-op when unavailable → identical recall to semantic=False.
    assert [i.symbol for i in index.search("reconnect", semantic=True)] == [
        i.symbol for i in index.search("reconnect", semantic=False)
    ]


def test_semantic_build_is_noop_without_model(tmp_path, monkeypatch):
    monkeypatch.delenv("FORENSIC_SEMANTIC_MODEL", raising=False)
    ins = [_ins("a.py::f", "claim", "ev", "2026-01-01T00:00:00+00:00")]
    assert build_insight_semantic_index(tmp_path, ins) is None
    assert ensure_insight_semantic_index(tmp_path / "insights.db", tmp_path / "x.jsonl") is None


def test_semantic_module_imports_without_extra():
    # Importing the module must never hard-require the extra (DEC-042/075 floor).
    from forensic_deepdive.insights import semantic_recall as sr

    assert hasattr(sr, "build_insight_semantic_index")
    assert hasattr(sr, "InsightSemanticIndex")


# --- (c) explicit shadow-ref push -------------------------------------------


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path):
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")


def test_push_outside_git_repo(tmp_path):
    ok, msg = push_shadow_ref(tmp_path)
    assert ok is False and "not a git repository" in msg


def test_push_without_ref(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    ok, msg = push_shadow_ref(repo)
    assert ok is False and "no insight ref" in msg


def test_push_dry_run_and_real_push_to_bare_remote(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README").write_text("x")
    _git(repo, "add", "README")
    _git(repo, "commit", "-qm", "init")
    jsonl = repo / ".deepdive" / "insights.jsonl"
    JsonlInsightStore(jsonl).record(_ins("A.b", "a claim", "evidence", "2026-01-01T00:00:00+00:00"))
    assert save_to_shadow_ref(repo, jsonl)
    # A bare remote to push into.
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
    _git(repo, "remote", "add", "origin", str(remote))

    ok, msg = push_shadow_ref(repo, dry_run=True)
    assert ok and "would push" in msg
    # Dry-run must NOT have moved the ref on the remote.
    code = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", "--verify", "--quiet", SHADOW_REF],
        capture_output=True,
    ).returncode
    assert code != 0
    # Real push lands the ref on the remote.
    ok, msg = push_shadow_ref(repo)
    assert ok and "pushed" in msg
    code = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", "--verify", "--quiet", SHADOW_REF],
        capture_output=True,
    ).returncode
    assert code == 0


def test_push_unknown_remote(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "f").write_text("x")
    _git(repo, "add", "f")
    _git(repo, "commit", "-qm", "i")
    jsonl = repo / ".deepdive" / "insights.jsonl"
    JsonlInsightStore(jsonl).record(_ins("A.b", "c", "e", "2026-01-01T00:00:00+00:00"))
    save_to_shadow_ref(repo, jsonl)
    ok, msg = push_shadow_ref(repo, remote="nope")
    assert ok is False and "not found" in msg
