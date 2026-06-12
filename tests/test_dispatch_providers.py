"""Registry-dispatch registration-provider extractor (DEC-058, v0.5 Step 3).

Covers the three registration shapes (decorator literal-key, bare decorator =
function name, dict-literal, subscript-assign), the exact + wildcard provider pair
per registration, and the per-registry fan-out cap (deterministic, capped at 25).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.dispatch.providers.registrations import (
    _FANOUT_CAP,
    extract_registry_providers,
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
    return {(c.contract_id, c.symbol_id): c for c in extract_registry_providers(ctx)}


def test_decorator_literal_key_registration(tmp_path):
    by = _extract(tmp_path)
    greet = by[("registry::registry::greet", "tools.py::greet_handler")]
    assert greet.confidence is Confidence.INFERRED
    assert greet.protocol == "registry"
    assert greet.framework == "registry-dispatch"


def test_bare_decorator_uses_function_name(tmp_path):
    by = _extract(tmp_path)
    # @registry.register (bare) → key = the function name "wave"
    assert ("registry::registry::wave", "tools.py::wave") in by


def test_dict_literal_and_subscript_registrations(tmp_path):
    by = _extract(tmp_path)
    assert ("registry::TOOLS::add", "tools.py::add") in by  # dict literal
    assert ("registry::TOOLS::sub", "tools.py::sub") in by  # dict literal
    assert ("registry::TOOLS::mul", "tools.py::mul") in by  # subscript assign


def test_each_registration_emits_an_exact_and_wildcard_provider(tmp_path):
    by = _extract(tmp_path)
    # add is registered → reachable by its exact key AND the dynamic wildcard.
    assert ("registry::TOOLS::add", "tools.py::add") in by
    assert ("registry::TOOLS::*", "tools.py::add") in by


def test_wildcard_holds_every_tools_handler(tmp_path):
    by = _extract(tmp_path)
    wildcard_handlers = {sym for (cid, sym) in by if cid == "registry::TOOLS::*"}
    assert wildcard_handlers == {"tools.py::add", "tools.py::sub", "tools.py::mul"}


def test_fanout_cap_is_deterministic_and_bounded(tmp_path):
    # A registry larger than the cap emits all exact providers (full HANDLES) but
    # caps the wildcard fan-out at _FANOUT_CAP, deterministically.
    repo = tmp_path / "big"
    repo.mkdir()
    n = _FANOUT_CAP + 5
    body = [f"def h{i}(): pass" for i in range(n)]
    body.append("BIG = {" + ", ".join(f'"k{i}": h{i}' for i in range(n)) + "}")
    (repo / "big.py").write_text("\n".join(body))
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"big.py": "python"},
        repo_path=repo,
    )
    provs = extract_registry_providers(ctx)
    exact = [c for c in provs if c.contract_id != "registry::BIG::*"]
    wildcard = [c for c in provs if c.contract_id == "registry::BIG::*"]
    assert len(exact) == n  # every registration keeps its named endpoint
    assert len(wildcard) == _FANOUT_CAP  # fan-out is capped
    # deterministic: the kept wildcard handlers are the sorted-first _FANOUT_CAP.
    kept = [c.symbol_id for c in wildcard]
    assert kept == sorted(kept)
