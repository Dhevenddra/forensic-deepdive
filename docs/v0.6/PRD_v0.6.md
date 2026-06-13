# PRD_v0.6.md — "Findings-Driven Refinements" (the contract)

> The contract `KICKOFF_v0.6.md` points at. Cites `research_v0.6.md` as *research §1–§9*. Binds with
> `CLAUDE.md`. v0.5 shipped at **9/9 gate** (DEC-001→062; v0.5.0 tagged & released locally, 710 tests).
> `DECISIONS.md` ends at **DEC-062**; v0.6 starts at **DEC-063**.

---

## §0 — TL;DR
v0.5 proved the `CrossBoundaryEdge`/`Endpoint` abstraction generalizes across **five protocols** (HTTP,
MCP, registry-dispatch, gRPC, messaging) on one spine. v0.6 does **not** add a sixth protocol or expand
the public surface. It **hardens the five-protocol abstraction against the real-repo failure modes the
v0.5 acceptance runs surfaced** — five findings-driven refinements + the first lane-(iii) memory
hardening + a profiling pass — then turns the project toward a **Terminal-complete v1.0** trajectory.
Every refinement is a `KeyBuilder` / provider / consumer / resolver change over the **unchanged**
`base.join`/`Endpoint`/`trace`/emit/`serve` machinery. Zero new base-env runtime deps. GUI/IDE is
**explicitly out of scope** and waits for its own research arc once the foundations are strong.

## §1 — The keystone (unchanged, non-negotiable)
**Reuse the `Endpoint` node for every protocol. Do NOT invent `Tool`/`Service`/`Channel` nodes.**
`Endpoint` carries `protocol`; `ROUTES_TO` carries `via` + `confidence`. `trace()`, the HOTPATHS
`## Cross-stack routes` section, and `serve --ui` query `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO`
**generically, with no `protocol==` filter**. The one DEC'd new-node exception remains the DI/ORM
`DbTable` node (DEC-059) — v0.6 adds **no further node types**.

