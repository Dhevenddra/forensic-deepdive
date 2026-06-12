"""MCP ClientSession tool-consumer extractor (DEC-057, v0.5 Step 2).

Covers: a positional literal name, the ``name=`` kwarg form (joining the
hyphen-normalized provider on ``mcp::get_info``), the enclosing-``def`` caller
``symbol_id``, and the dropped dynamic-variable name (never guessed — DEC-037).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.mcp.consumers.client_session import (
    extract_client_session_consumers,
)
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
    return {(c.contract_id, c.symbol_id): c for c in extract_client_session_consumers(ctx)}


def test_positional_literal_name_is_extracted(tmp_path):
    by = _extract(tmp_path)
    add = by[("mcp::add", "client.py::run_agent")]
    assert add.confidence is Confidence.EXTRACTED
    assert add.protocol == "mcp"
    assert add.framework == "mcp-client"


def test_name_kwarg_form_is_read(tmp_path):
    by = _extract(tmp_path)
    # call_tool(name="get_info") keys mcp::get_info (joins the get-info provider).
    assert ("mcp::get_info", "client.py::run_agent") in by


def test_dynamic_name_is_dropped_never_guessed(tmp_path):
    by = _extract(tmp_path)
    # call_tool(tool_var) has no stable key → emits nothing (the only three
    # consumers are the literal/name= ones).
    assert len(by) == 3
    assert all(cid != "mcp::" for cid, _ in by)


def test_caller_symbol_is_enclosing_def(tmp_path):
    by = _extract(tmp_path)
    assert all(sym == "client.py::run_agent" for _, sym in by)
