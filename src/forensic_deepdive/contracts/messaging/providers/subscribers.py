"""Messaging subscriber-provider extractor (DEC-060, v0.5 Step 5).

A subscriber/listener processes a channel — the HANDLES side. Shapes::

    consumer.subscribe(["orders"])                                # Kafka  → topic::orders
    channel.basic_consume(queue="tasks")                          # pika   → queue::tasks
    channel.queue_declare("tasks")                                # pika   → queue::tasks
    channel.queue_bind(exchange="logs", routing_key="kern.*")     # pika topic → amqp::logs

    @KafkaListener(topics = "orders")                             # Spring → topic::orders
    public void onMessage(String m) { ... }

The Python subscription site's provider ``symbol_id`` is the enclosing function (the
code that owns the subscription); the Java listener's is the annotated method (via
``_parent_chain``). A ``queue_bind`` to a named **exchange** keys on the exchange
(``amqp::<exchange>``) and carries the ``routing_key`` as the ``binding_pattern``
(``match_key``, DEC-067); the routing/binding match is refined by ``reconcile_amqp``. A
literal channel → EXTRACTED.
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
    string_list_values,
)
from forensic_deepdive.contracts.messaging.normalize import (
    AMQP,
    QUEUE,
    TOPIC,
    messaging_contract_id,
)
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_PY_MARKERS = (b".subscribe(", b"basic_consume", b"queue_declare", b"queue_bind")
_JAVA_MARKERS = (b"KafkaListener",)
_CONSUMER_RECVS = frozenset({"consumer", "_consumer", "kafka_consumer", "kafka", "self"})


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _receiver_name(fn: Node, src: bytes) -> str | None:
    obj = fn.child_by_field_name("object")
    if obj is None:
        return None
    if obj.type == "identifier":
        return _text(obj, src)
    if obj.type == "attribute":
        attr = obj.child_by_field_name("attribute")
        return _text(attr, src) if attr is not None else None
    return None


def _py_channels(call: Node, src: bytes) -> list[tuple[str, str, str]]:
    """``[(kind, channel, match_key), ...]`` for a Python subscriber call (subscribe may
    name several topics), or ``[]``. ``match_key`` is the AMQP binding pattern (only for
    ``amqp::``), else ``""``."""
    fn = call.child_by_field_name("function")
    if fn is None or fn.type != "attribute":
        return []
    attr = fn.child_by_field_name("attribute")
    args = call.child_by_field_name("arguments")
    if attr is None or args is None:
        return []
    method = _text(attr, src)
    if method == "subscribe":
        if _receiver_name(fn, src) not in _CONSUMER_RECVS:
            return []
        list_node = next((c for c in args.children if c.type == "list"), None)
        topics = string_list_values(list_node, src) if list_node is not None else []
        return [(TOPIC, t, "") for t in topics]
    if method == "basic_consume":
        q = keyword_arg_value(args, "queue", src)
        return [(QUEUE, q, "")] if q else []
    if method == "queue_declare":
        q = keyword_arg_value(args, "queue", src) or first_positional_string(args, src)
        return [(QUEUE, q, "")] if q else []
    if method == "queue_bind":  # pika topic-exchange binding (DEC-067)
        exchange = keyword_arg_value(args, "exchange", src)
        binding = keyword_arg_value(args, "routing_key", src)
        if exchange:
            return [(AMQP, exchange, binding or "")]
    return []


def _extract_python(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    out: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(
        ctx, languages=("python",), markers=_PY_MARKERS
    ):
        for node in _walk(root):
            if node.type != "call":
                continue
            for kind, channel, match_key in _py_channels(node, src):
                contract_id = messaging_contract_id(kind, channel)
                symbol_id = _enclosing_symbol(node, src, rel_path)
                if (contract_id, symbol_id) in seen:
                    continue
                seen.add((contract_id, symbol_id))
                out.append(
                    _provider(
                        contract_id,
                        symbol_id,
                        kind,
                        channel,
                        rel_path,
                        node.start_point[0],
                        match_key,
                    )
                )
    return out


def _extract_java(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    out: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(
        ctx, languages=("java",), markers=_JAVA_MARKERS
    ):
        for node in _walk(root):
            if node.type != "method_declaration":
                continue
            name_node = node.child_by_field_name("name")
            if name_node is None:
                continue
            for child in node.children:
                if child.type != "modifiers":
                    continue
                for deco in child.children:
                    if deco.type not in ("annotation", "marker_annotation"):
                        continue
                    name = deco.child_by_field_name("name")
                    if name is None or _text(name, src) != "KafkaListener":
                        continue
                    topics = _kafka_listener_topics_from_anno(deco, src)
                    parent = _parent_chain(name_node, "java")
                    method = _text(name_node, src)
                    qn_local = f"{parent}.{method}" if parent else method
                    symbol_id = f"{rel_path}::{qn_local}"
                    for topic in topics:
                        contract_id = messaging_contract_id(TOPIC, topic)
                        if (contract_id, symbol_id) in seen:
                            continue
                        seen.add((contract_id, symbol_id))
                        out.append(
                            _provider(
                                contract_id,
                                symbol_id,
                                TOPIC,
                                topic,
                                rel_path,
                                name_node.start_point[0],
                            )
                        )
    return out


def _kafka_listener_topics_from_anno(anno: Node, src: bytes) -> list[str]:
    args = anno.child_by_field_name("arguments")
    if args is None:
        return []
    for el in args.children:
        if el.type != "element_value_pair":
            continue
        key = el.child_by_field_name("key")
        val = el.child_by_field_name("value")
        if key is None or val is None or _text(key, src) != "topics":
            continue
        if val.type == "string_literal":
            return ["".join(_text(c, src) for c in val.children if c.type == "string_fragment")]
        if val.type == "array_initializer":
            out: list[str] = []
            for m in val.children:
                if m.type == "string_literal":
                    out.append(
                        "".join(_text(c, src) for c in m.children if c.type == "string_fragment")
                    )
            return out
    return []


def _provider(
    contract_id: str,
    symbol_id: str,
    kind: str,
    channel: str,
    rel_path: str,
    line: int,
    match_key: str = "",
) -> Contract:
    ev = f"subscribe {kind}::{channel}" + (f" bind={match_key}" if match_key else "")
    return Contract(
        role=ContractRole.PROVIDER,
        contract_id=contract_id,
        symbol_id=symbol_id,
        confidence=Confidence.EXTRACTED,
        evidence=ev,
        protocol=kind,
        normalized_path=channel,
        raw_path=channel,
        framework="messaging",
        rel_path=rel_path,
        line=line,
        match_key=match_key,
    )


def extract_subscriber_providers(ctx: ContractContext) -> list[Contract]:
    return _extract_python(ctx) + _extract_java(ctx)
