"""Publisher fixture (DEC-060) — the consumer (CALLS_ENDPOINT) side."""


def emit_order(producer, order):
    producer.send("orders", value=order)


def enqueue_task(channel, body):
    channel.basic_publish(exchange="", routing_key="tasks", body=body)
