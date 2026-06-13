"""AMQP topic-exchange publishers (DEC-067 fixture). Each names (exchange, routing_key)."""

import pika


def emit_log(channel):
    channel.basic_publish(exchange="logs", routing_key="kern.critical", body=b"x")


def emit_event(channel):
    channel.basic_publish(exchange="events", routing_key="user.created", body=b"y")


def emit_multi(channel):
    channel.basic_publish(exchange="multi", routing_key="a.b", body=b"z")
