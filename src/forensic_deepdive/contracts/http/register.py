"""Idempotent registration of HTTP extractors into the contract registry
(DEC-045). Called once by ``ContractPhase`` at run time rather than via import
side-effects, so import order is never load-bearing and the registry stays a
plain data structure. Re-calling is a guarded no-op (safe across the many
ContractPhase runs in a test session)."""

from __future__ import annotations

_REGISTERED = False


def register_http_extractors() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from forensic_deepdive.contracts.http.consumers import CONSUMER_EXTRACTORS
    from forensic_deepdive.contracts.http.providers import PROVIDER_EXTRACTORS
    from forensic_deepdive.contracts.registry import register_consumer, register_provider

    for extractor in PROVIDER_EXTRACTORS:
        register_provider("http", extractor)
    for extractor in CONSUMER_EXTRACTORS:
        register_consumer("http", extractor)
    _REGISTERED = True
