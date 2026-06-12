"""Messaging (pub/sub, queues) as a cross-boundary contract protocol (DEC-060,
v0.5 Step 5).

Another protocol instance on the same ``Endpoint``/``base.join`` spine. **Orientation
(DEC-060, resolving the PRD §3.5 wording):** a *subscriber/listener* is the
**provider** (it HANDLES the channel — the code that processes messages), a
*publisher* is the **consumer** (it CALLS_ENDPOINT the channel — it sends to it). So
``ROUTES_TO`` reads **publisher → subscriber**, mirroring the data flow and the HTTP
analogy (a frontend *calls* an endpoint a backend *handles*). The join is on a shared
channel name: ``topic::<name>`` (Kafka), ``queue::<name>`` (RabbitMQ/pika).

Shapes (research §5): Kafka ``producer.send('t')`` (publisher) / ``consumer.subscribe
(['t'])`` / ``@KafkaListener(topics='t')`` (subscriber); pika ``basic_publish
(routing_key='q')`` (publisher) / ``basic_consume(queue='q')`` / ``queue_declare('q')``
(subscriber). A literal channel name → EXTRACTED; several providers on one channel →
AMBIGUOUS (the join's job).

Deferred (DEC-060): Redis ``publish``/``subscribe``, NATS, AWS SNS/SQS boto3;
constant-/config-reference channel names (INFERRED); consumer-group/partition
semantics. Pure-static (DEC-009) — AST only, never a live broker.
"""
