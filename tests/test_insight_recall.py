"""Lane-(iii) memory hardening (DEC-069, v0.6 Step 6).

The JSONL store stays authoritative; a derived SQLite/FTS5 BM25 index is the
``recall_insights`` backend (rebuildable from the files, content-hash deduped), and a git
shadow-ref makes the store survive a clone. Pure stdlib ``sqlite3`` + git plumbing — no
runtime LLM (the pure-static floor holds).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from forensic_deepdive.insights.jsonl_store import JsonlInsightStore
from forensic_deepdive.insights.recall_index import (
    InsightRecallIndex,
    build_recall_index,
    ensure_recall_index,
    recall_index_path_for_jsonl,
)
from forensic_deepdive.insights.shadow_ref import (
    SHADOW_REF,
    load_from_shadow_ref,
    save_to_shadow_ref,
)
from forensic_deepdive.insights.store import Insight


def _ins(symbol, claim, evidence, verified_by="ai", at="2026-01-01T00:00:00.000000+00:00"):
    return Insight(symbol, claim, evidence, verified_by, at)


# --- content hash + dedup ---------------------------------------------------


def test_content_hash_ignores_timestamp_and_session():
    a = Insight("s", "c", "e", "ai", "2026-01-01T00:00:00+00:00", "sess-1")
    b = Insight("s", "c", "e", "ai", "2026-02-02T00:00:00+00:00", "sess-2")
    assert a.content_hash() == b.content_hash()
    assert Insight("s", "c2", "e", "ai", a.recorded_at).content_hash() != a.content_hash()


def test_build_dedups_identical_insights(tmp_path):
    idx = tmp_path / "insights.db"
    dup = _ins("Greeter.greet", "returns a greeting", "tested", at="2026-01-01T00:00:01+00:00")
    dup2 = _ins("Greeter.greet", "returns a greeting", "tested", at="2026-01-02T00:00:02+00:00")
    other = _ins("Owner.save", "persists", "code")
    build_recall_index(idx, [dup, dup2, other])
    results = InsightRecallIndex(idx).search("Greeter")
    assert len(results) == 1  # the two identical insights collapsed
    assert results[0].recorded_at == "2026-01-01T00:00:01+00:00"  # earliest kept


# --- FTS5 / BM25 recall -----------------------------------------------------


def test_recall_symbol_substring_then_bm25(tmp_path):
    idx = tmp_path / "insights.db"
    build_recall_index(
        idx,
        [
            _ins("api/views.py::owner_list", "lists owners", "returns a queryset"),
            _ins("api/models.py::Owner", "the owner model persists to owners", "tablename"),
            _ins("unrelated::thing", "websocket reconnect handler", "retries thrice"),
        ],
    )
    index = InsightRecallIndex(idx)
    # symbol substring match (the DEC-019 contract).
    by_symbol = index.search("owner_list")
    assert any("owner_list" in i.symbol for i in by_symbol)
    # BM25 full-text: a query word in the *claim* surfaces the insight even with no symbol
    # substring match.
    by_text = index.search("reconnect")
    assert any("websocket" in i.claim for i in by_text)


def test_since_and_limit(tmp_path):
    idx = tmp_path / "insights.db"
    build_recall_index(
        idx,
        [
            _ins("X.a", "claim a", "ev", at="2026-01-01T00:00:00+00:00"),
            _ins("X.b", "claim b", "ev", at="2026-06-01T00:00:00+00:00"),
        ],
    )
    index = InsightRecallIndex(idx)
    assert len(index.search("X", since="2026-03-01T00:00:00+00:00")) == 1
    assert len(index.search("X", limit=1)) == 1


# --- rebuild from the authoritative files -----------------------------------


def test_index_rebuilds_from_jsonl_after_deletion(tmp_path):
    jsonl = tmp_path / ".deepdive" / "insights.jsonl"
    store = JsonlInsightStore(jsonl)
    store.record(_ins("Svc.run", "dispatches commands", "registry lookup"))
    idx = recall_index_path_for_jsonl(jsonl)
    ensure_recall_index(idx, jsonl)
    assert InsightRecallIndex(idx).search("Svc.run")
    # Delete the derived index — it must rebuild from the authoritative JSONL.
    idx.unlink()
    assert not InsightRecallIndex(idx).exists()
    ensure_recall_index(idx, jsonl)
    assert InsightRecallIndex(idx).search("Svc.run")


# --- git shadow-ref portability ---------------------------------------------


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path):
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")


def test_shadow_ref_round_trip(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    jsonl = repo / ".deepdive" / "insights.jsonl"
    JsonlInsightStore(jsonl).record(_ins("A.b", "a claim", "evidence"))
    assert save_to_shadow_ref(repo, jsonl)
    # Wipe the local JSONL → the ref still holds it.
    jsonl.unlink()
    assert load_from_shadow_ref(repo, jsonl)
    assert any(i.symbol == "A.b" for i in JsonlInsightStore(jsonl).iter_all())


def test_shadow_ref_survives_clone(tmp_path):
    origin = tmp_path / "origin"
    _init_repo(origin)
    # A repo needs at least one commit to be cloneable.
    (origin / "README").write_text("x")
    _git(origin, "add", "README")
    _git(origin, "commit", "-qm", "init")
    jsonl = origin / ".deepdive" / "insights.jsonl"
    JsonlInsightStore(jsonl).record(_ins("Persisted.insight", "travels via the ref", "shadow"))
    assert save_to_shadow_ref(origin, jsonl)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
    # Fetch the shadow ref (not a branch/tag, so not fetched by default).
    subprocess.run(
        ["git", "-C", str(clone), "fetch", "-q", str(origin), f"{SHADOW_REF}:{SHADOW_REF}"],
        check=True,
        capture_output=True,
    )
    clone_jsonl = clone / ".deepdive" / "insights.jsonl"
    assert load_from_shadow_ref(clone, clone_jsonl)
    assert any(i.symbol == "Persisted.insight" for i in JsonlInsightStore(clone_jsonl).iter_all())


def test_shadow_ref_noop_outside_git(tmp_path):
    jsonl = tmp_path / "insights.jsonl"
    JsonlInsightStore(jsonl).record(_ins("A.b", "c", "e"))
    assert save_to_shadow_ref(tmp_path, jsonl) is False  # not a git repo → best-effort False


# --- the MCP backend swap (signature + response shape unchanged) ------------


def test_recall_insights_tool_uses_fts5_backend(tmp_path):
    from forensic_deepdive.mcp_server.server import recall_insights, record_insight

    db = tmp_path / ".deepdive" / "graph.lbug"
    rec = record_insight(db, "Greeter.greet", "returns a friendly greeting", "tested", "test")
    assert "recorded" in rec and "deduplicated" not in rec
    # Re-recording the identical insight is deduplicated (content hash).
    rec2 = record_insight(db, "Greeter.greet", "returns a friendly greeting", "tested", "test")
    assert rec2.get("deduplicated") is True
    # Recall via the FTS5 backend — same response shape; BM25 over the claim text works.
    out = recall_insights(db, "greeting")
    assert out["count"] >= 1 and any("greet" in i["symbol"] for i in out["insights"])
