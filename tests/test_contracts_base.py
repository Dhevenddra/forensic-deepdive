"""The CrossBoundaryEdge join (DEC-043, v0.4 Item D).

Pure tests of base.join against synthetic Contract lists — the abstraction +
determinism are proven ahead of the HTTP extractors (Items F/G).
"""

from __future__ import annotations

from forensic_deepdive.contracts import Contract, ContractRole, join
from forensic_deepdive.graph.schema import Confidence


def _provider(contract_id: str, symbol_id: str, **kw) -> Contract:
    return Contract(
        role=ContractRole.PROVIDER,
        contract_id=contract_id,
        symbol_id=symbol_id,
        confidence=Confidence.EXTRACTED,
        rel_path=kw.get("rel_path", "back/api.py"),
        line=kw.get("line", 0),
    )


def _consumer(contract_id: str, symbol_id: str, **kw) -> Contract:
    return Contract(
        role=ContractRole.CONSUMER,
        contract_id=contract_id,
        symbol_id=symbol_id,
        confidence=Confidence.EXTRACTED,
        rel_path=kw.get("rel_path", "front/app.ts"),
        line=kw.get("line", 0),
    )


def test_join_groups_by_contract_id_single_pair() -> None:
    links = join(
        providers=[_provider("http::GET::/u/{param}", "back/api.py::get_user")],
        consumers=[_consumer("http::GET::/u/{param}", "front/app.ts::fetchUser")],
    )
    assert len(links) == 1
    link = links[0]
    assert link.consumer_symbol_id == "front/app.ts::fetchUser"
    assert link.provider_symbol_id == "back/api.py::get_user"
    assert link.contract_id == "http::GET::/u/{param}"
    assert link.confidence == Confidence.INFERRED  # unique provider, Item D baseline
    assert link.via == "http"


def test_fan_in_many_consumers_one_provider() -> None:
    cid = "http::POST::/orders"
    links = join(
        providers=[_provider(cid, "back/api.py::create_order")],
        consumers=[
            _consumer(cid, "front/a.ts::submitA", line=1),
            _consumer(cid, "front/b.ts::submitB", line=2),
        ],
    )
    assert len(links) == 2
    assert {link.consumer_symbol_id for link in links} == {
        "front/a.ts::submitA",
        "front/b.ts::submitB",
    }
    assert all(link.provider_symbol_id == "back/api.py::create_order" for link in links)
    assert all(link.confidence == Confidence.INFERRED for link in links)


def test_multiple_providers_same_contract_are_ambiguous() -> None:
    cid = "http::GET::/items"
    links = join(
        providers=[
            _provider(cid, "back/v1.py::list_items", line=1),
            _provider(cid, "back/v2.py::list_items", line=2),
        ],
        consumers=[_consumer(cid, "front/app.ts::loadItems")],
    )
    # All candidate links surfaced, every one AMBIGUOUS (never pick one).
    assert len(links) == 2
    assert all(link.confidence == Confidence.AMBIGUOUS for link in links)
    assert {link.provider_symbol_id for link in links} == {
        "back/v1.py::list_items",
        "back/v2.py::list_items",
    }


def test_consumer_with_no_provider_yields_no_link() -> None:
    # The honest "calls an endpoint we can't locate" — no ROUTES_TO; the
    # CALLS_ENDPOINT → Endpoint is kept at persistence, not here.
    links = join(
        providers=[_provider("http::GET::/known", "back/api.py::known")],
        consumers=[_consumer("http::GET::/unknown", "front/app.ts::callUnknown")],
    )
    assert links == []


def test_join_is_deterministic_regardless_of_input_order() -> None:
    cid = "http::GET::/x"
    providers = [
        _provider(cid, "back/b.py::h", line=2),
        _provider(cid, "back/a.py::h", line=1),
    ]
    consumers = [
        _consumer(cid, "front/z.ts::c", line=2),
        _consumer(cid, "front/a.ts::c", line=1),
    ]
    forward = join(providers, consumers)
    reversed_ = join(list(reversed(providers)), list(reversed(consumers)))
    key = lambda link: (link.consumer_symbol_id, link.provider_symbol_id)  # noqa: E731
    assert [key(x) for x in forward] == [key(x) for x in reversed_]
    # Sorted by (consumer, provider).
    assert [key(x) for x in forward] == sorted(key(x) for x in forward)
