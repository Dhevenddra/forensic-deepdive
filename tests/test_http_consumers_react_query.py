"""React Query / TanStack consumer extractor (DEC-046, Item G).

useQuery/useMutation wrapping fetch/axios in queryFn/mutationFn → CALLS_ENDPOINT
attributed to the enclosing component/hook (a real graph symbol), not the
anonymous queryFn arrow. literal=EXTRACTED, template=INFERRED; /health dropped.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.react_query import extract_react_query_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "react_query_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"hooks.tsx": "tsx"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_react_query_consumers(ctx)}


def test_query_fn_template_attributes_to_hook(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "hooks.tsx::useUser")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # `/api/users/${id}`
    assert c.framework == "react-query"


def test_query_fn_literal_extracted(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users", "hooks.tsx::useUserList")]
    assert c.confidence is Confidence.EXTRACTED  # literal '/api/users'


def test_mutation_fn_axios_verb(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::POST::/api/users", "hooks.tsx::useAddUser")]
    assert c.method == "POST"  # axios.post inside mutationFn


def test_health_dropped_and_full_set(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids  # useHealth wraps fetch('/health')
    # attribution is to the real enclosing component, never the queryFn arrow
    assert all(not sym.endswith("::queryFn") for _, sym in by)
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::GET::/api/users",
        "http::POST::/api/users",
    }
