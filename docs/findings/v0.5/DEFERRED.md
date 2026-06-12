# v0.5 → next-arc carryover — deferred enhancements & findings

Everything v0.5 consciously did **not** build, the source (a DEC's "Deferred" clause
or a real-repo finding), and where it was assigned. This is the seed list for the
v0.6 plan. Nothing here is a bug — each is a scoped, documented deferral or a
finding-driven refinement.

Legend: **[finding]** = surfaced by a real-repo acceptance run (strongest signal);
**[DEC-NNN]** = documented deferral in that decision; **[assigned]** = already routed
to a specific later version in DEC-055.

---

## A. Findings-driven refinements (from the real-repo runs — top v0.6 candidates)

These earned their priority by appearing on real upstream code, not speculation.

1. **gRPC package-qualified keying** — **[finding: grpc-examples]**
   Bare `grpc::<Svc>/<Method>` keying **collides** when a monorepo reuses a service
   name (the gRPC examples repo has ~18 `Greeter`/`SayHello` copies → **975 AMBIGUOUS**
   cartesian joins). The generated module name (`helloworld_pb2_grpc` vs
   `route_guide_pb2_grpc`) **is** statically recoverable on both servicer and stub
   sides and would disambiguate. **Caveat:** the `.proto`'s own `package` declaration
   (`package routeguide;`) ≠ the generated module name (`route_guide_pb2_grpc`), so a
   correct fix must map proto-file → generated module (a real change, not one line).
   Also note: bare keying is *correct* when there genuinely are multiple impls (the
   route_guide sync+async dual-servicer case → AMBIGUOUS is right). [DEC-057/060 also
   flagged server-/package-qualified keying as a future INFERRED enhancement.]

2. **ORM `Model`-base disambiguation** — **[finding: Superset]**
   1 of 55 Superset tables (`coremodel`) was mis-tagged `orm='django'` instead of
   `sqlalchemy` — a class with a `Model` base that isn't a Django model fell into the
   Django branch. The `DbTable` + `PERSISTS_TO` edge are still **correct**; only the
   `orm` property is wrong (~2 %). Fix: require a Django-specific signal (a
   `django.db.models` import, a nested `Meta`, or app context) before the Django branch.

3. **RabbitMQ topic-exchange + binding-key topology** — **[finding: rabbitmq-tutorials]**
   Direct named queues join cleanly (`queue::`), but **topic exchanges = 0**: the
   tutorials publish with a `routing_key` to a topic *exchange* and bind a generated
   queue with a pattern (`queue_bind(routing_key='kern.*')`) — the binding key ≠ a
   `basic_consume(queue=literal)`, so the two sides share no key. Modeling
   exchange + binding-key topology (and the `*`/`#` wildcard match) is the gap.
   [DEC-060 deferred Redis/NATS/SNS-SQS + non-literal channel names alongside this.]

4. **JAX-RS sub-resource locators** — **[finding: jersey bookstore]**
   `examples/helloworld` (plain `@GET`) extracts cleanly; `examples/bookstore-webapp`
   yielded **0** because it is built on **sub-resource locators** — `@Path` methods
   that *return* a resource object instead of carrying a verb annotation. v0.5 requires
   a verb (`@GET`/…) on the method. [DEC-062 deferral, now confirmed on real code.]

5. **Extraction performance** — **[finding: Superset/hermes]**
   Full graph build is ~20 min on an 18.7k-symbol repo and ~40 min on hermes — the
   registry-dispatch fan-out + cross-stack join + DI/ORM passes over a large polyglot
   tree. The cap bounds graph *size*, not scan *time*. A perf/profiling pass is a
   standing candidate (incremental update, §C, would also help).

---

## B. Per-DEC deferrals (documented in the build, not yet implemented)

**MCP (DEC-057):**
- Server-qualified keying `mcp::<server>::<tool>` (needs `session`→server dataflow;
  a future INFERRED enhancement — v0.5 ships bare-tool keying).
- MCP **resources** and **prompts** (v0.5 models tools only).
- SEP-1575 tool `version` as anything beyond an `Endpoint` property.

