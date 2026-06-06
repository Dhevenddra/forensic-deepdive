"""HTTP call-site consumer extractors (DEC-046, v0.4 Item G).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting consumer
(``CALLS_ENDPOINT``) records. ``CONSUMER_EXTRACTORS`` is the ordered list the HTTP
registration wires in. fetch/axios is the first instance; RTK Query / React Query
/ Angular / Python·Java clients join this list as they land.
"""

from forensic_deepdive.contracts.http.consumers.angular_http import extract_angular_http_consumers
from forensic_deepdive.contracts.http.consumers.configured_client import (
    extract_configured_client_consumers,
)
from forensic_deepdive.contracts.http.consumers.fetch_axios import extract_fetch_axios_consumers
from forensic_deepdive.contracts.http.consumers.java_clients import extract_java_client_consumers
from forensic_deepdive.contracts.http.consumers.jquery import extract_jquery_consumers
from forensic_deepdive.contracts.http.consumers.py_requests import extract_py_requests_consumers
from forensic_deepdive.contracts.http.consumers.react_query import extract_react_query_consumers
from forensic_deepdive.contracts.http.consumers.rtk_query import extract_rtk_query_consumers

CONSUMER_EXTRACTORS = [
    extract_fetch_axios_consumers,
    extract_configured_client_consumers,
    extract_rtk_query_consumers,
    extract_react_query_consumers,
    extract_angular_http_consumers,
    extract_jquery_consumers,
    extract_py_requests_consumers,
    extract_java_client_consumers,
]

__all__ = [
    "CONSUMER_EXTRACTORS",
    "extract_angular_http_consumers",
    "extract_configured_client_consumers",
    "extract_fetch_axios_consumers",
    "extract_java_client_consumers",
    "extract_jquery_consumers",
    "extract_py_requests_consumers",
    "extract_react_query_consumers",
    "extract_rtk_query_consumers",
]
