"""Subscriber fixture (DEC-060) — the provider (HANDLES) side."""


def consume_orders(consumer):
    consumer.subscribe(["orders"])
    for msg in consumer:
        handle(msg)


def consume_tasks(channel):
    channel.basic_consume(queue="tasks", on_message_callback=work)
