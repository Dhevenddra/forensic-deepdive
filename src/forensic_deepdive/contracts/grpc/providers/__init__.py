"""gRPC provider extractors (DEC-060, v0.5 Step 5).

Two providers: the ``.proto`` spec scan (spec-backed, synthetic symbol) and the
Python servicer-method extractor (the real ``HANDLES`` symbol). ``PROVIDER_EXTRACTORS``
is the ordered list the gRPC registration wires in.
"""

from forensic_deepdive.contracts.grpc.proto_scan import extract_proto_providers
from forensic_deepdive.contracts.grpc.providers.servicers import extract_servicer_providers

PROVIDER_EXTRACTORS = [
    extract_proto_providers,
    extract_servicer_providers,
]

__all__ = [
    "PROVIDER_EXTRACTORS",
    "extract_proto_providers",
    "extract_servicer_providers",
]
