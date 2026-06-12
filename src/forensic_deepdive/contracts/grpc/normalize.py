"""gRPC ``contract_id`` key-builder (DEC-060, v0.5 Step 5).

Both sides key on the bare ``<Service>/<Method>`` (the proto package is dropped —
see ``contracts/grpc/__init__.py``): a ``.proto`` ``rpc M`` in ``service S`` and a
``stub.M()`` call on a ``SStub`` both produce ``grpc::S/M`` → an EXTRACTED join.
"""

from __future__ import annotations


def grpc_contract_id(service: str, method: str) -> str:
    """The canonical ``grpc::<Service>/<Method>`` contract id (the registry's
    ``grpc`` key-builder)."""
    return f"grpc::{service}/{method}"
