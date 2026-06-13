"""Messaging ``contract_id`` key-builder (DEC-060, v0.5 Step 5; DEC-067, v0.6 Step 4).

``<kind>::<name>`` where *kind* is ``topic`` (Kafka), ``queue`` (RabbitMQ/pika direct /
default-exchange), ``amqp`` (RabbitMQ **topic-exchange** — keyed on the *exchange*,
DEC-067), or ``event`` (Redis/NATS/SNS — deferred). A publisher and a subscriber on the
same channel produce the same key → the publish↔subscribe join.

**AMQP topic exchanges (DEC-067).** A publisher names ``(exchange, routing_key)`` and a
subscriber binds a queue with ``(exchange, binding_pattern)``; the routing key matches the
binding pattern under AMQP topic rules (``*`` = exactly one dot-delimited word, ``#`` =
zero or more words). We key on the **shared literal exchange** (``amqp::<exchange>``) so
``base.join`` matches publisher↔subscriber by exact key **unchanged**, then a contract-
layer ``reconcile_amqp`` prune (routing_key/binding_pattern carried as edge metadata)
tests each exchange-matched candidate: exact → EXTRACTED, wildcard → INFERRED, provable
non-match → DROP, several matching subscribers → AMBIGUOUS fan-out.
"""

from __future__ import annotations

import re

# The Endpoint.protocol / contract_id prefix for each messaging kind.
TOPIC = "topic"
QUEUE = "queue"
AMQP = "amqp"
EVENT = "event"


def messaging_contract_id(kind: str, name: str) -> str:
    """The canonical ``<kind>::<name>`` messaging contract id."""
    return f"{kind}::{name}"


def amqp_contract_id(exchange: str) -> str:
    """``amqp::<exchange>`` — the topic-exchange join key (DEC-067)."""
    return f"{AMQP}::{exchange}"


def amqp_binding_matches(binding_pattern: str, routing_key: str) -> bool:
    """True when an AMQP topic *binding_pattern* matches a *routing_key* (RabbitMQ
    rules: ``*`` = exactly one dot-delimited word, ``#`` = zero or more words). Pure
    stdlib ``re`` — no broker, no network (DEC-009)."""
    rx = re.escape(binding_pattern)
    # Order matters: dot-adjacent ``#`` (zero-or-more words, absorbing the dot) before
    # the standalone ``#``; then ``*`` (one word).
    rx = rx.replace(r"\.\#", r"(?:\.[^.]+)*")  # ".#"  → zero or more ".word"
    rx = rx.replace(r"\#\.", r"(?:[^.]+\.)*")  # "#."  → zero or more "word."
    rx = rx.replace(r"\#", r"(?:[^.]+(?:\.[^.]+)*)?")  # standalone "#"
    rx = rx.replace(r"\*", r"[^.]+")  # "*"  → exactly one word
    return re.fullmatch(rx, routing_key) is not None


def amqp_match_kind(binding_pattern: str, routing_key: str) -> str | None:
    """``"exact"`` (literal equality → EXTRACTED), ``"wildcard"`` (matches via ``*``/``#``
    → INFERRED), or ``None`` (provable non-match → DROP)."""
    if binding_pattern == routing_key:
        return "exact"
    if amqp_binding_matches(binding_pattern, routing_key):
        return "wildcard"
    return None
