"""Idempotent registration of registry-dispatch extractors into the contract
registry (DEC-058, mirroring ``contracts/http/register.py``). Called once by
``ContractPhase`` at run time rather than via import side-effects. Re-calling is a
guarded no-op."""

from __future__ import annotations

_REGISTERED = False


def register_dispatch_extractors() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from forensic_deepdive.contracts.dispatch.consumers import CONSUMER_EXTRACTORS
    from forensic_deepdive.contracts.dispatch.providers import PROVIDER_EXTRACTORS
    from forensic_deepdive.contracts.registry import register_consumer, register_provider

    for extractor in PROVIDER_EXTRACTORS:
        register_provider("registry", extractor)
    for extractor in CONSUMER_EXTRACTORS:
        register_consumer("registry", extractor)
    _REGISTERED = True
