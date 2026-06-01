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
        confidence=kw.get("confidence", Confidence.EXTRACTED),
        spec_backed=kw.get("spec_backed", False),
        normalized_path=kw.get("normalized_path", ""),
        rel_path=kw.get("rel_path", "back/api.py"),
        line=kw.get("line", 0),
    )


def _consumer(contract_id: str, symbol_id: str, **kw) -> Contract:
    return Contract(
        role=ContractRole.CONSUMER,
        contract_id=contract_id,
        symbol_id=symbol_id,
        confidence=kw.get("confidence", Confidence.EXTRACTED),
        normalized_path=kw.get("normalized_path", ""),
        rel_path=kw.get("rel_path", "front/app.ts"),
        line=kw.get("line", 0),
    )


def test_unique_both_literal_is_extracted() -> None:
    # DEC-047: a unique match where both sides are literal (EXTRACTED) → EXTRACTED.
    links = join(
        providers=[_provider("http::POST::/users", "back/api.py::create_user")],
        consumers=[_consumer("http::POST::/users", "front/app.ts::addUser")],
    )
    assert len(links) == 1
    link = links[0]
    assert link.consumer_symbol_id == "front/app.ts::addUser"
    assert link.provider_symbol_id == "back/api.py::create_user"
    assert link.contract_id == "http::POST::/users"
    assert link.confidence == Confidence.EXTRACTED
    assert link.via == "http"


def test_unique_one_side_inferred_is_inferred() -> None:
    # DEC-047: a param/template-generalized consumer (INFERRED) demotes the join,
    # even with a literal (EXTRACTED) provider.
    links = join(
        providers=[_provider("http::GET::/u/{param}", "back/api.py::get_user")],
        consumers=[
            _consumer(
                "http::GET::/u/{param}", "front/app.ts::fetchUser", confidence=Confidence.INFERRED
            )
        ],
    )
    assert len(links) == 1
    assert links[0].confidence == Confidence.INFERRED


def test_spec_backed_provider_is_extracted_even_if_consumer_inferred() -> None:
    # DEC-047: a spec-backed provider (Item I) → EXTRACTED regardless of the
    # consumer's per-edge confidence.
    links = join(
        providers=[_provider("http::GET::/u/{param}", "back/api.py::get_user", spec_backed=True)],
        consumers=[
            _consumer(
                "http::GET::/u/{param}", "front/app.ts::fetchUser", confidence=Confidence.INFERRED
            )
        ],
    )
    assert links[0].confidence == Confidence.EXTRACTED


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
    # one provider per consumer, both sides literal → EXTRACTED (DEC-047)
    assert all(link.confidence == Confidence.EXTRACTED for link in links)


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


def _http_keys(consumer):
    # Mirror ContractPhase's HTTP match_keys: exact, then method-wildcard.
    from forensic_deepdive.contracts.http.normalize import http_wildcard_id

    return (consumer.contract_id, http_wildcard_id(consumer.normalized_path))


def test_method_wildcard_fallback_is_inferred() -> None:
    # DEC-047: a GET consumer with no exact provider matches a `*` (bare
    # @RequestMapping) provider on the same path — INFERRED (verb undeclared).
    links = join(
        providers=[
            _provider("http::*::/items", "back/api.py::handle_items", normalized_path="/items")
        ],
        consumers=[
            _consumer("http::GET::/items", "front/app.ts::loadItems", normalized_path="/items")
        ],
        match_keys=_http_keys,
    )
    assert len(links) == 1
    link = links[0]
    assert link.provider_symbol_id == "back/api.py::handle_items"
    assert link.contract_id == "http::GET::/items"  # consumer's concrete id is kept
    assert link.confidence == Confidence.INFERRED
    assert link.evidence == "contract-join-wildcard"


def test_exact_match_preferred_over_wildcard() -> None:
    # An exact provider wins over a co-present wildcard provider (no double link).
    links = join(
        providers=[
            _provider("http::GET::/items", "back/api.py::list_items", normalized_path="/items"),
            _provider("http::*::/items", "back/api.py::any_items", normalized_path="/items"),
        ],
        consumers=[
            _consumer("http::GET::/items", "front/app.ts::loadItems", normalized_path="/items")
        ],
        match_keys=_http_keys,
    )
    assert len(links) == 1
    assert links[0].provider_symbol_id == "back/api.py::list_items"
    assert links[0].confidence == Confidence.EXTRACTED  # exact, both literal


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
