"""Idempotent registration of MCP extractors into the contract registry
(DEC-057, mirroring ``contracts/http/register.py``). Called once by
``ContractPhase`` at run time rather than via import side-effects, so import
order is never load-bearing and the registry stays a plain data structure.
Re-calling is a guarded no-op (safe across the many ContractPhase runs in a test
session)."""

from __future__ import annotations

_REGISTERED = False


def register_mcp_extractors() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from forensic_deepdive.contracts.mcp.consumers import CONSUMER_EXTRACTORS
    from forensic_deepdive.contracts.mcp.providers import PROVIDER_EXTRACTORS
    from forensic_deepdive.contracts.registry import register_consumer, register_provider

    for extractor in PROVIDER_EXTRACTORS:
        register_provider("mcp", extractor)
    for extractor in CONSUMER_EXTRACTORS:
        register_consumer("mcp", extractor)
    _REGISTERED = True