**What v0.6 is allowed to touch, and what it is not.** Each refinement is confined to:
`contracts/<proto>/normalize.py` (the KeyBuilder), `contracts/<proto>/providers|consumers/*` (extractors),
`contracts/http/providers/*` (the framework adds), `static/persistence.py` (the ORM signal), the shared
`_resolve_name_to_files` resolver in `BuildGraphPhase` (the DEC-059 cross-file ladder), and a contract-
layer reconcile helper (`base.reconcile_*`, the DEC-060 precedent). It must **NOT** touch
`mcp_server/server.py` (`trace`), `emit/hotpaths_md.py`, or `serve/graph_api.py`. **If a refinement makes
you reach into `trace`/emit/`serve`, stop — you broke the keystone; generalize instead.** (The lane-(iii)
memory step is the one place that legitimately extends an *existing* MCP tool's backend — §3.6.)

## §2 — Scope verdict (the spine — recorded as DEC-063, write first)
**(A) The spine = "harden the five-protocol abstraction against real-repo findings."** v0.6 fixes the
four findings the v0.5 acceptance runs surfaced (research §1–§4) + ships the deferred Django provider
(research §5), each a pure extractor/resolver change on the unchanged spine. No sixth protocol, no new
public surface, no architectural front opened. **(B) Memory: begin lane-(iii) hardening only** — a
local-first, zero-LLM FTS5 insight recall index reusing the DEC-041 sidecar + git shadow-ref portability
(research §6A). Lanes (i) incremental→v1.0 and (ii) temporal/Graphiti→opt-in-later are unchanged; adopt
**no** general-memory tool as a base path (all require runtime LLM/embeddings — research §6B). **(C)
Positioning:** forensic-deepdive is the **code-domain-specialized peer** to general-memory tools; Graphiti
stays the single opt-in temporal backend. **(D) Trajectory:** the v0.6→v1.0 fundamentals compound toward
a **Terminal-complete v1.0** (CLI + 9 MCP tools + 5 artifacts as the full contract; incremental update is
the last load-bearing fundamental, landed at v1.0). **GUI/IDE is deferred to its own arc** — the v0.5
seams (protocol generality, the data-layer reach, agent-dispatch modeling) are laid clean; build nothing
on them in v0.6. **(E) The §8 invariants apply unchanged**, plus the new standing practice §8.10
(dogfood lane-(iii): every step records its build insights into the hardened store).

**DEC budget:** DEC-063 → ~DEC-070 (one per step + the scope verdict; ~1.5× the seven steps, the v0.5
ratio).

## §3 — Build order (do not reorder) + per-step spec
**0** scope verdict (DEC-063, write first) → **1** ORM disambiguation (DEC-064, the warm-up correctness
fix) → **2** Django route provider (DEC-065) → **3** JAX-RS sub-resource locators (DEC-066) → **4** AMQP
topic/binding topology (DEC-067) → **5** gRPC package-qualified keying (DEC-068) → **6** lane-(iii) memory
hardening (DEC-069) → **7** profiling pass (DEC-070 if a non-trivial choice). One step at a time, tests
green before moving on, a DEC per non-trivial choice, PROGRESS.md + the insight store updated each session
end.

**Why ORM first (the deliberate reorder from the research-dossier order, recorded here):** it is the
cheapest change, a pure *correctness* regression fix (Superset 1/55 → 0/55 mis-tags), and it mirrors the
v0.5 discipline where Step 1 was the easy gate-closer (8/9 → 9/9) before the hard steps. The frameworks
(Steps 2–3) then share the cross-file resolver; the protocol-keying refinements (Steps 4–5) are the
trickier join-semantics work; memory (6) and perf (7) close the arc.

### §3.1 — Step 1: ORM Django-vs-SQLAlchemy disambiguation (DEC-064) — research §2
**Change:** `static/persistence.py` only. Gate the Django branch on a Django-specific signal:
`(from django.db import models / from django.db.models import Model) OR (qualified models.Model base) OR
(nested class Meta + a models.*Field)`. Else fall through to SQLAlchemy/other (`declarative_base()` /
`DeclarativeBase` / `__tablename__` / `Column`/`Mapped`/`mapped_column`). **Confidence:** EXTRACTED (all
syntactic). **`DbTable` + `PERSISTS_TO` are already correct — only the `orm` property changes.**
**Keystone:** trivially held (no join/surfacing change). **Fixtures:** extend the SQLAlchemy/Django ORM
fixtures with a `Model`-base-non-Django class (the `coremodel` shape). **Acceptance:** re-run Superset →
**55/55** correct ORM tags.

### §3.2 — Step 2: Django decoupled-route provider (DEC-065) — research §5
**Change:** new `contracts/http/providers/django.py`, appended to `PROVIDER_EXTRACTORS` (the only wiring),
+ reuse of `_resolve_name_to_files` (DEC-059) for cross-file view resolution. Parse `urls.py`:
`path('p/', views.fn)`, `re_path(r'...', view)`, `path('p/', MyView.as_view())`,
`path('p/', include('app.urls'))` (recurse + concatenate prefix), DRF
`router.register(r'prefix', ViewSet)` + `include(router.urls)` (expand SimpleRouter/DefaultRouter CRUD
set). Emit `Endpoint(protocol='http')` + HANDLES, **reusing the key `http::<METHOD>::<path>`** (no new
node). **Confidence:** direct `path()`/`as_view()` → EXTRACTED; DRF default-router expansion →
EXTRACTED-by-convention; custom router / `@action` → INFERRED. **Keystone:** held (a `providers/` add +
the existing resolver; `base.join`/`trace`/emit/`serve` untouched). **Acceptance:** a Django app's
`urls.py` routes join their view handlers across files, incl. one `include()` prefix and one DRF router.
**No fabrication:** a route whose view cannot be resolved emits an unmatched provider (HANDLES, honest),
never a synthetic handler `symbol_id`.

### §3.3 — Step 3: JAX-RS sub-resource locators (DEC-066) — research §4
**Change:** extend `contracts/http/providers/jaxrs.py` (DEC-062). Detect a `@Path` method with **no verb
annotation** → sub-resource locator; resolve its declared return type (incl. `Class<T>` forms) to a class
via `_resolve_name_to_files`; recurse into that class's `@GET`/`@Path` methods, concatenating the prefix.
**Confidence:** concrete annotated return type → EXTRACTED; `Object`/interface/abstract return →
AMBIGUOUS (unresolvable statically — emit the locator-as-unmatched, never guess). **Keystone:** held
(`providers/` extension + resolver). **Acceptance:** jersey `bookstore-webapp` → **0 → >0** routes; the
plain `helloworld` resource stays correct (no regression).

### §3.4 — Step 4: AMQP topic-exchange + binding-key topology (DEC-067) — research §3
**Change:** `contracts/messaging/` — key on the **exchange** (`amqp::<exchange>`, the shared literal both
`basic_publish(exchange=)` and `queue_bind(exchange=)` name) so `base.join` matches by exact key
**unchanged**; carry publisher `routing_key` and subscriber `binding_pattern` as edge properties; add an
**AMQP wildcard matcher** (`contracts/messaging/normalize.py`, stdlib `re`: `*`→one word, `#`→zero-or-more,
`.`-delimited) and a contract-layer reconcile/prune step (`base.reconcile_amqp`, the DEC-060
`reconcile_spec_backed` precedent) that tests each exchange-matched candidate: exact → EXTRACTED;
wildcard match → INFERRED; provable non-match → **DROP**; several subscribers match → AMBIGUOUS fan-out.
**Direct/named-queue `queue::<name>` is unchanged** (the new path is topic/exchange only). **Keystone:**
held (`base.join` untouched; the matcher + prune live in the contract layer, not `trace`/emit/`serve`).
**Acceptance:** rabbitmq-tutorials topic examples → **0 → >0** matched ROUTES_TO; the `kern.*`-style
wildcard binding matches a `kern.critical` publish (INFERRED), a non-matching key is dropped.

### §3.5 — Step 5: gRPC package-qualified keying (DEC-068) — research §1
**Change:** `contracts/grpc/normalize.py` (new key `grpc::<module>::<Service>/<Method>`) + the servicer
and stub extractors (recover the generated `*_pb2_grpc` **module identity** from AST) + an **import-alias
table** helper (handle `import X`, `from . import X`, `import X as Y`). Servicer module from the base
`<module>.<Svc>Servicer` and/or the `<module>.add_<Svc>Servicer_to_server(...)` registration; stub module
from `<var> = <module>.<Svc>Stub(channel)`, tied to `<var>.<Method>(...)` by intra-scope binding.
**Confidence:** EXTRACTED (deterministic protoc-emitted tokens). **NO `.proto` parse, NO `[proto]` dep**
(deferred to Go/Java gRPC). **CAVEAT recorded in the DEC:** the module-identity key ≠ the wire path
`/<package>.<Svc>/<Method>` (that equivalence is INFERRED and stays deferred). **Keystone:** held (a
more-specific key on the same exact-match join). **Acceptance:** the grpc-examples monorepo's **975
AMBIGUOUS cartesian joins resolve** (`helloworld_pb2_grpc::Greeter/SayHello` ≠
`route_guide_pb2_grpc::Greeter/SayHello`); route_guide's genuine dual sync+async servicer stays
AMBIGUOUS (correctly — two real impls).

### §3.6 — Step 6: lane-(iii) memory hardening (DEC-069) — research §6A
**Change:** harden the existing `JsonlInsightStore` (DEC-019): keep the JSONL/markdown files as the
authoritative source; add a **derived SQLite/FTS5 BM25 recall index reusing the DEC-041 sidecar**
infrastructure (rebuildable — delete it, rebuild from files); store insights on a **git shadow-ref** for
portability; **dedup by SHA-256 content hash** (the DEC-036 `ParseCache` discipline); optional FSRS-style
decay score kept off the LLM path. `recall_insights` switches its backend from a JSONL scan to the FTS5
index; the optional `[semantic]` ONNX layer fuses via the existing RRF (DEC-038). **Keystone boundary:**
this **does not add a 10th MCP tool or 6th artifact** and **does not change `recall_insights`/
`record_insight` signatures** — it only improves an *existing* tool's retrieval backend (the sanctioned,
bounded touch of `mcp_server` for the agent-insight layer, parallel to DEC-019). **Pure-static floor:**
held (stdlib `sqlite3` + the already-DEC'd `[semantic]` extra; no runtime LLM). **Acceptance:**
`record_insight` → `recall_insights` round-trips through FTS5 with BM25 ranking; the index rebuilds from
files after deletion; dedup collapses identical insights; the store survives a clone via the shadow-ref.

### §3.7 — Step 7: profiling / perf pass (DEC-070 if a non-trivial choice) — research §9
**Change:** a `cProfile`-driven profiling pass (stdlib, no dep) over the three standing cost centers — the
registry-dispatch fan-out, the cross-stack join, the DI/ORM passes — on the 18–21k-symbol acceptance
repos (Superset, hermes-agent). **Behavior must not change** (goldens byte-identical; determinism via
collect-then-sort preserved). Any optimization that changes a data structure or ordering gets its own DEC.
**Incremental/persistent update stays deferred to v1.0** (lane i) — this is profiling + targeted
constant-factor wins only. **Acceptance:** a profile report + at least one documented constant-factor
improvement (or a documented "no safe win without incremental update" finding promoting the work to v1.0).

## §4 — The acceptance gate (§4.9, raised to a publish-prep posture)
`pytest -x` green; `ruff check`/`format` clean; **goldens byte-identical** (every refinement is graph-only
— `python_sample`/`tiny_fixture` carry none of the new markers); `AGENT_BRIEF ≤5kb` everywhere; the
5-artifact + 9-MCP-tool contract unchanged. **Per-step keystone proof:** the `git diff` for each step
touches only its `contracts/`/`static/persistence.py`/resolver/reconcile + tests — **never** `trace`/emit/
`serve`. **Real-repo acceptance (expanded stress matrix — research §7, all MIT/Apache):**

| Step | Primary acceptance repo (the 0→>0 / correctness target) | Stress-test additions |
|---|---|---|
| 1 ORM | apache/superset → 55/55 ORM tags | a mixed SQLAlchemy+Django repo |
| 2 Django | a DRF tutorial app + `include()` prefix + a router | `django/django`; a large Django CMS (e.g. wagtail) for cross-file scale |
| 3 JAX-RS | `eclipse-ee4j/jersey` `bookstore-webapp` → >0 | `mkyong/jax-rs`; Open Liberty `guide-rest-intro` |
| 4 AMQP | `rabbitmq/rabbitmq-tutorials` topic examples → >0 | a real topic-exchange app |
| 5 gRPC | `grpc/grpc` `examples/` → 975 cartesian resolved | route_guide dual-servicer stays AMBIGUOUS (no regression) |
| 6 memory | round-trip + rebuild + dedup + shadow-ref clone | run on the project's own DECISIONS insights (dogfood) |
| 7 perf | Superset + hermes-agent profile | a third large polyglot repo |

Findings land under `docs/findings/v0.6/` with per-refinement confidence splits + the keystone zero-diff
evidence. As in v0.4/v0.5, **an honest single-repo shortfall (reported, never fabricated) is an
acceptable pass with the gap promoted to the next arc** — and v0.6 is expected to surface its own v0.7
seed findings (the findings-drive-the-next-arc loop, framed as evidence-based scoping, not a defect).

## §5 — Memory lanes (status after v0.6)
- **Lane (i) incremental/persistent graph update → v1.0** (DEC-051's line-free `node_id` is its
  no-migration seam; the perf pass §3.7 may surface that no safe constant-factor win exists without it,
  reinforcing the v1.0 placement). **This is the last load-bearing fundamental for Terminal-complete
  v1.0** and the enabling prerequisite for any future near-live IDE surface.
- **Lane (ii) temporal/Graphiti → opt-in-later, unchanged** (2-of-5 threshold, DEC-005/019; LLM cost is
  why it is not the base path). The single opt-in temporal backend — add no second.
- **Lane (iii) agent-facing write-back → HARDENED in v0.6** (§3.6): local-first, zero-LLM FTS5 recall +
  git-portable shadow-ref + content-hash dedup. This is the only v0.6 memory build.

## §8 — Invariants (apply unchanged, plus §8.10)
1. **Reuse `Endpoint`, never a new node type** (the DI/ORM `DbTable` remains the one DEC'd exception; v0.6
   adds none).
2. **Confidence stays sacred.** EXTRACTED only for deterministic literal/syntactic facts (gRPC module
   tokens, ORM signals, direct Django `path()`, exact AMQP/JAX-RS matches). Wildcard AMQP matches →
   INFERRED; provable non-match → DROP; multi-match → AMBIGUOUS-all (emit every candidate, never guess).
   JAX-RS unresolvable return → AMBIGUOUS. DRF custom-router/`@action` → INFERRED.
3. **Pure-static floor (DEC-009).** Never run the analyzed code, hit a live broker/MCP server/network/LLM,
   or invoke protoc. Everything is AST-only (existing tree-sitter grammars) — including all five
   refinements and the lane-(iii) index (stdlib + the already-DEC'd `[semantic]`).
4. **No un-DEC'd runtime dep.** v0.6 adds **none** (research §8). The `[proto]` extra stays deferred;
   gRPC keying recovers module identity from generated Python AST, not `.proto`.
5. **`symbol_id` via `_parent_chain` or the edge is filtered.** Every new/extended provider/consumer/
   resolver composes `<rel_path>::<qn_local>` with the same `_parent_chain`; run-time idempotent
   registration (`register_*_extractors()` in `ContractPhase.run`), never an import side-effect.
6. **`base.join` is not touched for a new match shape.** AMQP wildcard matching lives in the matcher +
   reconcile layer (the DEC-060 precedent), not in `join`. If a refinement needs `join` to iterate-and-
   test, re-key onto a shared literal (the exchange) and refine via properties instead.
7. **No fabrication.** An unresolved Django view / JAX-RS return type / non-matching AMQP key emits an
   honest unmatched provider or is dropped — never a synthetic `symbol_id` or a guessed ROUTES_TO.
8. **Every new edge class is graph-only** → the 5 golden artifacts stay byte-identical; `AGENT_BRIEF ≤5kb`.
9. **The 9 MCP tools + 5-artifact contract are frozen.** New capability surfaces through the *existing*
   `trace` + HOTPATHS section, never a 10th tool or 6th artifact. (Lane-(iii) improves an existing tool's
   backend only.)
10. **Dogfood lane-(iii) (the new standing practice).** From Step 6 onward, every step records its key
    build insights into the hardened insight store (not just PROGRESS notes); as new findings emerge
    mid-build, they are written as insights — the project uses its own memory layer during its own build.

## §9 — DEC pre-draft (the v0.6 ledger; expect ~1.5× expansion)
- **DEC-063** — v0.6 scope verdict (the spine; §2). Write FIRST, before any other v0.6 code.
- **DEC-064** — Step 1 ORM Django/SQLAlchemy disambiguation (§3.1).
- **DEC-065** — Step 2 Django decoupled-route provider (§3.2).
- **DEC-066** — Step 3 JAX-RS sub-resource locators (§3.3).
- **DEC-067** — Step 4 AMQP topic-exchange + binding-key topology (§3.4).
- **DEC-068** — Step 5 gRPC package-qualified keying (§3.5).
- **DEC-069** — Step 6 lane-(iii) memory hardening (§3.6).
- **DEC-070** — Step 7 perf pass, only if a non-trivial optimization choice is made (§3.7).

## §10 — Surfacing (unchanged — the proof the keystone held)
No surfacing-layer change in v0.6. `trace()` walks the new Django/JAX-RS HANDLES, the resolved gRPC
module-qualified joins, and the AMQP exchange routes **for free** (they are all `Endpoint`/`ROUTES_TO`);
the HOTPATHS `## Cross-stack routes` section and `serve --ui` render them with **zero `protocol==`
branch**. The only `mcp_server` touch is the lane-(iii) `recall_insights` backend swap (§3.6) — an
existing tool's retrieval engine, not a new tool. **GUI/IDE remains out of scope**; the v0.5 endgame
seams stay laid-clean-and-unbuilt until their own research arc.

---

*The IDE/GUI is out of scope and needs its own complete research arc once foundations are strong (the
v0.6→v1.0 fundamentals — five-protocol coverage hardened, the data-layer reach, and at v1.0 incremental
update — are what make a future near-live surface possible on the unchanged engine). Lay the foundation;
don't start GUI talks yet.*
