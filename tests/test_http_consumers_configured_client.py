"""Configured-HTTP-client consumer extractor (DEC-056, v0.5 Step 1).

Covers the SupersetClient shape: ``<Client>.<verb>({ endpoint | url | path })`` and
``<Client>.request({ method, endpoint })``, literal vs templated/numeric paths
(EXTRACTED/INFERRED), the dropped fully-dynamic endpoint, and the axios receiver
skip (owned by the fetch/axios extractor — no double emission).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.consumers.configured_client import (
    extract_configured_client_consumers,
)
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "superset_flagship_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"chart.ts": "typescript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_configured_client_consumers(ctx)}


def test_templated_endpoint_is_inferred(tmp_path):
    by = _extract(tmp_path)
    data = by[("http::GET::/api/v1/chart/{param}/data", "chart.ts::fetchChartData")]
    assert data.confidence is Confidence.INFERRED
    assert data.framework == "configured-client"


def test_literal_endpoint_is_extracted(tmp_path):
    by = _extract(tmp_path)
    created = by[("http::POST::/api/v1/chart", "chart.ts::createChart")]
    assert created.confidence is Confidence.EXTRACTED


def test_request_form_reads_method_key(tmp_path):
    by = _extract(tmp_path)
    export = by[("http::GET::/api/v1/dashboard/export", "chart.ts::exportDashboard")]
    assert export.confidence is Confidence.EXTRACTED


def test_url_and_path_keys(tmp_path):
    by = _extract(tmp_path)
    assert ("http::GET::/api/v1/tag", "chart.ts::listTags") in by  # url key
    # path key + numeric segment → INFERRED
    legacy = by[("http::DELETE::/api/v1/report/{param}", "chart.ts::legacyReport")]
    assert legacy.confidence is Confidence.INFERRED


def test_dynamic_dropped_and_axios_skipped(tmp_path):
    by = _extract(tmp_path)
    # fully-dynamic endpoint variable → no contract; axios receiver → owned elsewhere.
    assert not any(sid.endswith("dynamicEndpoint") for _, sid in by)
    assert not any("owned" in cid for cid, _ in by)
    assert {cid for cid, _ in by} == {
        "http::GET::/api/v1/chart/{param}/data",
        "http::POST::/api/v1/chart",
        "http::GET::/api/v1/dashboard/export",
        "http::GET::/api/v1/tag",
        "http::DELETE::/api/v1/report/{param}",
    }
