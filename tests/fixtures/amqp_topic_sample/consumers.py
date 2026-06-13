"""AMQP topic-exchange subscribers (DEC-067 fixture). Each binds a queue to an exchange
with a binding pattern (routing_key). reconcile_amqp matches these against the publishers'
routing keys: exact → EXTRACTED, wildcard → INFERRED, non-match → DROP, multi → AMBIGUOUS."""

import pika


def bind_kern(channel, q):  # wildcard match of kern.critical → INFERRED
    channel.queue_bind(exchange="logs", queue=q, routing_key="kern.*")


def bind_auth(channel, q):  # non-match of kern.critical → DROP
    channel.queue_bind(exchange="logs", queue=q, routing_key="auth.*")


def bind_event(channel, q):  # exact match of user.created → EXTRACTED
    channel.queue_bind(exchange="events", queue=q, routing_key="user.created")


def bind_multi_star(channel, q):  # both bind_multi_* match a.b → AMBIGUOUS fan-out
    channel.queue_bind(exchange="multi", queue=q, routing_key="a.*")


def bind_multi_exact(channel, q):
    channel.queue_bind(exchange="multi", queue=q, routing_key="a.b")
