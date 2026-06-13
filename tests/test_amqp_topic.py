"""AMQP topic-exchange + binding-key topology (DEC-067, v0.6 Step 4).

Pub/sub keyed on the shared-literal **exchange** (``amqp::<exchange>``) so base.join
matches unchanged; reconcile_amqp then refines each exchange-matched pair by the AMQP
topic match between the publisher routing_key and the subscriber binding_pattern:
exact → EXTRACTED, wildcard → INFERRED, provable non-match → DROP, multi → AMBIGUOUS.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.base import Contract, ContractRole, CrossLink, reconcile_amqp
from forensic_deepdive.contracts.messaging.normalize import amqp_binding_matches, amqp_match_kind
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "amqp_topic_sample"


# --- the wildcard matcher (pure) --------------------------------------------


def test_amqp_binding_matches():
    assert amqp_binding_matches("kern.*", "kern.critical")
    assert not amqp_binding_matches("kern.*", "kern.a.b")  # * = exactly one word
    assert amqp_binding_matches("kern.#", "kern.a.b")  # # = zero or more
    assert amqp_binding_matches("kern.#", "kern")  # # matches zero words
    assert amqp_binding_matches("#", "anything.at.all")
    assert amqp_binding_matches("*.critical", "kern.critical")
    assert not amqp_binding_matches("auth.*", "kern.critical")


def test_amqp_match_kind():
    assert amqp_match_kind("kern.critical", "kern.critical") == "exact"
    assert amqp_match_kind("kern.*", "kern.critical") == "wildcard"
    assert amqp_match_kind("auth.*", "kern.critical") is None


# --- reconcile_amqp prune (unit) --------------------------------------------


def _pub(sym, ex, rk):
    return Contract(
        ContractRole.CONSUMER,
        f"amqp::{ex}",
        sym,
        Confidence.EXTRACTED,
        protocol="amqp",
        match_key=rk,
    )


def _sub(sym, ex, bp):
    return Contract(
        ContractRole.PROVIDER,
        f"amqp::{ex}",
        sym,
        Confidence.EXTRACTED,
        protocol="amqp",
        match_key=bp,
    )


def _link(pub, sub, ex):
    return CrossLink(pub, sub, f"amqp::{ex}", Confidence.AMBIGUOUS, "amqp")


def test_reconcile_amqp_prunes_and_reconfidences():
    pub = _pub("p::emit", "logs", "kern.critical")
    sub_match = _sub("c::kern", "logs", "kern.*")
    sub_drop = _sub("c::auth", "logs", "auth.*")
    links = [_link("p::emit", "c::kern", "logs"), _link("p::emit", "c::auth", "logs")]
    out = reconcile_amqp(links, [sub_match, sub_drop], [pub])
    # auth.* dropped (provable non-match); kern.* kept as a single INFERRED wildcard match.
    assert [(cl.provider_symbol_id, cl.confidence.value) for cl in out] == [("c::kern", "INFERRED")]


def test_reconcile_amqp_exact_is_extracted():
    pub = _pub("p::e", "events", "user.created")
    sub = _sub("c::e", "events", "user.created")
    out = reconcile_amqp([_link("p::e", "c::e", "events")], [sub], [pub])
    assert out[0].confidence is Confidence.EXTRACTED


def test_reconcile_amqp_non_amqp_passthrough():
    cl = CrossLink("a", "b", "http::GET::/x", Confidence.EXTRACTED, "http")
    assert reconcile_amqp([cl], [], []) == [cl]


# --- full-pipeline acceptance -----------------------------------------------


def test_amqp_topic_routes_to(tmp_path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    db_path = tmp_path / "graph.lbug"
    PipelineRunner(default_phases()).run(
        ExtractConfig(
            repo_path=repo,
            output_dir=tmp_path / "out",
            flatten=False,
            write_editor_shims=False,
            build_graph_db=True,
            graph_db_path=db_path,
        )
    )
    with LadybugStore(db_path) as s:
        routes = {
            (r[0], r[1], r[2], r[3])
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) WHERE r.via='amqp' "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }
    prod, cons = "producers.py", "consumers.py"
    # wildcard kern.* matches kern.critical → INFERRED.
    assert (f"{prod}::emit_log", f"{cons}::bind_kern", "amqp::logs", "INFERRED") in routes
    # auth.* does NOT match kern.critical → dropped (no edge to bind_auth).
    assert not any(r[1] == f"{cons}::bind_auth" for r in routes)
    # exact user.created → EXTRACTED.
    assert (f"{prod}::emit_event", f"{cons}::bind_event", "amqp::events", "EXTRACTED") in routes
    # a.b matches both a.* and a.b → AMBIGUOUS fan-out (every candidate).
    star = (f"{prod}::emit_multi", f"{cons}::bind_multi_star", "amqp::multi", "AMBIGUOUS")
    exact = (f"{prod}::emit_multi", f"{cons}::bind_multi_exact", "amqp::multi", "AMBIGUOUS")
    assert star in routes
    assert exact in routes
