"""Flask-AppBuilder route-provider extractor (DEC-056, v0.5 Step 1).

Covers FAB's class-/convention-driven routing: ``resource_name`` and explicit
``route_base`` prefixes (EXTRACTED), the class-name convention fallback
(INFERRED), the bare-``@expose`` GET default, ``methods=[...]`` expansion, the
``<pk>`` angle param, and the enclosing-class guard (a ``ModelView`` is ignored).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.flask_appbuilder import (
    extract_flask_appbuilder_providers,
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
        source_files_by_path={"api.py": "python"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_flask_appbuilder_providers(ctx)}


def test_resource_name_prefix_extracted_and_angle_param(tmp_path):
    by = _extract(tmp_path)
    data = by[("http::GET::/api/v1/chart/{param}/data", "api.py::ChartRestApi.data")]
    assert data.confidence is Confidence.EXTRACTED  # resource_name literal
    assert data.framework == "flask-appbuilder"


def test_resource_name_root_post(tmp_path):
    by = _extract(tmp_path)
    created = by[("http::POST::/api/v1/chart", "api.py::ChartRestApi.bulk_create")]
    assert created.confidence is Confidence.EXTRACTED


def test_explicit_route_base_extracted_and_default_get(tmp_path):
    by = _extract(tmp_path)
    # @expose("/export/") with no methods= → GET; route_base literal → EXTRACTED
    export = by[("http::GET::/api/v1/dashboard/export", "api.py::DashboardRestApi.export")]
    assert export.confidence is Confidence.EXTRACTED


def test_class_name_convention_is_inferred(tmp_path):
    by = _extract(tmp_path)
    # LogRestApi has no resource_name/route_base → /api/v1/log convention, INFERRED
    recent = by[("http::GET::/api/v1/log/recent", "api.py::LogRestApi.recent")]
    assert recent.confidence is Confidence.INFERRED


def test_modelview_ignored_and_exact_set(tmp_path):
    by = _extract(tmp_path)
    # WidgetView(ModelView) is not a FAB API → no route emitted for it.
    assert {cid for cid, _ in by} == {
        "http::GET::/api/v1/chart/{param}/data",
        "http::POST::/api/v1/chart",
        "http::GET::/api/v1/dashboard/export",
        "http::GET::/api/v1/log/recent",
    }
    assert not any("widget" in sid.lower() for _, sid in by)
