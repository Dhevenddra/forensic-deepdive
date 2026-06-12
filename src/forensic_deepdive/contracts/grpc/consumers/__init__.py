"""gRPC consumer extractors (DEC-060, v0.5 Step 5).

One consumer: the Python generated-stub call site (``stub.Method(req)``).
``CONSUMER_EXTRACTORS`` is the ordered list the gRPC registration wires in.
"""

from forensic_deepdive.contracts.grpc.consumers.stubs import extract_stub_consumers

CONSUMER_EXTRACTORS = [
    extract_stub_consumers,
]

__all__ = [
    "CONSUMER_EXTRACTORS",
    "extract_stub_consumers",
]
