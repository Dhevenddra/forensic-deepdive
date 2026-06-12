"""MCP tool-consumer extractors (DEC-057, v0.5 Step 2).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting consumer
(``CALLS_ENDPOINT``) records for ``ClientSession.call_tool("name")`` call sites.
``CONSUMER_EXTRACTORS`` is the ordered list the MCP registration wires in
(``contracts.mcp.register``).
"""

from forensic_deepdive.contracts.mcp.consumers.client_session import (
    extract_client_session_consumers,
)

CONSUMER_EXTRACTORS = [
    extract_client_session_consumers,
]

__all__ = [
    "CONSUMER_EXTRACTORS",
    "extract_client_session_consumers",
]