**Registry dispatch (DEC-058):**
- `getattr(obj, name)()` attribute dispatch (no registration-table counterpart).
- Cross-module registry population beyond the bare-variable-name union (best-effort;
  note incompleteness).
- JS/TS registry dispatch (v0.5 is Python-only — hermes is Python).
- Registrations whose *value* is a non-identifier (lambda / `obj.method`) — skipped.

**DI/ORM tail (DEC-059):**
- The **`PROVIDES`** edge (deferred as redundant with IMPLEMENTS / the resolved
  INJECTS — re-evaluate if a use case needs the inverse).
- DI frameworks: **NestJS** `@Injectable`, **Angular**, **Guice**, **Dagger**.
- ORM: **TypeORM**, **Prisma**; SQLAlchemy **imperative `Table()`** mapping.
- `@Qualifier` / `@Primary` disambiguation (multi-impl currently stays AMBIGUOUS-all).
- `@Configuration` / `@Bean` factory providers (beyond annotation/ctor injection).
- **`RELATES_TO`** table-to-table FK/relationship edges (the `DbTable` node is the seam).

**gRPC + messaging (DEC-060):**
- **Go / Java** gRPC servicers + stubs (v0.5 is Python-only).
- Redis `publish`/`subscribe`, NATS, AWS SNS/SQS (boto3) messaging.
- Constant-/config-reference channel names (→ INFERRED).
- Consumer-group / partition semantics.

**`.proto` parsing (DEC-061):**
- The opt-in `[proto]` extra (`proto-schema-parser` + `antlr4-python3-runtime`) — only
  if the zero-dep tree-sitter-proto floor is ever shown to miss real RPCs. Default
  stays zero-dep.

**Framework breadth (DEC-062):**
- **Django** route provider — the decoupled `urls.py` → view routing table needs
  cross-file view-reference resolution (a spec-table shape, unlike decorator-on-handler);
  its own focused follow-on.
- NestJS `RouterModule.register([{path, module}])` module-prefix nesting.
- JAX-RS `@ApplicationPath` app-prefix + (the sub-resource locators of §A.4).

---

## C. Assigned elsewhere in DEC-055 (not v0.6-discretionary)

- **Incremental / persistent graph update** → **v1.0** (DEC-051's line-free `node_id`
  is the deliberate no-migration seam; pulling it forward wastes that sequencing).
- **Temporal / Graphiti** layer → **opt-in-later** (gated behind DEC-005's 2-of-5
  threshold; carries LLM cost — breaches the pure-static floor's centrality).
- **Agent-facing memory hardening** (portable git-ref insight storage + a JSONL→SQLite
  recall index) → **optional**, additive, never a headline (was the tentative-but-unbuilt
  DEC-062 slot in the original PRD §5; the real DEC-062 became framework breadth).
- **True multi-repo federation** (one `Endpoint` shared across repo boundaries) →
  **its own later arc** — needs a repo registry, cross-repo `node_id` namespacing, and
  a manifest escape-hatch. The unmatched `CALLS_ENDPOINT` (e.g. hermes calling external
  MCP servers' tools) is the honest seam.
- **IDE integration** → **post-v1.0 endgame**. v0.5 laid the seams (protocol generality
  proven across 5 instances; the DI/ORM `Table` data-layer reach; agent-dispatch
  modeling) but builds nothing on them yet.

---

## D. Honest non-goals re-affirmed (DEC-055 §8 invariants — do not "fix" these)

- **AMBIGUOUS is not a bug.** Multiple registry handlers, multiple impls, multiple gRPC
  servicers, repeated service names → emit **all** candidates, never guess one
  (DEC-025/037). The 975 gRPC AMBIGUOUS and the dispatch fan-outs are *honest*.
- **Dropped > guessed.** A dynamic `call_tool(var)` / non-literal channel is dropped,
  not fabricated.
- **0 ROUTES_TO can be correct.** hermes' MCP `ROUTES_TO=0` is right — it serves tools
  and calls *external-server* tools (the federation seam), not its own.
