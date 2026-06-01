"""Python requests/httpx consumer extractor (DEC-046, Item G).

Module receivers (requests/httpx) → literal=EXTRACTED, f-string/numeric=INFERRED.
Client-var receivers (allowlisted) → always INFERRED. requests.request(METHOD,url)
form. dict.get and /health are not emitted. Enclosing def via Python _parent_chain.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.py_requests import extract_py_requests_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "py_requests_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"client.py": "python"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_py_requests_consumers(ctx)}


def test_module_fstring_inferred(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "client.py::load_user")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # f"/api/users/{user_id}"
    assert c.framework == "requests/httpx"


def test_module_literal_extracted(tmp_path):
    by = _consumers(tmp_path)
    assert by[("http::GET::/api/users", "client.py::list_users")].confidence is Confidence.EXTRACTED
    assert by[("http::POST::/api/users", "client.py::add_user")].confidence is Confidence.EXTRACTED


def test_request_form_verb_from_first_arg(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::DELETE::/api/users/{param}", "client.py::remove_user")]
    assert c.method == "DELETE"  # requests.request("DELETE", f"...")


def test_client_var_receiver_inferred_and_method_qn(tmp_path):
    by = _consumers(tmp_path)
    # client.get(...) inside a method → enclosing qn is ApiClient.fetch_things, and
    # a guessed client-var receiver is INFERRED even with a literal URL.
    c = by[("http::GET::/api/things", "client.py::ApiClient.fetch_things")]
    assert c.confidence is Confidence.INFERRED


def test_dict_get_and_health_not_emitted(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids  # requests.get('/health') noise
    # d.get(key) must not be mistaken for an HTTP call
    assert all(sym != "client.py::lookup" for _, sym in by)
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::GET::/api/users",
        "http::POST::/api/users",
        "http::DELETE::/api/users/{param}",
        "http::GET::/api/things",
    }
