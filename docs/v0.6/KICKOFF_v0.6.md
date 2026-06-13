# KICKOFF_v0.6.md — operating mode for v0.6 "Findings-Driven Refinements"

> Paste the block in §8 as your first message to Claude Code in the repo. Everything above compresses
> into it. Binds with `CLAUDE.md`; points at `PRD_v0.6.md` (the contract) and `research_v0.6.md`
> (cited as *research §1–§9*, its nine Key-Findings sections).

## 1. What you're building (one breath)
v0.5 shipped at **9/9 gate** (DEC-001→062; v0.5.0 tagged & released locally, 710 tests) and proved the
`CrossBoundaryEdge`/`Endpoint` abstraction generalizes across **five protocols** on one spine. v0.6 does
**NOT** add a sixth protocol or expand the public surface. It **hardens the five-protocol abstraction
against the real-repo failure modes the v0.5 acceptance runs surfaced** — five findings-driven
refinements + the first lane-(iii) memory hardening + a profiling pass — then sets the **Terminal-complete
v1.0** trajectory. Every change is a `KeyBuilder`/provider/consumer/resolver edit over the **unchanged**
`base.join`/`Endpoint`/`trace`/emit/`serve` machinery. **Zero new base-env runtime deps.** GUI/IDE is
out of scope and waits for its own research arc.

## 2. The keystone you must internalize before any code
**Reuse the `Endpoint` node for every refinement. Do NOT invent `Tool`/`Service`/`Channel` nodes (the
DI/ORM `DbTable`, DEC-059, stays the one DEC'd exception — v0.6 adds none).** `trace()`, the HOTPATHS
`## Cross-stack routes` section, and `serve --ui` query `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO`
**generically, with no `protocol==` filter**. Each refinement is confined to `contracts/<proto>/` (the
KeyBuilder + extractors), `contracts/http/providers/*` (the framework adds), `static/persistence.py` (the
ORM signal), the shared `_resolve_name_to_files` resolver (DEC-059), and a contract-layer `base.reconcile_*`
helper (DEC-060). **If you catch yourself editing `trace`/emit/`serve` for a refinement, STOP and
generalize** — the abstraction already handles it. The single sanctioned `mcp_server` touch is the
lane-(iii) `recall_insights` backend swap (PRD §3.6) — an existing tool's retrieval engine, not a new
tool. (Full design: PRD §1.)

## 3. Session-start protocol (with CLAUDE.md's)
1. `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` → `git log --oneline -10`.
2. Read `PRD_v0.6.md` §0–§4 fully, §5–§10 skim. Keep `research_v0.6.md` for §refs.
3. State in one sentence: *"Working on v0.6 Step <N> (<name>), respecting DEC-<M> about <Y>."*
4. `DECISIONS.md` ends at **DEC-062**; v0.6 starts at **DEC-063**.

## 4. Build order (do not reorder)
**0** scope verdict (DEC-063, write first) → **1** ORM Django/SQLAlchemy disambiguation (DEC-064, the
warm-up correctness fix) → **2** Django decoupled-route provider (DEC-065) → **3** JAX-RS sub-resource
locators (DEC-066) → **4** AMQP topic-exchange + binding-key topology (DEC-067) → **5** gRPC
package-qualified keying (DEC-068) → **6** lane-(iii) memory hardening (DEC-069) → **7** profiling pass
(DEC-070 if a non-trivial choice). Step 1 is the cheap correctness warm-up (Superset 1/55 → 0/55,
mirroring v0.5's 8/9 → 9/9 Step-1 discipline); 2–3 share the cross-file resolver; 4–5 are the trickier
join-keying work; 6 hardens memory; 7 profiles. Finish v0.6 and ship its findings (`docs/findings/v0.6/`)
before touching v0.7+.

## 5. The five rules that catch most mistakes here
1. **Reuse `Endpoint`, never a new node type.** The keystone proof is a per-step `git diff` that touches
   only that step's `contracts/`/`static/persistence.py`/resolver/reconcile + tests — **never** the
   `trace`/emit/`serve` query logic. If those change for a refinement, you broke the keystone.
2. **Confidence stays sacred.** EXTRACTED only for deterministic literal/syntactic facts (gRPC module
   tokens, ORM signals, direct Django `path()`, exact AMQP/JAX-RS matches). AMQP wildcard match → INFERRED;
   provable non-match → **DROP**; multiple matches → AMBIGUOUS-all (emit every candidate, never guess one).
   JAX-RS `Object`/interface/abstract return → AMBIGUOUS. DRF custom-router/`@action` → INFERRED.
3. **Pure-static floor (DEC-009).** Never run the analyzed code, hit a live broker / MCP server / network /
   LLM, or invoke protoc. Everything is AST-only against existing grammars; the lane-(iii) index is stdlib
   `sqlite3` + the already-DEC'd `[semantic]` extra.
4. **No un-DEC'd runtime dep — v0.6 adds NONE.** gRPC keying recovers the `*_pb2_grpc` module identity from
   generated Python AST (an import-alias table), **not** a `.proto` parse — the `[proto]` extra stays
   deferred to Go/Java gRPC.
5. **`base.join` is not touched for a new match shape, and nothing is fabricated.** AMQP wildcard matching
   lives in the matcher + reconcile layer (re-key onto the shared literal *exchange*, refine via edge
   properties) — never in `join`. An unresolved Django view / JAX-RS return / non-matching AMQP key emits
   an honest unmatched provider or is dropped, never a synthetic `symbol_id` or guessed `ROUTES_TO`. And
   `symbol_id` via `_parent_chain` or the edge is silently filtered; registration is run-time idempotent.

## 6. The differentiator, stated plainly (research §7)
GitNexus is **still PolyForm-Noncommercial** (we are Apache-2.0) and ships open bugs that mirror the exact
failure modes v0.6 fixes — **#1183** (FastAPI `include_router(prefix=)` dropped → prefix-stripped
collisions → 0 cross-links; our Django §5 prefix recursion is the fix) and **#1664** (Java RPC → 0
cross-links). Graphify is MIT but **LLM-required** (a 3-pass code+LLM tool, not pure-static) and has no
cross-boundary ROUTES_TO. v0.6 hardens the only-shipped, pure-static, materialized cross-boundary join
against real code — and on the memory front, **every general-memory tool (Mem0, Zep/Graphiti, cognee,
Letta, SuperMemory) requires a runtime LLM/embeddings**, so our "distillation over retention" pure-static
floor is the genuine differentiator: forensic-deepdive is the **code-domain-specialized peer** to those
tools, Graphiti remaining our single opt-in temporal backend.

