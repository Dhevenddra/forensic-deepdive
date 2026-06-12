"""Registry-dispatch ``contract_id`` key-builder (DEC-058, v0.5 Step 3).

The dispatch analog of ``http_contract_id``/``mcp_contract_id``. Two keys per
registry:

- **exact** — ``registry::<id>::<key>`` — a *literal-key* dispatch (``TOOLS["add"]()``)
  resolves to the single handler registered under that key.
- **wildcard** — ``registry::<id>::*`` — a *dynamic-key* dispatch (``TOOLS[var]()``)
  keys this; every registration ALSO emits a wildcard provider under it, so the
  unchanged ``base.join`` fans the dynamic consumer out to all handlers
  (AMBIGUOUS-all) — the same provider-side wildcard mechanism HTTP uses for a
  method-agnostic ``http::*::<path>`` route (DEC-047), here inverted to the
  consumer-dynamic case.

``<id>`` is the registry variable name (e.g. ``TOOLS``, ``registry``). Registry
keys are exact dict keys — kept verbatim (no separator normalization, unlike MCP):
both sides must match the literal the code wrote.
"""

from __future__ import annotations

# The wildcard key segment a dynamic-key dispatch matches (every registration also
# registers under it). Distinct from any real tool name (``*`` isn't a valid id).
WILDCARD = "*"


def registry_contract_id(registry_id: str, key: str) -> str:
    """The canonical ``registry::<id>::<key>`` contract id (the registry
    key-builder). Pass :data:`WILDCARD` as *key* for the dynamic-dispatch key."""
    return f"registry::{registry_id}::{key}"


def registry_wildcard_id(registry_id: str) -> str:
    """The ``registry::<id>::*`` key a dynamic-key dispatch joins (and every
    registration's wildcard provider is keyed on)."""
    return registry_contract_id(registry_id, WILDCARD)
