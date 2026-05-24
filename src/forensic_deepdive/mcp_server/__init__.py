"""MCP server (DEC-016) — exposes the LadybugDB graph to AI agents.

Five composite tools (per PRD §4.5 / DEC-016): ``impact``, ``context``,
``archaeology``, ``flow``, ``query``. Each is intentionally rich rather
than endpoint-mirror so agents can do useful work in one tool call.

Public surface::

    from forensic_deepdive.mcp_server import make_server, serve_stdio

    server = make_server(graph_db_path)
    # ... register / inspect / call tools directly, or:
    await serve_stdio(graph_db_path)  # launches stdio transport
"""

from forensic_deepdive.mcp_server.server import (
    archaeology,
    flow,
    impact,
    make_server,
    serve_stdio,
)
from forensic_deepdive.mcp_server.server import (
    context as context_tool,
)
from forensic_deepdive.mcp_server.server import (
    query as query_tool,
)

__all__ = [
    "archaeology",
    "context_tool",
    "flow",
    "impact",
    "make_server",
    "query_tool",
    "serve_stdio",
]
