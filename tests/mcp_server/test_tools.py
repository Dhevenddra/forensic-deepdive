"""Tests for the 5 composite MCP tools (DEC-016).

Each test builds a real LadybugDB graph from a fixture, then calls the
underlying tool functions directly. We don't spin up the stdio transport
— the MCP protocol layer is upstream-tested by ``mcp`` itself. What we
verify here is the tools' query shapes, payloads, and edge cases.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from forensic_deepdive.mcp_server import server as srv
from forensic_deepdive.pipeline import (
    ExtractConfig,
    PipelineRunner,
    default_phases,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    """Build a real .lbug graph from python_sample and return its path."""
    repo = tmp_path / "py"
    shutil.copytree(FIXTURES / "python_sample", repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return db_path


# ---------------------------------------------------------------------------
# impact
# ---------------------------------------------------------------------------


def test_impact_upstream_finds_callers(populated_db: Path) -> None:
    """impact(format_message, direction=upstream) finds the callers
    (Greeter.greet inside greeter.py + run inside app.py)."""
    out = srv.impact(populated_db, "format_message", direction="upstream", depth=1)
    assert out["matches"], "format_message should resolve to a Symbol"
    assert out["depth_buckets"], "bucket 0 should hold direct callers"
    bucket0 = {entry["qualified_name"] for entry in out["depth_buckets"][0]}
    assert any(qn.endswith("::Greeter.greet") for qn in bucket0)
    assert any(qn.endswith("::run") for qn in bucket0)


def test_impact_downstream_finds_callees(populated_db: Path) -> None:
    """impact(Greeter.greet, downstream) finds what greet calls
    (format_message)."""
    out = srv.impact(populated_db, "greeter.py::Greeter.greet", direction="downstream", depth=1)
    bucket0 = {entry["qualified_name"] for entry in out["depth_buckets"][0]}
    assert any(qn.endswith("::format_message") for qn in bucket0)


def test_impact_unresolved_symbol_returns_empty(populated_db: Path) -> None:
    out = srv.impact(populated_db, "nonexistent_xyz_symbol", direction="upstream")
    assert out["matches"] == []
    assert out["summary"]["unresolved"] is True


def test_impact_rejects_bad_direction(populated_db: Path) -> None:
    out = srv.impact(populated_db, "format_message", direction="sideways")
    assert "error" in out


def test_impact_respects_min_confidence(populated_db: Path) -> None:
    """min_confidence='EXTRACTED' filters out INFERRED edges (e.g. the
    whole-module-import resolution path)."""
    out_inferred = srv.impact(
        populated_db,
        "format_message",
        direction="upstream",
        min_confidence="INFERRED",
    )
    out_extracted = srv.impact(
        populated_db,
        "format_message",
        direction="upstream",
        min_confidence="EXTRACTED",
    )
    inferred_count = sum(len(b) for b in out_inferred["depth_buckets"])
    extracted_count = sum(len(b) for b in out_extracted["depth_buckets"])
    assert extracted_count <= inferred_count  # stricter filter, same-or-fewer


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------


def test_context_returns_full_360(populated_db: Path) -> None:
    out = srv.context(populated_db, "format_message")
    assert out["symbol"]["qualified_name"].endswith("::format_message")
    # format_message has callers (Greeter.greet, run) and no callees
    # (it just builds a string).
    caller_qns = {c["qualified_name"] for c in out["callers"]}
    assert any(qn.endswith("::Greeter.greet") for qn in caller_qns)
    # Recent commits should be empty for a non-git temp dir.
    assert out["recent_commits"] == []


def test_context_class_symbol_has_members(populated_db: Path) -> None:
    out = srv.context(populated_db, "Greeter")
    member_qns = set(out["members"])
    assert any(qn.endswith("::Greeter.greet") for qn in member_qns)
    assert any(qn.endswith("::Greeter.__init__") for qn in member_qns)


def test_context_unresolved(populated_db: Path) -> None:
    out = srv.context(populated_db, "nonexistent_xyz")
    assert out.get("unresolved") is True


# ---------------------------------------------------------------------------
# archaeology
# ---------------------------------------------------------------------------


def test_archaeology_non_git_repo_has_no_commits(populated_db: Path) -> None:
    """python_sample fixture is not a git repo — archaeology returns
    a result with zero commits, no authors."""
    out = srv.archaeology(populated_db, "greeter.py")
    assert out["file"] == "greeter.py"
    assert out["total_commits"] == 0
    assert out["authors"] == []


def test_archaeology_resolves_symbol_to_its_file(populated_db: Path) -> None:
    """archaeology() accepts a symbol name and resolves to its file."""
    out = srv.archaeology(populated_db, "format_message")
    assert out["file"] == "greeter.py"


def test_archaeology_unresolved(populated_db: Path) -> None:
    out = srv.archaeology(populated_db, "nope.xyz")
    assert out.get("unresolved") is True


def test_archaeology_with_git_history(tmp_path: Path) -> None:
    """End-to-end: build a tmp git repo, extract, then archaeology()
    returns real authors / commits / defect proximity."""
    import os
    import subprocess

    def _git(repo, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

    def _commit(repo, author, email, date, msg, **files):
        for n, c in files.items():
            (repo / n).write_text(c, encoding="utf-8")
        env = {
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_COMMITTER_DATE": date,
        }
        _git(repo, "add", "-A")
        _git(repo, "-c", "commit.gpgsign=false", "commit", "-m", msg, env_extra=env)

    repo = tmp_path / "g"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(
        repo,
        "Alice",
        "alice@x",
        "2023-01-01T00:00:00+00:00",
        "add a",
        **{"a.py": "def helper(): pass\n"},
    )
    _commit(
        repo,
        "Alice",
        "alice@x",
        "2023-02-01T00:00:00+00:00",
        "fix: tighten validation",
        **{"a.py": "def helper(): return 1\n"},
    )
    _commit(
        repo,
        "Bob",
        "bob@x",
        "2023-03-01T00:00:00+00:00",
        "feat: B added",
        **{"a.py": "def helper(): return 2\n"},
    )
    db_path = tmp_path / "g.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)

    out = srv.archaeology(db_path, "a.py")
    assert out["total_commits"] == 3
    names = {a["name"] for a in out["authors"]}
    assert {"Alice", "Bob"} <= names
    assert out["bus_factor"] >= 1
    # One of three commit messages contains 'fix' -> defect proximity ≈ 0.333
    assert out["defect_commits"] >= 1
    assert 0 < out["defect_proximity"] <= 1
    # Recent commits present.
    assert len(out["recent_commits"]) == 3


# ---------------------------------------------------------------------------
# flow
# ---------------------------------------------------------------------------


def test_flow_walks_calls_chain(populated_db: Path) -> None:
    """flow(run) walks from the run() entry point through its callees."""
    out = srv.flow(populated_db, "run", max_depth=3)
    assert out["entry_points"], "run should resolve"
    # At least one path passes through format_message.
    chained_symbols = {step["symbol"] for path in out["paths"] for step in path}
    assert any(qn.endswith("::format_message") for qn in chained_symbols)


def test_flow_unresolved(populated_db: Path) -> None:
    out = srv.flow(populated_db, "no_such_entry_xyz")
    assert out.get("unresolved") is True
    assert out["paths"] == []


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


def test_query_natural_language_hybrid(populated_db: Path) -> None:
    # DEC-038: NL branch is now hybrid (lexical + structural), RRF-fused,
    # shaped, with provenance + degraded-mode honesty.
    out = srv.query(populated_db, natural_language="greet")
    qns = {r["qualified_name"] for r in out["results"]}
    # Both class Greeter and method Greeter.greet should match.
    assert any(qn.endswith("::Greeter") for qn in qns)
    assert any(qn.endswith("::Greeter.greet") for qn in qns)
    # Degraded-mode honesty: lexical + structural ran, semantic did not.
    assert out["retrievers_active"] == ["lexical", "structural"]
    assert out["degraded"] is True
    # Per-hit provenance + confidence.
    hit = out["results"][0]
    assert set(hit) >= {"symbol", "file", "line", "score", "retrievers", "confidence"}
    assert hit["confidence"] in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
    assert "lexical" in hit["retrievers"]
    # The exact-identifier match (Greeter.greet) is tagged EXTRACTED.
    by_qn = {r["qualified_name"]: r for r in out["results"]}
    greet = next(r for qn, r in by_qn.items() if qn.endswith("::Greeter.greet"))
    assert greet["confidence"] == "EXTRACTED"


def test_visualize_returns_mermaid(populated_db: Path) -> None:
    # DEC-039: the 8th tool. Greeter is a class -> classDiagram auto-pick.
    out = srv.visualize(populated_db, "Greeter")
    assert out["mermaid"].startswith("```mermaid")
    assert out["diagram"] == "classDiagram"
    assert "class Greeter" in out["mermaid"]


def test_visualize_rejects_non_mermaid_format(populated_db: Path) -> None:
    assert "error" in srv.visualize(populated_db, "Greeter", format="svg")


def test_query_natural_language_lexical_index_built(populated_db: Path) -> None:
    # Extract pre-builds the sidecar FTS5 index (DEC-038 / BuildGraphPhase).
    from forensic_deepdive.query.lexical import lexical_index_path_for_db

    assert lexical_index_path_for_db(populated_db).is_file()


def test_query_raw_cypher(populated_db: Path) -> None:
    out = srv.query(populated_db, cypher="MATCH (f:File) RETURN count(f)")
    assert out["row_count"] == 1
    assert out["rows"][0][0] == 2  # greeter.py + app.py


def test_query_invalid_cypher_returns_error(populated_db: Path) -> None:
    out = srv.query(populated_db, cypher="this is not cypher")
    assert "error" in out


def test_query_requires_either_arg(populated_db: Path) -> None:
    assert "error" in srv.query(populated_db)
    assert "error" in srv.query(populated_db, cypher="MATCH (n) RETURN n", natural_language="x")


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def test_make_server_registers_all_tools(populated_db: Path) -> None:
    """DEC-016 (5 composite tools) + DEC-019 (2 insight tools) + DEC-039
    (visualize). The server registers 8 tools total in v0.3."""
    import asyncio

    server = srv.make_server(populated_db)
    assert server.name == "forensic-deepdive"
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == {
        # DEC-016 graph composites.
        "impact_tool",
        "context_tool",
        "archaeology_tool",
        "flow_tool",
        "query_tool",
        # DEC-019 insight layer.
        "record_insight_tool",
        "recall_insights_tool",
        # DEC-039 visual export.
        "visualize_tool",
    }


def test_each_tool_description_is_bounded(populated_db: Path) -> None:
    """DEC-016: tool descriptions ≤ 200 tokens each. Approximate via
    ≤ 1000 characters (a generous proxy)."""
    import asyncio

    server = srv.make_server(populated_db)
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert len(tool.description or "") <= 1000, tool.name


# ---------------------------------------------------------------------------
# DEC-019 — insight tools (record_insight, recall_insights, context augment)
# ---------------------------------------------------------------------------


def test_record_insight_persists_and_returns_dict(populated_db: Path) -> None:
    """record_insight returns the persisted insight; recall_insights
    finds it on the same store."""
    out = srv.record_insight(
        populated_db,
        symbol="greeter.py::format_message",
        claim="returns string with greeting prefix",
        evidence="src/greeter.py:5",
        verified_by="static",
    )
    assert "recorded" in out
    assert out["recorded"]["symbol"] == "greeter.py::format_message"
    assert out["recorded"]["verified_by"] == "static"
    # Recall the same insight.
    recalled = srv.recall_insights(populated_db, "format_message")
    assert recalled["count"] == 1
    assert recalled["insights"][0]["claim"] == "returns string with greeting prefix"


def test_record_insight_validates_verified_by(populated_db: Path) -> None:
    """An invalid ``verified_by`` returns an error payload (matches the
    query() error-as-payload pattern from DEC-016)."""
    out = srv.record_insight(
        populated_db,
        symbol="s",
        claim="c",
        evidence="e",
        verified_by="bogus_value",
    )
    assert "error" in out
    assert "verified_by" in out["error"]


def test_recall_insights_returns_empty_when_none(populated_db: Path) -> None:
    out = srv.recall_insights(populated_db, "never_recorded_xyz")
    assert out["count"] == 0
    assert out["insights"] == []


def test_recall_insights_orders_newest_first(populated_db: Path) -> None:
    import time

    for n in range(3):
        srv.record_insight(
            populated_db,
            symbol="format_message",
            claim=f"claim {n}",
            evidence=f"e{n}",
            verified_by="ai",
        )
        time.sleep(0.001)
    out = srv.recall_insights(populated_db, "format_message")
    assert [i["claim"] for i in out["insights"]] == ["claim 2", "claim 1", "claim 0"]


def test_context_includes_recent_insights(populated_db: Path) -> None:
    """DEC-019: context() augments its payload with up to 3 recent
    insights for the queried symbol. Always present, even if empty."""
    # Empty case — field present, empty list.
    out = srv.context(populated_db, "format_message")
    assert "recent_insights" in out
    assert out["recent_insights"] == []
    # After recording one insight, context surfaces it.
    srv.record_insight(
        populated_db,
        symbol="greeter.py::format_message",
        claim="frequently used by greeting subsystem",
        evidence="src/greeter.py:5",
        verified_by="human",
    )
    out2 = srv.context(populated_db, "format_message")
    assert len(out2["recent_insights"]) == 1
    assert out2["recent_insights"][0]["claim"] == ("frequently used by greeting subsystem")


def test_context_recent_insights_capped_at_3(populated_db: Path) -> None:
    """Even if 10 insights exist, context() returns only the 3 newest."""
    import time

    for n in range(10):
        srv.record_insight(
            populated_db,
            symbol="greeter.py::format_message",
            claim=f"claim {n}",
            evidence=f"e{n}",
            verified_by="ai",
        )
        time.sleep(0.001)
    out = srv.context(populated_db, "format_message")
    assert len(out["recent_insights"]) == 3
    # Newest first.
    assert out["recent_insights"][0]["claim"] == "claim 9"


def test_insight_store_lives_next_to_graph(populated_db: Path) -> None:
    """The JSONL store path is ``<graph_parent>/insights.jsonl`` — both
    sit under ``<repo>/.deepdive/``."""
    out = srv.record_insight(
        populated_db,
        symbol="s",
        claim="c",
        evidence="e",
        verified_by="human",
    )
    insight_path = Path(out["path"])
    assert insight_path.name == "insights.jsonl"
    assert insight_path.parent == populated_db.parent
