"""Messaging (pub/sub, queues) as a CrossBoundaryEdge protocol (DEC-060, v0.5 Step 5).

Covers the publisher (consumer) + subscriber (provider) extractors and the
publish↔subscribe join: ROUTES_TO reads publisher→subscriber. A unique subscriber →
EXTRACTED; several subscribers on one channel → AMBIGUOUS (the fan-out). Cross-language
(a Python producer joins a Java @KafkaListener).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.messaging.consumers.publishers import extract_publisher_consumers
from forensic_deepdive.contracts.messaging.providers.subscribers import extract_subscriber_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "messaging_sample"
_LANGS = {"publisher.py": "python", "subscriber.py": "python", "OrderListener.java": "java"}


def _ctx(tmp_path: Path) -> ContractContext:
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    return ContractContext(
        tags=[], imports=[], method_calls=[], source_files_by_path=dict(_LANGS), repo_path=repo
    )


def test_publishers_are_consumers(tmp_path):
    cons = {
        (c.contract_id, c.symbol_id, c.protocol)
        for c in extract_publisher_consumers(_ctx(tmp_path))
    }
    assert ("topic::orders", "publisher.py::emit_order", "topic") in cons
    assert ("queue::tasks", "publisher.py::enqueue_task", "queue") in cons


def test_subscribers_are_providers(tmp_path):
    provs = {(c.contract_id, c.symbol_id) for c in extract_subscriber_providers(_ctx(tmp_path))}
    assert ("topic::orders", "subscriber.py::consume_orders") in provs  # Kafka subscribe
    assert ("queue::tasks", "subscriber.py::consume_tasks") in provs  # pika basic_consume
    assert ("topic::orders", "OrderListener.java::OrderListener.onOrder") in provs  # @KafkaListener


def test_send_requires_a_producer_receiver(tmp_path):
    # ``.send`` on a non-producer receiver is not a publish (avoids false positives).
    repo = tmp_path / "x"
    repo.mkdir()
    (repo / "f.py").write_text("def g(sock):\n    sock.send('hello')\n")
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"f.py": "python"},
        repo_path=repo,
    )
    assert extract_publisher_consumers(ctx) == []


def _run(tmp_path: Path) -> Path:
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
    return db_path


def test_publish_subscribe_join(tmp_path):
    db = _run(tmp_path)
    with LadybugStore(db) as s:
        routes = {
            tuple(r)
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) WHERE r.via IN ['topic', 'queue'] "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }
    # queue: unique subscriber → EXTRACTED.
    assert (
        "publisher.py::enqueue_task",
        "subscriber.py::consume_tasks",
        "queue::tasks",
        "EXTRACTED",
    ) in routes
    # topic: two subscribers (Python + Java) → AMBIGUOUS fan-out, publisher→subscriber.
    orders = {(p, conf) for c, p, e, conf in routes if e == "topic::orders"}
    assert orders == {
        ("subscriber.py::consume_orders", "AMBIGUOUS"),
        ("OrderListener.java::OrderListener.onOrder", "AMBIGUOUS"),
    }
