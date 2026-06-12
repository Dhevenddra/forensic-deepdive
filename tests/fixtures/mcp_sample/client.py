"""An MCP ClientSession fixture (DEC-057) — the MCP consumer side.

Exercises: a positional literal name, the ``name=`` kwarg form (joining the
hyphen-normalized provider ``get-info`` → ``mcp::get_info``), and a dynamic
variable name (dropped — never guessed, DEC-037).
"""

from mcp import ClientSession


async def run_agent(session: ClientSession, city: str, tool_var: str):
    total = await session.call_tool("add", arguments={"a": 1, "b": 2})
    forecast = await session.call_tool("get_weather", arguments={"city": city})
    details = await session.call_tool(name="get_info", arguments={})
    # dynamic name → no stable key → dropped (never guessed)
    dynamic = await session.call_tool(tool_var, arguments={})
    return total, forecast, details, dynamic
