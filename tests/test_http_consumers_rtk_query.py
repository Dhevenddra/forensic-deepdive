"""RTK Query consumer extractor (DEC-046, Item G).

builder.query/mutation → query arrow returning a url string/template or a
``{ url, method }`` object. Endpoints attribute to the file ``<module>`` symbol
(the endpoint key isn't a graph symbol); literal=EXTRACTED, template=INFERRED;
``/health`` is noise-filtered.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.rtk_query import extract_rtk_query_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "rtk_query_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"api.ts": "typescript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_rtk_query_consumers(ctx)}


def test_query_string_template_inferred(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "api.ts::<module>")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # `/api/users/${id}` template
    assert c.method == "GET"
    assert c.framework == "rtk-query"
    assert "getUser" in c.evidence


def test_query_object_literal_extracted(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users", "api.ts::<module>")]
    assert c.confidence is Confidence.EXTRACTED  # () => ({ url: '/api/users', method: 'GET' })


def test_mutation_method_from_object(tmp_path):
    by = _consumers(tmp_path)
    assert by[("http::POST::/api/users", "api.ts::<module>")].method == "POST"
    rm = by[("http::DELETE::/api/users/{param}", "api.ts::<module>")]
    assert rm.method == "DELETE"  # template url + explicit method on a mutation


def test_health_noise_dropped_and_full_set(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::GET::/api/users",
        "http::POST::/api/users",
        "http::DELETE::/api/users/{param}",
    }
