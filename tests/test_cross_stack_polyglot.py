"""Cross-language ROUTES_TO end-to-end (DEC-046, Item G).

The wedge across language boundaries: three provider↔consumer pairs, each in a
different stack, joined on a shared contract_id into materialized ROUTES_TO edges
in a real .lbug. This is the proof that the new consumer extractors' symbol_ids
match the graph (else the edge is silently filtered):

  FastAPI (python)  /api/users/{id}     ↔  Angular HttpClient (ts)
  Flask   (python)  /svc/items/<int:id> ↔  requests           (python)
  Spring  (java)    /spring/orders/{id} ↔  RestTemplate        (java)

Distinct path namespaces keep the three pairs from cross-joining.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "cross_stack_polyglot_sample"


def test_polyglot_routes_to(tmp_path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    assert ctx.get(BuildGraphPhase).enabled is True
    with LadybugStore(db_path) as store:
        routes = {
            (row[0], row[1], row[2])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint"
            )
        }
    assert routes == {
        # FastAPI(python) ↔ Angular(ts)
        (
            "frontend.ts::UserApi.loadUser",
            "backend_fastapi.py::get_user",
            "http::GET::/api/users/{param}",
        ),
        (
            "frontend.ts::UserApi.addUser",
            "backend_fastapi.py::create_user",
            "http::POST::/api/users",
        ),
        # Flask(python) ↔ requests(python)
        ("gateway.py::load_item", "backend_flask.py::fetch_item", "http::GET::/svc/items/{param}"),
        ("gateway.py::push_item", "backend_flask.py::add_item", "http::POST::/svc/items"),
        # Spring(java) ↔ RestTemplate(java)
        (
            "OrderClient.java::OrderClient.fetchOrder",
            "OrderController.java::OrderController.getOrder",
            "http::GET::/spring/orders/{param}",
        ),
        (
            "OrderClient.java::OrderClient.sendOrder",
            "OrderController.java::OrderController.createOrder",
            "http::POST::/spring/orders",
        ),
    }
