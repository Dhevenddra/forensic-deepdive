"""Registry-dispatch consumer extractors (DEC-058, v0.5 Step 3).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting consumer
(``CALLS_ENDPOINT``) records for dispatch sites (``registry[key]()`` /
``registry.get(key)()``). ``CONSUMER_EXTRACTORS`` is the ordered list the dispatch
registration wires in (``contracts.dispatch.register``).
"""

from forensic_deepdive.contracts.dispatch.consumers.dispatch_sites import (
    extract_registry_consumers,
)

CONSUMER_EXTRACTORS = [
    extract_registry_consumers,
]

__all__ = [
    "CONSUMER_EXTRACTORS",
    "extract_registry_consumers",
]
