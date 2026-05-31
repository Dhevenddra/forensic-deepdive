"""LadybugStore round-trip for the cross-boundary schema (DEC-043, Item D).

Validates the Endpoint node (incl. the BOOLEAN ``spec_backed`` column) and the
HANDLES / CALLS_ENDPOINT / ROUTES_TO edges against a real .lbug.
"""

from __future__ import annotations

from forensic_deepdive.graph import (
    CallsEndpointEdge,
    Confidence,
    Endpoint,
    HandlesEdge,
    LadybugStore,
    RoutesToEdge,
    Symbol,
    SymbolKind,
)


def _symbol(qn: str) -> Symbol:
    return Symbol(
        qualified_name=qn,
        kind=SymbolKind.FUNCTION,
        file_path=qn.split("::", 1)[0],
        line_start=1,
        line_end=2,
    )


def test_endpoint_and_cross_boundary_edges_round_trip(tmp_path) -> None:
    db = tmp_path / "g.lbug"
    handler = "back/api.py::get_user"
    caller = "front/app.ts::fetchUser"
    cid = "http::GET::/users/{param}"

    with LadybugStore(db) as store:
        store.add_many_symbols([_symbol(handler), _symbol(caller)])
        store.add_many_endpoints(
            [
                Endpoint(
                    contract_id=cid,
                    protocol="http",
                    method="GET",
                    normalized_path="/users/{param}",
                    raw_path_samples="/users/{id}, /users/:id",
                    framework="fastapi",
                    spec_backed=True,
                )
            ]
        )
        store.add_many_handles(
            [HandlesEdge(symbol=handler, contract_id=cid, confidence=Confidence.EXTRACTED)]
        )
        store.add_many_calls_endpoint(
            [CallsEndpointEdge(symbol=caller, contract_id=cid, confidence=Confidence.EXTRACTED)]
        )
        store.add_many_routes_to(
            [
                RoutesToEdge(
                    consumer=caller,
                    provider=handler,
                    via="http",
                    endpoint=cid,
                    confidence=Confidence.INFERRED,
                )
            ]
        )

    with LadybugStore(db) as store:
        # Endpoint node, incl. the BOOLEAN spec_backed.
        rows = list(
            store.query(
                "MATCH (e:Endpoint) RETURN e.contract_id, e.protocol, e.method, "
                "e.framework, e.spec_backed"
            )
        )
        assert rows == [[cid, "http", "GET", "fastapi", True]]

        # HANDLES: handler → endpoint.
        handles = list(
            store.query(
                "MATCH (s:Symbol)-[:HANDLES]->(e:Endpoint) RETURN s.qualified_name, e.contract_id"
            )
        )
        assert handles == [[handler, cid]]

        # CALLS_ENDPOINT: caller → endpoint.
        calls_ep = list(
            store.query(
                "MATCH (s:Symbol)-[:CALLS_ENDPOINT]->(e:Endpoint) "
                "RETURN s.qualified_name, e.contract_id"
            )
        )
        assert calls_ep == [[caller, cid]]

        # ROUTES_TO: consumer → provider, carrying via + endpoint + confidence.
        routes = list(
            store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.via, r.endpoint, r.confidence"
            )
        )
        assert routes == [[caller, handler, "http", cid, "INFERRED"]]
