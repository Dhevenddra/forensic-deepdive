"""MCP tool-provider extractor (DEC-057, v0.5 Step 2 — the headline provider).

A FastMCP ``@mcp.tool()`` (or ``@server.tool(name="x")``) decorated function is a
*provider* of an MCP tool — the ``HANDLES`` side of an ``Endpoint(protocol='mcp')``::

    mcp = FastMCP("Demo")            # server identity (an Endpoint property)

    @mcp.tool()                      # tool name = function name (SDK default)
    def add(a: int, b: int): ...

    @mcp.tool(name="get_weather")    # explicit name wins over the function name
    def weather(city: str): ...

**The tool name is a syntactic fact** — the ``name=`` kwarg when present
(authoritative), else the function name (the SDK uses it verbatim) — so both forms
are **EXTRACTED**-grade. Handler ``symbol_id`` via ``_parent_chain`` (the load-
bearing anti-drift rule), or the edge is filtered against ``valid_symbol_qns``.

**Shape guard (no one-repo hacks):** a ``@<recv>.tool`` decorator counts only when
``<recv>`` is a FastMCP/``Server`` instance constructed *in this file* (``<var> =
FastMCP(...)``); when the server is constructed elsewhere and only the decorator is
local, we fall back to the conventional receiver names ``mcp``/``server`` (the file
already passed the FastMCP/``@mcp.tool`` marker pre-filter). ``FastMCP("name")`` is
read for server identity (an ``Endpoint`` display property via ``raw_path``), never
part of the key (bare-tool keying — DEC-057).

Deferred (PRD §3.2): the low-level ``Server(...)`` + ``@server.call_tool()`` dispatch
table (tool names are string literals inside the handler body → Step 3's detector);
MCP *resources*/*prompts* (tools only in v0.5); ``version=`` as anything beyond a
property (never part of the key).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.scan import (
    first_positional_string,
    iter_candidate_files,
    keyword_arg_value,
    rightmost_name,
)
from forensic_deepdive.contracts.mcp.normalize import mcp_contract_id, normalize_tool_name
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.static.tags import _parent_chain

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"FastMCP", b"@mcp.tool", b".tool(", b"Server(")
_LANGS = ("python",)
# Constructors whose instances expose ``.tool`` decorators (server identity).
_SERVER_CTORS = frozenset({"FastMCP", "Server"})
# Fallback receiver names when the server is constructed in another module.
_CONVENTIONAL_RECEIVERS = frozenset({"mcp", "server"})


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _walk(node: Node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _collect_server_vars(root: Node, src: bytes) -> dict[str, str]:
    """Map each ``<var> = FastMCP("name")`` / ``Server("name")`` local to its
    server name (``""`` when the name isn't a literal). Used both as the decorator
    shape guard and to attribute server identity to the Endpoint."""
    server_vars: dict[str, str] = {}
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None or left.type != "identifier" or right.type != "call":
            continue
        fn = right.child_by_field_name("function")
        if fn is None or rightmost_name(fn, src) not in _SERVER_CTORS:
            continue
        args = right.child_by_field_name("arguments")
        name = (first_positional_string(args, src) if args is not None else None) or ""
        server_vars[_text(left, src)] = name
    return server_vars


def _tool_decorator(decorator: Node, src: bytes) -> tuple[str, str | None] | None:
    """``(receiver, explicit_name)`` for a ``@<recv>.tool`` / ``@<recv>.tool(...)``
    decorator, or ``None`` when this decorator isn't a ``.tool`` one. ``explicit_name``
    is the ``name=`` kwarg literal when present, else ``None`` (use the fn name)."""
    expr = next(
        (c for c in decorator.children if c.type in ("call", "attribute", "identifier")), None
    )
    if expr is None:
        return None
    if expr.type == "attribute":  # bare @recv.tool
        attr = expr.child_by_field_name("attribute")
        obj = expr.child_by_field_name("object")
        if attr is None or obj is None or _text(attr, src) != "tool":
            return None
        receiver = rightmost_name(obj, src)
        return (receiver, None) if receiver is not None else None
    if expr.type == "call":  # @recv.tool(...) / @recv.tool(name="x")
        fn = expr.child_by_field_name("function")
        if fn is None or fn.type != "attribute":
            return None
        attr = fn.child_by_field_name("attribute")
        obj = fn.child_by_field_name("object")
        if attr is None or obj is None or _text(attr, src) != "tool":
            return None
        receiver = rightmost_name(obj, src)
        if receiver is None:
            return None
        args = expr.child_by_field_name("arguments")
        explicit = keyword_arg_value(args, "name", src) if args is not None else None
        return receiver, explicit
    return None


def _handler_symbol_id(definition: Node, src: bytes, rel_path: str) -> str | None:
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        return None
    parent = _parent_chain(name_node, "python")
    handler = _text(name_node, src)
    qn_local = f"{parent}.{handler}" if parent else handler
    return f"{rel_path}::{qn_local}"


def extract_mcp_tool_providers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        server_vars = _collect_server_vars(root, src)
        for node in _walk(root):
            if node.type != "decorated_definition":
                continue
            definition = node.child_by_field_name("definition")
            if definition is None or definition.type != "function_definition":
                continue
            for decorator in node.children:
                if decorator.type != "decorator":
                    continue
                parsed = _tool_decorator(decorator, src)
                if parsed is None:
                    continue
                receiver, explicit = parsed
                # Shape guard: a known FastMCP/Server var, else the conventional
                # receiver names (server constructed in another module).
                if server_vars:
                    if receiver not in server_vars:
                        continue
                elif receiver not in _CONVENTIONAL_RECEIVERS:
                    continue
                name_node = definition.child_by_field_name("name")
                if name_node is None:
                    continue
                tool_name = explicit if explicit is not None else _text(name_node, src)
                if not normalize_tool_name(tool_name):
                    continue
                symbol_id = _handler_symbol_id(definition, src, rel_path)
                if symbol_id is None:
                    continue
                contract_id = mcp_contract_id(tool_name)
                key = (contract_id, symbol_id)
                if key in seen:
                    continue
                seen.add(key)
                server = server_vars.get(receiver, "")
                normalized = normalize_tool_name(tool_name)
                contracts.append(
                    Contract(
                        role=ContractRole.PROVIDER,
                        contract_id=contract_id,
                        symbol_id=symbol_id,
                        confidence=Confidence.EXTRACTED,
                        evidence=f"@{receiver}.tool name={tool_name!r}",
                        protocol="mcp",
                        method="",
                        normalized_path=normalized,
                        raw_path=f"{server}/{normalized}" if server else normalized,
                        framework="fastmcp",
                        rel_path=rel_path,
                        line=name_node.start_point[0],
                    )
                )
    return contracts
