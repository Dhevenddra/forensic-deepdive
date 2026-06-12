"""DEC-059 end-to-end — the DI/ORM traceability tail (v0.5 Step 4).

Two fixtures:
- ``di_orm_sample`` (Python, FastAPI + SQLAlchemy): the ``trace`` tail walks the
  handler →INJECTS→ provider →CALLS→ model →PERSISTS_TO→ Table chain (the committed
  ``boundary`` promise, now delivered).
- ``di_ladder_sample`` (Java, Spring + JPA): the resolution ladder — a concrete/
  single-impl interface → INFERRED, a multi-impl interface → AMBIGUOUS-all
  (mirroring Spring's NoUniqueBeanDefinition), and a JPA literal ``@Table`` →
  EXTRACTED PERSISTS_TO.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.mcp_server.server import _calls_tail
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"


def _build(tmp_path: Path, sample: str) -> Path:
    repo = tmp_path / sample
    shutil.copytree(FIXTURES / sample, repo)
    db_path = tmp_path / "graph.lbug"
    PipelineRunner(default_phases()).run(
        ExtractConfig(
            repo_path=repo,
            output_dir=tmp_path / "out",
            flatten=False,
            write_editor_shims=False,
            build_graph_db=True,
            graph_db_path=db_path,
        )
    )
    return db_path


# --- Python: FastAPI Depends + SQLAlchemy → trace reaches the table ---------


def test_python_tail_edges_materialize(tmp_path):
    db = _build(tmp_path, "di_orm_sample")
    with LadybugStore(db) as s:
        injects = set(
            tuple(r)
            for r in s.query(
                "MATCH (a:Symbol)-[e:INJECTS]->(b:Symbol) "
                "RETURN a.qualified_name, b.qualified_name, e.confidence"
            )
        )
        persists = set(
            tuple(r)
            for r in s.query(
                "MATCH (m:Symbol)-[p:PERSISTS_TO]->(t:DbTable) "
                "RETURN m.qualified_name, t.table_id, p.confidence"
            )
        )
    assert ("api.py::create_owner", "repo.py::save_owner", "EXTRACTED") in injects
    assert ("models.py::Owner", "table::owners", "EXTRACTED") in persists


def test_python_trace_tail_reaches_table(tmp_path):
    db = _build(tmp_path, "di_orm_sample")
    with LadybugStore(db) as s:
        tail = _calls_tail(s, "api.py::create_owner", 10)
    # handler →INJECTS→ provider →CALLS→ model →PERSISTS_TO→ table
    assert {
        "symbol": "repo.py::save_owner",
        "file": "repo.py",
        "depth": 1,
        "confidence": "EXTRACTED",
        "via": "injects",
    } in tail
    assert {
        "symbol": "models.py::Owner",
        "file": "models.py",
        "depth": 2,
        "confidence": "EXTRACTED",
        "via": "calls",
    } in tail
    assert {
        "table": "owners",
        "table_id": "table::owners",
        "depth": 3,
        "confidence": "EXTRACTED",
        "via": "persists_to",
    } in tail


# --- Java: the Spring resolution ladder ------------------------------------


def test_java_resolution_ladder(tmp_path):
    db = _build(tmp_path, "di_ladder_sample")
    with LadybugStore(db) as s:
        injects = {
            (r[1].split("::")[-1], r[2])
            for r in s.query(
                "MATCH (a:Symbol)-[e:INJECTS]->(b:Symbol) "
                "RETURN a.qualified_name, b.qualified_name, e.confidence"
            )
        }
    # interface with one impl → INFERRED; interface with two impls → AMBIGUOUS-all.
    assert ("OwnerRepositoryImpl", "INFERRED") in injects
    assert ("EmailNotifier", "AMBIGUOUS") in injects
    assert ("SmsNotifier", "AMBIGUOUS") in injects


def test_java_jpa_persists_to_extracted(tmp_path):
    db = _build(tmp_path, "di_ladder_sample")
    with LadybugStore(db) as s:
        persists = {
            tuple(r)
            for r in s.query(
                "MATCH (m:Symbol)-[p:PERSISTS_TO]->(t:DbTable) "
                "RETURN m.qualified_name, t.table_id, p.confidence"
            )
        }
    assert ("Owner.java::Owner", "table::owners", "EXTRACTED") in persists
