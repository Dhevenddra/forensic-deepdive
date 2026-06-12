"""Idempotent registration of gRPC extractors (DEC-060, mirroring
``contracts/http/register.py``). Called once by ``ContractPhase`` at run time."""

from __future__ import annotations

_REGISTERED = False


def register_grpc_extractors() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from forensic_deepdive.contracts.grpc.consumers import CONSUMER_EXTRACTORS
    from forensic_deepdive.contracts.grpc.providers import PROVIDER_EXTRACTORS
    from forensic_deepdive.contracts.registry import register_consumer, register_provider

    for extractor in PROVIDER_EXTRACTORS:
        register_provider("grpc", extractor)
    for extractor in CONSUMER_EXTRACTORS:
        register_consumer("grpc", extractor)
    _REGISTERED = True
