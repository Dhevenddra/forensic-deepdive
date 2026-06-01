"""Java HTTP-client consumer extractor (DEC-046, Item G).

RestTemplate (getForObject/postForObject/exchange), fluent WebClient
(get().uri()), and OpenFeign (@GetMapping / @RequestLine on a @FeignClient
interface, with the interface-level @RequestMapping prefix). literal=EXTRACTED,
param/numeric=INFERRED; a concatenated URL and /health are dropped.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.java_clients import extract_java_client_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "java_clients_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"UserClient.java": "java", "UserFeign.java": "java"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_java_client_consumers(ctx)}


def test_resttemplate_get_param_inferred(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "UserClient.java::UserClient.getUser")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # "/api/users/{id}"
    assert c.framework == "java-http-client"


def test_resttemplate_post_literal_and_exchange_verb(tmp_path):
    by = _consumers(tmp_path)
    assert (
        by[("http::POST::/api/users", "UserClient.java::UserClient.addUser")].confidence
        is Confidence.EXTRACTED
    )
    # exchange(url, HttpMethod.DELETE, …) → verb from the HttpMethod arg; "/api/users/1" numeric
    assert ("http::DELETE::/api/users/{param}", "UserClient.java::UserClient.removeUser") in by


def test_webclient_fluent_get_uri(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/things", "UserClient.java::UserClient.fetchThings")]
    assert c.confidence is Confidence.EXTRACTED  # webClient.get().uri("/api/things")


def test_openfeign_mapping_and_requestline_with_prefix(tmp_path):
    by = _consumers(tmp_path)
    # @GetMapping("/users/{id}") + interface @RequestMapping("/api") → /api/users/{id}
    get = by[("http::GET::/api/users/{param}", "UserFeign.java::UserFeign.get")]
    assert get.framework == "openfeign"
    # @RequestLine("POST /users") + prefix → POST /api/users
    create = by[("http::POST::/api/users", "UserFeign.java::UserFeign.create")]
    assert create.method == "POST"
    assert create.confidence is Confidence.EXTRACTED


def test_concat_and_health_dropped(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids
    assert all(sym != "UserClient.java::UserClient.dynamic" for _, sym in by)
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::POST::/api/users",
        "http::DELETE::/api/users/{param}",
        "http::GET::/api/things",
    }
