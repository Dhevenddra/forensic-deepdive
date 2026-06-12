"""Messaging publisher-consumer extractor (DEC-060, v0.5 Step 5).

A publisher sends to a channel — the CALLS_ENDPOINT side (ROUTES_TO publisher→
subscriber). Two Python shapes::

    producer.send("orders", value=b"...")        # Kafka → topic::orders
    channel.basic_publish(routing_key="tasks")    # pika  → queue::tasks

Kafka ``.send``/``.produce`` is guarded by a producer-ish receiver-name allowlist
(``.send`` is otherwise far too common); pika ``basic_publish`` reads the
``routing_key`` kwarg. Literal channel name → EXTRACTED; caller ``symbol_id`` via the
reused ``_enclosing_symbol``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.consumers.py_requests import _enclosing_symbol, _walk
from forensic_deepdive.contracts.http.scan import (
    first_positional_string,
    iter_candidate_files,
    keyword_arg_value,
)
from forensic_deepdive.contracts.messaging.normalize import QUEUE, TOPIC, messaging_contract_id
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b".send(", b".produce(", b"basic_publish")
_LANGS = ("python",)
# Producer-ish receiver names — ``.send``/``.produce`` only count on these.
_PRODUCER_RECVS = frozenset({"producer", "_producer", "kafka_producer", "kafka", "self"})


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _receiver_name(fn: Node, src: bytes) -> str | None:
    obj = fn.child_by_field_name("object")
    if obj is None:
        return None
    if obj.type == "identifier":
        return _text(obj, src)
    if obj.type == "attribute":  # self.producer → producer
        attr = obj.child_by_field_name("attribute")
        return _text(attr, src) if attr is not None else None
    return None


def _classify(call: Node, src: bytes) -> tuple[str, str] | None:
    """``(kind, channel)`` for a publisher call, or ``None``."""
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return None
    attr = fn.child_by_field_name("attribute")
    args = call.child_by_field_name("arguments")
    if attr is None or args is None:
        return None
    method = _text(attr, src)
    if method in ("send", "produce"):
        recv = _receiver_name(fn, src)
        if recv is None or recv not in _PRODUCER_RECVS:
            return None
        topic = first_positional_string(args, src)
        return (TOPIC, topic) if topic else None
    if method == "basic_publish":
        key = keyword_arg_value(args, "routing_key", src)
        return (QUEUE, key) if key else None
    return None


def extract_publisher_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call":
                continue
            classified = _classify(node, src)
            if classified is None:
                continue
            kind, channel = classified
            contract_id = messaging_contract_id(kind, channel)
            symbol_id = _enclosing_symbol(node, src, rel_path)
            if (contract_id, symbol_id) in seen:
                continue
            seen.add((contract_id, symbol_id))
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=Confidence.EXTRACTED,
                    evidence=f"publish {kind}::{channel}",
                    protocol=kind,
                    normalized_path=channel,
                    raw_path=channel,
                    framework="messaging",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
