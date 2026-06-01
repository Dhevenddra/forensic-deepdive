"""HTTP call-site consumer extractors (DEC-046, v0.4 Item G).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting consumer
(``CALLS_ENDPOINT``) records. ``CONSUMER_EXTRACTORS`` is the ordered list the HTTP
registration wires in. fetch/axios is the first instance; RTK Query / React Query
/ Angular / Python·Java clients join this list as they land.
"""

from forensic_deepdive.contracts.http.consumers.fetch_axios import extract_fetch_axios_consumers

CONSUMER_EXTRACTORS = [extract_fetch_axios_consumers]

__all__ = ["CONSUMER_EXTRACTORS", "extract_fetch_axios_consumers"]
