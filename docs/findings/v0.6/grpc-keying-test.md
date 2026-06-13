# gRPC package/directory-qualified keying — v0.6 Step 5 acceptance (DEC-068)

v0.5 keyed gRPC on the **bare** `grpc::<Service>/<Method>` (proto package dropped). In a
monorepo this collides catastrophically: `grpc-examples` ships ~14–18 independent examples
that each define `service Greeter { rpc SayHello }`, so every `Greeter/SayHello` servicer
and stub across the whole tree shared one key → a **cartesian fan-out of ~975 AMBIGUOUS**
joins. Step 5 recovers the generated `*_pb2_grpc` **module identity** from Python AST and
qualifies the key — over the **unchanged** `base.join`.

## The keystone held

`grpc::<module>::<Service>/<Method>` is "a more-specific key on the same exact-match join."
`git diff` (non-test src) = `contracts/grpc/{normalize,providers/servicers,consumers/stubs,
proto_scan}.py` only. `base.join`/`registry`/`trace`/emit/`serve` untouched (the key-builder
signature changed `(service, method)` → `(module, service, method)`, but the registry only
stores the reference; `join` keys on the produced `contract_id`).

## How the module identity is recovered (pure AST, no `.proto` parse)

- **Servicer:** the base class `<module-ref>.<Svc>Servicer`.
- **Stub:** `<var> = <module-ref>.<Svc>Stub(channel)`, tied to `<var>.<Method>()`.
- **Proto spec:** the `.proto` filename → `<stem>_pb2_grpc`.
- `<module-ref>` resolves through a per-file **import-alias table** (`import X`, `import X as
  Y`, `from . import X`, `from pkg import X`, `from X import Servicer`).
- **Directory-qualified** for flat/relative (sibling) imports — two example dirs that both
  `import helloworld_pb2_grpc` name *different* generated modules (`<dir>/helloworld_pb2_grpc`,
  each dir its own `sys.path` root); **dotted-package-qualified** for shared
  `from pkg.gen import foo_pb2_grpc`. **No `.proto` parse for the module, no `[proto]` dep.**

**CAVEAT:** the module-identity key is the Python generated-code identity, *not* the gRPC
wire path `/<package>.<Service>/<Method>`. That equivalence is INFERRED and deferred.

## Real-repo acceptance — `grpc-examples/examples/python`

`C:\Dev\scratch\grpc-examples` (Apache-2.0).

| | v0.5 (bare keys) | v0.6 basename-only (intermediate) | **v0.6 dir-qualified** |
|---|---|---|---|
| grpc `ROUTES_TO` AMBIGUOUS | ~975 (cartesian) | 936 | **68** |
| grpc `ROUTES_TO` EXTRACTED | 9 | 9 | **26** |

The **68 remaining AMBIGUOUS are genuine** same-directory multiple implementations, exactly
the honest outcome the PRD requires:
- `route_guide/route_guide_pb2_grpc::RouteGuide/*` — **two** servers (`route_guide_server.py`
  sync + `asyncio_route_guide_server.py` async).
- `helloworld/helloworld_pb2_grpc::Greeter/SayHello` — **five** server variants
  (sync/async × reflection/graceful-shutdown).
- `auth/…`, `debug/…`, `observability/…`, `uds/…`, `wait_for_ready/…` — multiple genuine
  servers per dir.

These are real dual/multi-implementations (the analyzer cannot and must not pick one →
AMBIGUOUS-all). Every **cross-directory** false join is gone — modules are now distinct,
e.g. `grpc::data_transmission/demo_pb2_grpc::GRPCDemo/SimpleMethod` cleanly EXTRACTED.

## Why basename alone wasn't enough (the directory-qualification insight)

Basename-only keying left 936 AMBIGUOUS — the 18 duplicated helloworld examples all share
the basename `helloworld_pb2_grpc`. A flat `import helloworld_pb2_grpc` is a **sibling**
import, so the module's identity is inseparable from the importing file's directory.
Directory-qualifying flat/relative imports (`<dir>/helloworld_pb2_grpc`) dropped 936 → 68.

## Tests

`tests/test_grpc.py` — a new `grpc_module_alias_table`/`grpc_resolve_module` unit test
across all import forms (flat, aliased, relative submodule, dotted package, symbol import);
existing keys updated bare → module-qualified; the spec-backed servicer↔stub join + the
spec-only endpoint still hold. 6 grpc tests green, goldens byte-identical.

## Takeaway

gRPC's 975-way cartesian collapses to 26 clean EXTRACTED joins + 68 genuine
multiple-implementation AMBIGUOUS, by recovering the generated module identity (directory/
package-qualified) from Python AST alone — no `.proto` parse, no new dependency, and
`base.join` untouched.
