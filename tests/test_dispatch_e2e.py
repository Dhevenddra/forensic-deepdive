"""DEC-058 end-to-end — tool-registry dynamic dispatch (v0.5 Step 3).

A registration table (``@registry.register`` / ``TOOLS = {...}`` / ``registry[k]=fn``)
joins its dispatch sites (``registry[key]()`` / ``TOOLS.get(key)()``) on a shared
``registry::<id>::<key>`` ``contract_id`` — through the **unchanged** ``base.join``.
A literal-key dispatch resolves one handler (INFERRED); a dynamic-key dispatch fans
out to every handler (AMBIGUOUS-all). Keystone: only ``registry.py`` + a phases.py
wire + ``contracts/dispatch/`` changed; ``trace`` walks the bounded fan-out unchanged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.mcp_server.server import trace
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "registry_dispatch_sample"


def _run(tmp_path: Path) -> Path:
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return db_path


def _routes(db_path: Path) -> set[tuple[str, str, str, str]]:
    with LadybugStore(db_path) as store:
        return {
            (row[0], row[1], row[2], row[3])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }


def test_literal_dispatch_resolves_one_handler_inferred(tmp_path):
    routes = _routes(_run(tmp_path))
    assert (
        "agent.py::run_literal",
        "tools.py::greet_handler",
        "registry::registry::greet",
        "INFERRED",
    ) in routes


def test_dynamic_dispatch_fans_out_ambiguous_all(tmp_path):
    routes = _routes(_run(tmp_path))
    fanout = {
        (p, conf)
        for c, p, e, conf in routes
        if c == "agent.py::run_dynamic" and e == "registry::TOOLS::*"
    }
    assert fanout == {
        ("tools.py::add", "AMBIGUOUS"),
        ("tools.py::sub", "AMBIGUOUS"),
        ("tools.py::mul", "AMBIGUOUS"),
    }


def test_get_dispatch_also_fans_out(tmp_path):
    routes = _routes(_run(tmp_path))
    handlers = {p for c, p, e, _ in routes if c == "agent.py::run_get"}
    assert handlers == {"tools.py::add", "tools.py::sub", "tools.py::mul"}


def test_trace_walks_the_bounded_fanout(tmp_path):
    # The unchanged trace tool walks the dynamic dispatch → wildcard endpoint →
    # every registered handler (the bounded AMBIGUOUS fan-out).
    out = trace(_run(tmp_path), "run_dynamic", direction="downstream")
    walked = {(chain["endpoint"], chain["handler"]) for chain in out["chains"]}
    assert walked == {
        ("registry::TOOLS::*", "tools.py::add"),
        ("registry::TOOLS::*", "tools.py::sub"),
        ("registry::TOOLS::*", "tools.py::mul"),
    }
