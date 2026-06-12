"""Idempotent registration of messaging extractors (DEC-060, mirroring
``contracts/http/register.py``). Registered under the ``topic`` protocol entry; the
extractors emit ``topic::``/``queue::`` contracts (the Endpoint.protocol comes from
each Contract, so one entry hosts both kinds). Called once by ``ContractPhase``."""

from __future__ import annotations

_REGISTERED = False


def register_messaging_extractors() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from forensic_deepdive.contracts.messaging.consumers import CONSUMER_EXTRACTORS
    from forensic_deepdive.contracts.messaging.providers import PROVIDER_EXTRACTORS
    from forensic_deepdive.contracts.registry import register_consumer, register_provider

    for extractor in PROVIDER_EXTRACTORS:
        register_provider("topic", extractor)
    for extractor in CONSUMER_EXTRACTORS:
        register_consumer("topic", extractor)
    _REGISTERED = True
