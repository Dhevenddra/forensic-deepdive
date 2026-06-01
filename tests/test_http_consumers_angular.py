"""Angular HttpClient consumer extractor (DEC-046, Item G).

this.http.<verb>(url) → CALLS_ENDPOINT attributed to the enclosing class method
(UserService.getUser — a real graph symbol). literal=EXTRACTED, template=INFERRED;
/health dropped.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.angular_http import extract_angular_http_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "angular_http_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"user.service.ts": "typescript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_angular_http_consumers(ctx)}


def test_get_template_attributes_to_method(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "user.service.ts::UserService.getUser")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # `/api/users/${id}`
    assert c.framework == "angular-httpclient"


def test_get_literal_extracted(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users", "user.service.ts::UserService.listUsers")]
    assert c.confidence is Confidence.EXTRACTED


def test_post_and_delete_verbs(tmp_path):
    by = _consumers(tmp_path)
    assert ("http::POST::/api/users", "user.service.ts::UserService.addUser") in by
    rm = by[("http::DELETE::/api/users/{param}", "user.service.ts::UserService.removeUser")]
    assert rm.method == "DELETE"


def test_health_dropped_and_full_set(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::GET::/api/users",
        "http::POST::/api/users",
        "http::DELETE::/api/users/{param}",
    }
