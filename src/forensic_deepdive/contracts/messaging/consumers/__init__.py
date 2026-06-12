"""Messaging consumer (publisher) extractors (DEC-060, v0.5 Step 5).

A *publisher* is the CALLS_ENDPOINT side (it sends to a channel). ``CONSUMER_EXTRACTORS``
is the ordered list the messaging registration wires in.
"""

from forensic_deepdive.contracts.messaging.consumers.publishers import extract_publisher_consumers

CONSUMER_EXTRACTORS = [
    extract_publisher_consumers,
]

__all__ = [
    "CONSUMER_EXTRACTORS",
    "extract_publisher_consumers",
]
