"""MCP tool-provider extractors (DEC-057, v0.5 Step 2).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting provider
(``HANDLES``) records for ``@mcp.tool()`` / ``@server.tool(name=)`` handlers.
``PROVIDER_EXTRACTORS`` is the ordered list the MCP registration wires in
(``contracts.mcp.register``).
"""

from forensic_deepdive.contracts.mcp.providers.mcp_tools import extract_mcp_tool_providers

PROVIDER_EXTRACTORS = [
    extract_mcp_tool_providers,
]

__all__ = [
    "PROVIDER_EXTRACTORS",
    "extract_mcp_tool_providers",
]