## 7. What "done" means (the §4.9 gate, publish-prep posture)
`pytest -x` green; `ruff` clean; **goldens byte-identical**; `AGENT_BRIEF ≤5kb`; the 5-artifact + 9-MCP-tool
contract unchanged; each step's keystone `git diff` clean. **Real-repo acceptance (expanded stress
matrix):** Step 1 → Superset **55/55** ORM tags; Step 2 → a DRF app's `urls.py` joins view handlers across
files (incl. an `include()` prefix + a router), stress on `django/django`/wagtail; Step 3 → jersey
`bookstore-webapp` **0 → >0** routes, `helloworld` no regression; Step 4 → rabbitmq-tutorials topic **0 →
>0** matched ROUTES_TO (`kern.*` matches `kern.critical` INFERRED, non-match dropped); Step 5 → grpc-examples
**975 cartesian AMBIGUOUS resolved** via module-qualified keys, route_guide dual-servicer stays AMBIGUOUS;
Step 6 → `record_insight`→`recall_insights` round-trips through FTS5, index rebuilds from files, dedup
collapses duplicates, store survives a clone via the shadow-ref; Step 7 → a profile report + one documented
constant-factor win (or a documented "needs incremental update → v1.0"). Findings under
`docs/findings/v0.6/` with confidence splits + keystone zero-diff evidence. As in v0.4/v0.5, an honest
single-repo shortfall (reported, never fabricated) is an acceptable pass with the gap promoted to v0.7 —
v0.6 is *expected* to seed v0.7 findings (evidence-based scoping, not a defect).

