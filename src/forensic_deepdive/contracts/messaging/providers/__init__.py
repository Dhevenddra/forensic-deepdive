"""Messaging provider (subscriber) extractors (DEC-060, v0.5 Step 5).

A *subscriber/listener* is the HANDLES side (it processes a channel's messages).
``PROVIDER_EXTRACTORS`` is the ordered list the messaging registration wires in.
"""

from forensic_deepdive.contracts.messaging.providers.subscribers import extract_subscriber_providers

PROVIDER_EXTRACTORS = [
    extract_subscriber_providers,
]

__all__ = [
    "PROVIDER_EXTRACTORS",
    "extract_subscriber_providers",
]
