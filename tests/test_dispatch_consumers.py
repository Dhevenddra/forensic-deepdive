"""Registry-dispatch dispatch-site consumer extractor (DEC-058, v0.5 Step 3).

Covers: a literal-key subscript dispatch (exact key), a dynamic-key subscript
dispatch (the wildcard key), the ``.get`` dispatch form, and the enclosing-``def``
caller ``symbol_id``. All dispatch consumers are INFERRED (the join decides
unique-vs-ambiguous).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.dispatch.consumers.dispatch_sites import (
    extract_registry_consumers,
)
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "registry_dispatch_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"tools.py": "python", "agent.py": "python"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_registry_consumers(ctx)}


def test_literal_key_subscript_dispatch_is_exact(tmp_path):
    by = _extract(tmp_path)
    lit = by[("registry::registry::greet", "agent.py::run_literal")]
    assert lit.confidence is Confidence.INFERRED
    assert lit.protocol == "registry"


def test_dynamic_key_subscript_dispatch_uses_wildcard(tmp_path):
    by = _extract(tmp_path)
    # registry[var]() can hit any handler → keys the wildcard.
    assert ("registry::TOOLS::*", "agent.py::run_dynamic") in by


def test_get_dispatch_form_is_detected(tmp_path):
    by = _extract(tmp_path)
    # TOOLS.get(var)() — dynamic key → wildcard, enclosing run_get.
    assert ("registry::TOOLS::*", "agent.py::run_get") in by


def test_caller_symbols_are_enclosing_defs(tmp_path):
    by = _extract(tmp_path)
    callers = {sym for _, sym in by}
    assert callers == {
        "agent.py::run_literal",
        "agent.py::run_dynamic",
        "agent.py::run_get",
    }
