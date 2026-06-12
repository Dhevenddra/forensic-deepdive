"""MCP tool-provider extractor (DEC-057, v0.5 Step 2).

Covers: ``@mcp.tool()`` function-name tools, ``@mcp.tool(name=...)`` explicit names
(the explicit name wins), hyphen normalization (``get-info`` → ``mcp::get_info``),
the FastMCP server identity surfaced on ``raw_path``, and an orphan tool (a located
provider with no consumer). All provider names are syntactic facts → EXTRACTED.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.mcp.providers.mcp_tools import extract_mcp_tool_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "mcp_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"server.py": "python", "client.py": "python"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_mcp_tool_providers(ctx)}


def test_function_name_is_the_default_tool_name(tmp_path):
    by = _extract(tmp_path)
    add = by[("mcp::add", "server.py::add")]
    assert add.confidence is Confidence.EXTRACTED
    assert add.protocol == "mcp"
    assert add.method == ""
    assert add.framework == "fastmcp"


def test_explicit_name_kwarg_wins_over_function_name(tmp_path):
    by = _extract(tmp_path)
    # function ``weather`` but @mcp.tool(name="get_weather")
    assert ("mcp::get_weather", "server.py::weather") in by
    assert ("mcp::weather", "server.py::weather") not in by


def test_hyphenated_name_is_separator_normalized(tmp_path):
    by = _extract(tmp_path)
    # @mcp.tool(name="get-info") → mcp::get_info (the consumer keys the same)
    info = by[("mcp::get_info", "server.py::info")]
    assert info.confidence is Confidence.EXTRACTED


def test_server_identity_surfaced_on_raw_path(tmp_path):
    by = _extract(tmp_path)
    # FastMCP("Demo") attributed as a display property (never part of the key).
    add = by[("mcp::add", "server.py::add")]
    assert add.raw_path == "Demo/add"


def test_orphan_tool_is_a_provider(tmp_path):
    by = _extract(tmp_path)
    # a located provider with no consumer still HANDLES its endpoint.
    assert ("mcp::orphan_tool", "server.py::orphan_tool") in by