## 8. The paste-able kickoff block
```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, and `git log --oneline -10`. Then read
docs/v0.6/PRD_v0.6.md (§0–§4 fully, §5–§10 skim) and docs/v0.6/KICKOFF_v0.6.md;
keep docs/v0.6/research_v0.6.md for the §refs (its nine Key-Findings sections).

v0.5 shipped at 9/9 gate (DEC-001→062; v0.5.0 tagged). We are building v0.6
"Findings-Driven Refinements" — HARDENING the five-protocol CrossBoundaryEdge
abstraction against the real-repo failure modes the v0.5 acceptance runs surfaced.
NOT a new protocol, NOT new architecture, NOT any public-surface expansion. GUI/IDE
is OUT of scope (its own research arc later).

FIRST: write DEC-063 — the v0.6 scope verdict: spine = "harden the five-protocol
abstraction against real-repo findings" (the four v0.5 findings + the deferred Django
provider, each a pure extractor/resolver change on the unchanged Endpoint/base.join
spine); Memory = begin lane-(iii) hardening only (local-first zero-LLM FTS5 recall
index reusing the DEC-041 sidecar + git shadow-ref portability — adopt NO general-memory
tool as a base path, all require runtime LLM/embeddings; Graphiti stays the single
opt-in temporal backend; lanes (i) incremental→v1.0 and (ii) temporal→opt-in-later
unchanged); positioning = code-domain-specialized peer to general-memory tools;
trajectory = Terminal-complete v1.0 (incremental update is the last load-bearing
fundamental, at v1.0), GUI/IDE deferred to its own arc. Do NOT write other v0.6 code
until DEC-063 is committed.

THE KEYSTONE (internalize, PRD §1): reuse the Endpoint node for every refinement — do
NOT invent Tool/Service/Channel node types (the DI/ORM DbTable, DEC-059, is the one
DEC'd exception; v0.6 adds none). trace()/serve --ui/the HOTPATHS cross-stack section
query Endpoint/HANDLES/CALLS_ENDPOINT/ROUTES_TO generically with no protocol filter, so
every refinement lights up trace/emit/UI for free. Each step is confined to its
contracts/<proto>/ (KeyBuilder + extractors), contracts/http/providers/* (framework
adds), static/persistence.py (the ORM signal), the shared _resolve_name_to_files
resolver (DEC-059), and a contract-layer base.reconcile_* helper (DEC-060). The ONLY
sanctioned mcp_server touch is the lane-(iii) recall_insights backend swap (an existing
tool's retrieval engine, not a 10th tool). If a refinement makes you edit trace/emit/
serve, STOP and generalize.

THEN build v0.6 in order 1→2→3→4→5→6→7 (PRD §3), one step at a time, tests green before
moving on, a DEC for every non-trivial choice (ending ~DEC-070), PROGRESS.md updated
each session end. Honor every invariant in PRD §8 — especially: reuse Endpoint (no new
node types); confidence sacred (EXTRACTED only deterministic/literal; AMQP wildcard →
INFERRED, provable non-match → DROP, multi-match → AMBIGUOUS-all; JAX-RS unresolvable
return → AMBIGUOUS; DRF custom-router/@action → INFERRED); pure-static floor (never run
code / live broker / MCP server / network / LLM / protoc — AST only); NO un-DEC'd
runtime dep (v0.6 adds none — gRPC keying recovers the *_pb2_grpc module identity from
generated Python AST via an import-alias table, NOT a .proto parse; [proto] stays
deferred); base.join untouched for new match shapes (AMQP wildcard matching lives in the
matcher + reconcile layer, keyed on the shared-literal exchange, refined via edge
properties); no fabrication (unresolved view/return/non-matching key → honest unmatched
provider or dropped, never a synthetic symbol_id); symbol_id via _parent_chain or the
edge is filtered; run-time idempotent registration. NEW standing practice (PRD §8.10):
from Step 6 on, dogfood lane-(iii) — record each step's key build insights into the
hardened insight store, not just PROGRESS notes.

Step 1 (DEC-064, the warm-up): ORM Django-vs-SQLAlchemy disambiguation in
static/persistence.py — gate the Django branch on a Django-specific signal (a
django.db.models import / a qualified models.Model base / a nested Meta + a models.*Field);
else fall through to SQLAlchemy (declarative_base/DeclarativeBase/__tablename__/Column/
Mapped/mapped_column). The DbTable + PERSISTS_TO are already correct — only the orm
property changes. Acceptance: re-run apache/superset → 55/55 ORM tags (was 54/55, the
coremodel Model-base mis-tag).

Confirm understanding in one sentence, write DEC-063, then begin Step 1. Do NOT push to
remote (CLAUDE.md sacred rule — pushing is a separate explicit instruction, never
implied by this kickoff). Do NOT touch v0.7+ or the GUI/IDE until v0.6 passes its §4.9
gate.
```

---

*The GUI/IDE is out of scope and needs its own complete research arc once foundations are strong. v0.6
hardens the five-protocol coverage and the data-layer reach; v1.0 lands incremental update — the last
load-bearing fundamental and the enabling prerequisite for any future near-live surface on the unchanged
engine. Lay the foundation; don't start GUI talks yet. And "pushing it this time" = harder development
effort + an expanded acceptance matrix — never an implied license to push to remote.*
