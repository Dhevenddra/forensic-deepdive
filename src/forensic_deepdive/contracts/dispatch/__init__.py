"""Tool-registry dynamic dispatch as a cross-boundary protocol (DEC-058, v0.5
Step 3 — the honest-confidence hard part).

The pattern every agent framework uses: a name→handler table (``@registry.register("x")``
/ ``TOOLS = {"x": fn}`` / ``registry[name] = fn``) dispatched by key
(``registry[key]()`` / ``registry.get(key)()``). Modeled on the **same**
``Endpoint``/``base.join`` spine as HTTP/MCP (the keystone): a registration is a
*provider* (``HANDLES``), a dispatch is a *consumer* (``CALLS_ENDPOINT``), joined
through ``Endpoint(protocol='registry', contract_id='registry::<id>::<key>')``.

The honest-confidence core (DEC-025/037): a **literal-key** dispatch resolves to one
handler → **INFERRED** (the registry indirection is real — a name match, not a
direct call); a **dynamic-key** dispatch (``registry[var]()``) can hit *any*
registered handler → it keys the wildcard ``registry::<id>::*`` and fans out to
**every** handler as **AMBIGUOUS-all** (emit all, never collapse to one guess),
**capped** so a giant registry can't explode the graph.

Pure-static (DEC-009): every shape is read off the AST — never by importing or
running the dispatch.
"""
