"""gRPC as a cross-boundary contract protocol (DEC-060, v0.5 Step 5).

Back to the keystone (after the DI/ORM exception): gRPC is another protocol instance
on the **same** ``Endpoint``/``base.join`` spine — a servicer method is a *provider*
(``HANDLES``), a generated-stub call site is a *consumer* (``CALLS_ENDPOINT``), joined
through ``Endpoint(protocol='grpc', contract_id='grpc::<Svc>/<Method>')``. The
``.proto`` ``service``/``rpc`` definition is the **spec** (like OpenAPI, DEC-048): it
marks the endpoint ``spec_backed=True`` so the join is EXTRACTED, and surfaces rpcs
with no in-code servicer as honest spec-only endpoints.

Keying decision (DEC-060): key on the **bare ``<Svc>/<Method>``**, not the proto
package — the stub side recovers the service from the ``<Svc>Stub`` class name but
not the proto ``package`` (that needs stub-import→.proto dataflow). Package-qualified
``grpc::<pkg>.<Svc>/<Method>`` keying is a future INFERRED enhancement (mirrors the
MCP bare-tool decision, DEC-057).

Zero new runtime dep (DEC-061): the ``.proto`` floor is the **tree-sitter-proto
grammar already bundled in ``tree-sitter-language-pack``** — pure-static, AST-only,
never ``protoc``.
"""
