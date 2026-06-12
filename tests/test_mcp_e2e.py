"""DEC-057 end-to-end — MCP as a CrossBoundaryEdge protocol (v0.5 Step 2, the
headline + the keystone proof).

A FastMCP provider (``@mcp.tool()``) joins an MCP ``ClientSession.call_tool("name")``
consumer on a shared ``mcp::<tool>`` ``contract_id`` → a materialized ``ROUTES_TO``
graph with ``via='mcp'`` — through the **unchanged** ``base.join``/``Endpoint``
spine. The keystone (DEC-055): only ``registry.py`` + ``contracts/mcp/`` changed;
``trace``/emit/``serve`` query logic is untouched, yet the ``mcp`` edges light up.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.mcp_server.server import trace
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "mcp_sample"


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


def _routes(db_path: Path) -> set[tuple[str, str, str, str, str]]:
    with LadybugStore(db_path) as store:
        return {
            (row[0], row[1], row[2], row[3], row[4])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence, r.via"
            )
        }


def test_mcp_routes_to_materializes(tmp_path):
    routes = _routes(_run(tmp_path))
    assert routes == {
        ("client.py::run_agent", "server.py::add", "mcp::add", "EXTRACTED", "mcp"),
        (
            "client.py::run_agent",
            "server.py::weather",
            "mcp::get_weather",
            "EXTRACTED",
            "mcp",
        ),
        # hyphen-normalized provider get-info joins the get_info consumer
        (
            "client.py::run_agent",
            "server.py::info",
            "mcp::get_info",
            "EXTRACTED",
            "mcp",
        ),
    }


def test_orphan_tool_handles_without_route(tmp_path):
    db_path = _run(tmp_path)
    # orphan_tool is a located provider with no consumer → HANDLES, no ROUTES_TO.
    assert not any(p == "server.py::orphan_tool" for _, p, _, _, _ in _routes(db_path))
    with LadybugStore(db_path) as store:
        handled = {
            row[0]
            for row in store.query(
                "MATCH (s:Symbol)-[:HANDLES]->(e:Endpoint) "
                "WHERE e.contract_id = 'mcp::orphan_tool' RETURN s.qualified_name"
            )
        }
    assert handled == {"server.py::orphan_tool"}


def test_trace_walks_agent_to_tool_to_handler(tmp_path):
    # The keystone proof at runtime: the UNCHANGED ``trace`` tool walks
    # agent → MCP tool → handler purely because the mcp edges reuse the
    # Endpoint/HANDLES/CALLS_ENDPOINT spine (no protocol branch in trace).
    db_path = _run(tmp_path)
    out = trace(db_path, "run_agent", direction="downstream")
    walked = {(chain["consumer"], chain["endpoint"], chain["handler"]) for chain in out["chains"]}
    assert walked == {
        ("client.py::run_agent", "mcp::add", "server.py::add"),
        ("client.py::run_agent", "mcp::get_info", "server.py::info"),
        ("client.py::run_agent", "mcp::get_weather", "server.py::weather"),
    }


def test_endpoints_carry_the_mcp_protocol(tmp_path):
    db_path = _run(tmp_path)
    with LadybugStore(db_path) as store:
        protocols = {
            row[0]
            for row in store.query(
                "MATCH (e:Endpoint) WHERE e.contract_id STARTS WITH 'mcp::' RETURN e.protocol"
            )
        }
    assert protocols == {"mcp"}
