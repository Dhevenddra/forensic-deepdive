"""Messaging ``contract_id`` key-builder (DEC-060, v0.5 Step 5).

``<kind>::<name>`` where *kind* is ``topic`` (Kafka), ``queue`` (RabbitMQ/pika), or
``event`` (Redis/NATS/SNS — deferred). Both a publisher and a subscriber on the same
channel produce the same key → the publish↔subscribe join.
"""

from __future__ import annotations

# The Endpoint.protocol / contract_id prefix for each messaging kind.
TOPIC = "topic"
QUEUE = "queue"
EVENT = "event"


def messaging_contract_id(kind: str, name: str) -> str:
    """The canonical ``<kind>::<name>`` messaging contract id."""
    return f"{kind}::{name}"
