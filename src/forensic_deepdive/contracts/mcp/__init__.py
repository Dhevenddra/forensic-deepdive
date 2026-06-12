"""MCP (Model Context Protocol) as a cross-boundary contract protocol (DEC-057,
v0.5 Step 2 — the headline).

The keystone (DEC-055/PRD §1): MCP reuses the **same** ``Endpoint``/``base.join``
machinery HTTP uses — an ``@mcp.tool()`` handler is a *provider* (``HANDLES``), a
``ClientSession.call_tool("name")`` is a *consumer* (``CALLS_ENDPOINT``), joined
through an ``Endpoint(protocol='mcp', contract_id='mcp::<tool>')`` so ``trace``,
the HOTPATHS ``## Cross-stack routes`` section, and ``serve --ui`` light up the
``mcp`` edges **with zero surfacing-layer change**. The only per-protocol code is
this subpackage's key-builder + provider/consumer extractors.

Pure-static (DEC-009): ``mcp`` / ``fastmcp`` are *detection targets*, never
imports — every shape is read off the AST, never by running the agent or hitting
a live MCP server.
"""
