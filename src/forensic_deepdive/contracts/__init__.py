"""Cross-boundary contracts (DEC-043, v0.4 wedge).

The ``CrossBoundaryEdge`` abstraction: a contract is
``(role, contract_id, symbol_id, confidence, ...)``; :func:`base.join` groups by
``contract_id``. HTTP is the first instance (Items E–I); gRPC/topics reuse it in
v0.5 as new key-builders.
"""

from forensic_deepdive.contracts.base import (
    Contract,
    ContractRole,
    CrossLink,
    join,
)
from forensic_deepdive.contracts.registry import (
    REGISTRY,
    ContractContext,
    ProtocolEntry,
    register_consumer,
    register_provider,
)

__all__ = [
    "REGISTRY",
    "Contract",
    "ContractContext",
    "ContractRole",
    "CrossLink",
    "ProtocolEntry",
    "join",
    "register_consumer",
    "register_provider",
]
