"""A FastMCP server fixture (DEC-057) — the MCP provider side.

Exercises: ``@mcp.tool()`` (function-name tool), ``@mcp.tool(name=...)`` (explicit
name wins), a hyphenated explicit name (separator normalization), and an orphan
tool with no consumer (HANDLES, no ROUTES_TO — the honest unmatched posture).
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")


@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b


@mcp.tool(name="get_weather")
def weather(city: str) -> str:
    return f"sunny in {city}"


@mcp.tool(name="get-info")
def info() -> str:
    # explicit hyphenated name → normalized to mcp::get_info
    return "info"


@mcp.tool()
def orphan_tool() -> str:
    # a located provider with no consumer → HANDLES, no ROUTES_TO
    return "lonely"
