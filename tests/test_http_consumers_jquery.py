"""jQuery AJAX consumer extractor (DEC-046, Item G).

$.get/$.post/$.getJSON (url = arg 0) and $.ajax/jQuery.ajax ({url, method|type}).
literal=EXTRACTED, template=INFERRED; /health and a concatenated (dynamic) URL
are dropped.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.jquery import extract_jquery_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "jquery_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"app.js": "javascript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_jquery_consumers(ctx)}


def test_shorthand_get_template_inferred(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "app.js::loadUser")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # `/api/users/${id}`
    assert c.framework == "jquery"


def test_shorthand_post_and_getjson(tmp_path):
    by = _consumers(tmp_path)
    assert by[("http::POST::/api/users", "app.js::addUser")].confidence is Confidence.EXTRACTED
    # $.getJSON → GET
    assert ("http::GET::/api/users", "app.js::listUsers") in by


def test_ajax_method_and_legacy_type(tmp_path):
    by = _consumers(tmp_path)
    assert by[("http::DELETE::/api/users/{param}", "app.js::removeUser")].method == "DELETE"
    # jQuery.ajax({ type: 'PUT' }) — legacy `type` key
    assert by[("http::PUT::/api/things", "app.js::replaceThing")].method == "PUT"


def test_health_and_concat_url_dropped(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids
    assert all(sym != "app.js::dynamic" for _, sym in by)  # "/api/users/" + id dropped
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::GET::/api/users",
        "http::POST::/api/users",
        "http::DELETE::/api/users/{param}",
        "http::PUT::/api/things",
    }
