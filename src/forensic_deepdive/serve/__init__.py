"""`forensic serve --ui` — the Sigma.js whole-graph explorer (DEC-053, v0.4 Item K).

A local **served** UI (not a static export): a read-only stdlib-`http.server`
backend streams a **bounded, filtered** graphology graph to a vendored Sigma.js
(WebGL) client. The deterministic graph builder (:mod:`graph_api`) is a pure,
unit-testable core; :mod:`http_server` is the thin read-only HTTP shell over it.

This is a *separate surface* from the 5 markdown artifacts — it touches no
emitter, so the artifact contract and the AGENT_BRIEF ≤5kb cap are untouched.
It is a new HTTP transport *alongside* the MCP stdio transport
(``mcp_server.serve_stdio``), not a replacement.
"""

from __future__ import annotations

from forensic_deepdive.serve.graph_api import (
    ALL_EDGE_TYPES,
    DEFAULT_EDGE_TYPES,
    build_graph_payload,
    build_meta,
    build_node_detail,
)
from forensic_deepdive.serve.http_server import is_loopback_host, serve_ui

__all__ = [
    "ALL_EDGE_TYPES",
    "DEFAULT_EDGE_TYPES",
    "build_graph_payload",
    "build_meta",
    "build_node_detail",
    "is_loopback_host",
    "serve_ui",
]
