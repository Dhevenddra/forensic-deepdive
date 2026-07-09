# Changelog

All notable changes to `forensic-deepdive`. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.9.0] — 2026-07-09

> v0.9 **"The Interactive CLI"** — a completion release. Deepdive was already an
> agent-first tool you could *invoke*; v0.9 makes it one a **human** can sit inside.
> Four interactive surfaces (`repl`, `browse`, `onboard`, `deepdive`), a de-leak of
> internal ledger IDs from everything the tool emits, and two Windows fixes that fell
> out of actually driving the CLI rather than only testing it.
>
> Engine, graph, contract and the five-artifact contract are **unchanged**. Emitted
> output changes only in wording (see *Fixed* → ledger IDs) and in two reporting
> lines. The `[interactive]` extra is **opt-in** — `extract` and `serve` stay lean.

### Added
- **`forensic repl`** — an interactive query REPL over **one held-open store**: connect
  once, ask many questions. Natural-language questions by default, `:cypher` for raw
  queries, `:help`/`:quit` meta-commands, history and completion via `prompt_toolkit`.
- **`forensic browse`** — a read-only **Textual TUI graph browser**, loaded from a
  snapshot so it never contends for the store. Launched blocking, never nested inside
  another prompt loop.
- **`forensic onboard`** — a guided wizard for a first-time repo: confirm → `extract` →
  read `AGENT_BRIEF.md` first (then the other four + the graph) → pick your MCP client →
  print the config → restart-and-approve → next steps. `--yes` runs it scripted, and
  needs no extra. It renders its snippet through the **same** renderer as `mcp-config`
  (`cli/mcp_snippet.py`), so a second hardcoded snippet is structurally impossible.
- **`deepdive` — a session shell** (new `[project.scripts]` console script). One prompt
  over one repo, dispatching `extract`/`query`/`trace`/`impact`/`flow`/`diagram`/
  `browse`/`onboard`/`serve` as in-session commands. A known command word is a command;
  anything else is a natural-language question.
- **`forensic mcp-config --dev`** — emits the from-source form
  (`uv run --project <checkout> forensic serve --repo <repo>`) for all four clients,
  instead of only the post-publish `uvx` form.
- **`forensic list --prune`** — drops registry entries whose recorded graph file no
  longer exists, and prints what it removed. Live and graph-less entries are kept, and
  bare `list` never mutates.
- **Self-hosted Claude Code plugin marketplace** — `.claude-plugin/marketplace.json`
  (marketplace `dhevenddra`, plugin source `./`), so the plugin installs straight from
  GitHub with no clone and no PyPI step: `/plugin marketplace add
  Dhevenddra/forensic-deepdive` → `/plugin install forensic-deepdive@dhevenddra`.
- **`CONTRIBUTING.md`** — dev setup, the four-step verification gate, the load-bearing
  architectural invariants, conventional commits, and inbound=outbound Apache-2.0.
- **`[interactive]` extra** — `prompt-toolkit` + `textual` (both MIT). Required by the
  four surfaces above; every other command works without it, and a missing extra prints
  an actionable install hint rather than a traceback.

### Fixed
- **Internal `DEC-NNN` ledger IDs no longer appear in any emitted artifact or MCP
  payload.** They leaked into all five artifacts' confidence banners, MAP/HOTPATHS/
  ARCHAEOLOGY/AGENT_BRIEF provenance notes, `ARCHITECTURE.md`, two skill shims, and the
  `trace` payload's `boundary` string. `DECISIONS.md` is local-only and never ships, so
  each was a **dangling reference for every consumer** of an analyzed repo. Provenance
  is now self-contained English ("per the call-graph resolver"), and a regex sweep test
  over all five rendered artifacts keeps it that way. DEC references remain in code
  comments, which are maintainer-facing.
- **Examples-only repos no longer under-report their size.** Where files are demoted as
  `examples/`, the headline now reads `N (+M in graph, demoted as examples/)` in both
  `MAP.md` and the styled `extract` summary. The classification is unchanged — only the
  line people quote. Repos with no demotions emit a byte-identical line.
- **Module-scope handlers display their module dotted-path**, not the literal `<module>`
  — `backend/routers/whatsapp.py::<module>` now renders as `backend.routers.whatsapp` in
  HOTPATHS, `AGENT_BRIEF.md`, `ARCHITECTURE.md` and the styled `trace` tree. Display
  only: the graph identity and the `trace` JSON payload keep the raw qualified name.
- **Windows: interactive surfaces no longer crash under Git Bash / MinTTY.**
  `sys.stdin.isatty()` returns **True** there while `prompt_toolkit` still has no Windows
  console screen buffer, so a TTY guard alone is not enough. All three surfaces now catch
  `NoConsoleScreenBufferError` and print an actionable hint (use PowerShell/cmd, or
  prefix with `winpty`) instead of a traceback.
- **Windows: the session shell borrows the store rather than holding it.** LadybugDB
  takes an **exclusive file lock on Windows** (a second concurrent handle raises; the
  same open succeeds on Linux). Since every path-taking tool opens its own handle, a
  shell that held the store open would have crashed 6 of its 9 commands. `StoreSession`
  releases around every such tool and lazily re-opens — correct on both platforms, and
  it makes in-session `extract` invalidate-and-reopen for free. The tool contract (tools
  take a path, never an open store) is unchanged.

### Changed
- **README** — added "Install from PyPI" + "Use it as an MCP server" sections (plugin /
  MCP Registry / manual-config), a Contributing section, and an explicit Apache-2.0 §4
  attribution note (the LICENSE-appendix boilerplate is a template, not a requirement).
- **`docs/install.md`** — 0.8.0 is live: dropped the pre-publish caveat (now links the
  PyPI project + the MCP Registry entry `io.github.Dhevenddra/forensic-deepdive`),
  documented the two-command plugin install, and both `mcp-config` forms.
- **`examples/`** — all eleven repos regenerated at 0.9.0 (new footers, the two reporting
  fixes, and zero ledger-ID references).

## [0.8.0] — 2026-06-21

> v0.8 **"USABLE → USEFUL + public release"** — the first public PyPI release.
> **Framing (honest):** v0.8 ships as an **assisted-analysis** tool. The
> autonomous end-to-end usefulness question (does deepdive-seeding make an agent
> *resolve* real issues faster) is **not yet proven**: a model-free localization
> **pilot** is recorded (`experiments/fastcontext/RESULTS.md` — the static seed is
> a *weak* prior, recall@10 ≈ 0.44 on an n=8 subset), and the end-to-end
> measurement is deferred to v0.9 (needs a GPU + frontier main-agent endpoint). No
> autonomous-execution claims are made here.

### Added
- **`ARCHITECTURE.md` + `forensic diagram`** — a system-level, confidence-styled
  Mermaid view of the cross-boundary graph (ROUTES_TO / INJECTS / PERSISTS_TO),
  a *separate* surface (not a sixth contract artifact); regenerated on extract.
- **`forensic mcp-config`** — prints a copy-paste MCP client snippet (Claude
  Code / Cursor / VS Code / Codex), pipe-redirectable to `.mcp.json`.
- **`--refresh-shims`** — rewrites *stale* Deepdive-generated shims; hand-edited
  files are never touched.
- **`--emit-vault`** — opt-in [Obsidian](https://obsidian.md) vault (frontmatter +
  `[[wikilinks]]` + MOC) under `<output>/vault/`.
- **Distribution** — schema-valid MCP Registry `server.json`, a Claude Code plugin
  (`.claude-plugin/` + `.mcp.json`), a `forensic-deepdive` console alias for
  `uvx`, per-client install docs (`docs/install.md`), and PyPI Trusted-Publishing
  (OIDC) release CI.
- **`forensic_deepdive.seed`** — a pure-static, zero-LLM graph-derived context
  seed (used by the FastContext experiment; reusable on its own).

### Changed
- **Precision (Track B):** `impact()` cross-file name-coincidence is now AMBIGUOUS
  (a precise default set, recoverable at the AMBIGUOUS floor); NL `query()` gains a
  name-substring + de-inflection lexical tier and states degraded mode at the point
  of use; HOTPATHS "Callers" is now **distinct callers** (not raw edge count);
  `impact`/`context` dedupe by node_id; `flow` drops trivial self-cycles; AGENT_BRIEF
  demotes theme/constant hubs and gates thin-signal rules on low-history repos;
  ARCHAEOLOGY suppresses the bus-factor-1 ownership table and warns on shallow clones.
- **`trace`** self-notes inapplicability on repos with no cross-boundary endpoints.

### Fixed
- **Packaging (critical):** declared `tree-sitter` as a core dependency and pinned
  the ABI-compatible `tree-sitter` / `tree-sitter-language-pack` pair — a clean
  `pip install` previously crashed (`ModuleNotFoundError`, then a Language/Parser
  ABI mismatch). Vendored UI assets now resolve via `importlib.resources`. Wheel
  clean-room-verified; 3-platform build CI added.

## [0.7.0] — 2026-06-19

> v0.7 **"Coverage Completion + the CLI Style System"** — a two-track, publish-prep
> release (no sixth protocol, no public-surface expansion). **Track A** completes
> extractor coverage on the **unchanged** five-protocol `Endpoint` spine (Django
> `include(<variable>)` recursion + CBV verbs + DRF `@action`; JAX-RS `@ApplicationPath`
> + `@Produces`/`@Consumes`; AMQP literal-key real-repo acceptance), hardens lane-(iii)
> agent memory (opt-in `[semantic]` RRF + recency decay + explicit shadow-ref push), and
> indexes the `resolve_name_to_files` hot path (**49.7×**, byte-identical). **Track B** adds
> the publish-facing **styled CLI** — a `DEEPDIVE` banner, a registry-driven `forensic info`
> capability panel, and styled `extract` + a new `forensic trace` command — all Console-only,
> with artifacts staying byte-identical plain markdown and machine streams ANSI-free. Closed
> the usability gate (MANUAL_TEST run solo + an agent-onboarding A/B/C + a live MCP test on
> Iris-Nearby): **usable confirmed**; onboarding auto-discovery + skill-routing verified in a
> real session. DEC-071 → DEC-081; 779 tests. The 5-artifact + 9-MCP-tool contract is frozen.

### Added
- **Styled CLI (DEC-077/078/079)** — a themed Rich Console (blue/black/white brand chrome;
  confidence keeps semantic green/yellow/red + glyph, never colour-alone, ASCII `[E]`
  fallback), a static `DEEPDIVE` banner with a blue vertical gradient, a **data-driven
  `forensic info`** capability panel (artifacts/protocols/tools read from the live registries,
  so it can't drift), a styled `extract` summary with a confidence-coded cross-stack split,
  and a new **`forensic trace <symbol>`** CLI command (confidence-coloured Rich tree;
  `--json`/non-TTY → plain JSON).
- **Provider/coverage completion** — Django `include(<variable>)` recursion + class-based-view
  per-method verbs + DRF `@action` + deep dotted view paths (DEC-072); JAX-RS `@ApplicationPath`
  app-prefix + `@Produces`/`@Consumes` content-type + single-implementer interface-return
  locators (DEC-073); AMQP literal-key real-repo acceptance on `pika` (DEC-074).
- **Memory lane-(iii) follow-ons (DEC-075)** — opt-in `[semantic]` ONNX RRF fusion over
  insights + a stdlib recency-decay score (no `py-fsrs`) + an explicit `forensic insights push`
  shadow-ref publish (never automatic).

### Fixed
- **`serve --repo`** is now an option (was positional), matching `trace`/`graph` and the
  documented MCP config (DEC-080).
- **cp1252 pipe-safety** — piped `--help` (an arrow glyph in `trace`'s docstring) and the
  styled `extract` summary (a `✓`) no longer raise `UnicodeEncodeError` on a Windows console
  code page; both degrade to ASCII (DEC-080).
- **Onboarding-shim accuracy** — generated `CLAUDE.md`/`AGENTS.md` (and internal docstrings)
  now list all **nine** MCP tools, not a stale five (DEC-080).

### Performance
- **`resolve_name_to_files`** indexed by `rel_path` — **49.7×** on the hot path, byte-identical
  output (DEC-076). LadybugDB prepared-statement reuse measured (1.28×) but **deferred** (Kuzu
  deprecates the separate prepare+execute API).

## [0.6.0] — 2026-06-14

> v0.6 **"Findings-Driven Refinements"** — does **not** add a sixth protocol or expand
> the public surface. It **hardens** the five-protocol `CrossBoundaryEdge`/`Endpoint`
> abstraction against the four real-repo failure modes the v0.5 acceptance runs
> surfaced, ships the deferred Django provider, hardens lane-(iii) agent memory, and
> profiles. Every refinement is a `KeyBuilder`/provider/consumer/resolver/`reconcile_*`
> change over the **unchanged** `base.join`/`Endpoint`/`trace`/emit/`serve` machinery
> (the keystone held on all eight steps). **Zero new base-env runtime deps**; the
> 5-artifact + 9-MCP-tool contracts unchanged; the 5 golden artifacts stay
> byte-identical (every refinement is graph-only). DEC-063 → DEC-070; 740 tests.

### Added
- **Django decoupled-route provider** (DEC-065) — the first provider that resolves
  handlers **across files**: a `urls.py` `urlpatterns` table (`path()`/`re_path()`/
  `Klass.as_view()`/`include()` prefix recursion/DRF `router.register` CRUD) binds to
  its view handlers in other files via the shared `resolve_name_to_files` ladder +
  Python submodule resolution. Method-agnostic views key at `http::*::<path>`. wagtail:
  **0 → 125** `Endpoint`s, **99 EXTRACTED cross-file HANDLES** across 29 files.
- **JAX-RS sub-resource locators** (DEC-066) — a `@Path` method with no verb resolves its
  return type to a resource class and recurses into its routes (prefix concatenated).
  jersey `bookstore-webapp`: **0 → 1** cross-file EXTRACTED route. `Object`/unresolvable
  return → an honest unmatched locator (never guessed).
- **AMQP topic-exchange + binding-key topology** (DEC-067) — RabbitMQ topic exchanges key
  on the shared-literal **exchange** (`amqp::<exchange>`) so `base.join` matches unchanged;
  a contract-layer `reconcile_amqp` refines each pair by the `*`/`#` routing-key↔binding
  match (exact→EXTRACTED, wildcard→INFERRED, non-match→DROP, multi→AMBIGUOUS). rabbitmq-
  tutorials: **0 → 3** exchange `ROUTES_TO`.
- **Agent-memory FTS5/BM25 recall** (DEC-069) — `recall_insights` gains a derived,
  rebuildable SQLite/FTS5 BM25 index (reusing the DEC-041 sidecar) + content-hash dedup +
  a git **shadow-ref** (`refs/forensic-deepdive/insights`) so the store survives a clone.
  **Zero runtime LLM** (the pure-static floor); same tool signatures (the one sanctioned
  `mcp_server` touch — an existing tool's backend, not a 10th tool).

### Changed
- **ORM Django/SQLAlchemy disambiguation** (DEC-064) — a bare `Model` base (e.g. Flask-
  AppBuilder's SQLAlchemy `Model`) is only tagged Django on a Django-specific signal
  (`django.db.models` import / qualified `models.Model` base / nested `Meta` + `models.*Field`);
  else it falls through to SQLAlchemy. apache/superset: **54/55 → 55/55** correct ORM tags.
- **gRPC package/directory-qualified keying** (DEC-068) — `grpc::<module>::<Service>/<Method>`,
  recovering the generated `*_pb2_grpc` module identity from Python AST (servicer base / stub
  ctor / proto filename) via an import-alias table; **directory-qualified** for flat sibling
  imports (each example dir is its own `sys.path` root). grpc-examples: **~975 → 68**
  cartesian `AMBIGUOUS` (resolved; the 68 are genuine same-dir dual servers). No `.proto`
  parse for the module; `[proto]` stays deferred.

### Performance
- **Indexed absolute-import resolution** (DEC-070) — `_resolve_python_import`'s O(files)
  suffix scan (the profiling hot spot — 62% of a Superset extract, ~1.2 B `endswith` calls)
  becomes an O(1) precomputed suffix-index lookup. **A Superset extract drops 1711s → 117s
  (14.7×); 1.258 B → 49.5 M function calls** — byte-identical output (the resolver returns
  the same file → the same graph → the same artifacts).

### Notes
- v0.6 surfaces its own v0.7 seeds (reported, never fabricated): Django `include(<variable>)`
  recursion; AMQP dynamic-key matching; `resolve_name_to_files` as the next perf candidate;
  Go/Java gRPC + the wire-path equivalence; the `[semantic]` RRF fusion over insights.
- Incremental/persistent graph update stays deferred to **v1.0** (the last load-bearing
  fundamental). GUI/IDE remains out of scope (its own research arc).

## [0.5.0] — 2026-06-12

> v0.5 **"Cross-Boundary Protocols"** — extends the DEC-043 `CrossBoundaryEdge`/
> `Endpoint` abstraction from one protocol (HTTP) to **five** (HTTP, MCP, registry-
> dispatch, gRPC, messaging) **on the same spine**, plus the DI/ORM traceability
> tail. The headline: agents. v0.4 proved the static layer was blind to how agents
> wire themselves; v0.5 models MCP tool dispatch + registry dispatch as cross-
> boundary protocols, taking hermes-agent from **1** internal `ROUTES_TO` to **22
> MCP tool endpoints + 35 registry-dispatch `ROUTES_TO`**. The v0.4 flagship
> shortfall is **closed**: Superset **0 → 61** cross-stack `ROUTES_TO`. Pure-static
> floor + the 5-artifact + ≤5kb-AGENT_BRIEF contracts unchanged; the 5 golden
> artifacts stay byte-identical (every new edge class is graph-only).

### Added
- **The flagship HTTP gap closed** (DEC-056) — a configured-client consumer
  (`<Client>.get/post({endpoint})`, the SupersetClient shape, guarded by object-
  literal shape not an allowlist) + a Flask-AppBuilder provider (`ModelRestApi`/
  `@expose`). Superset: **0 → 61** cross-stack `ROUTES_TO`, 8/9 → **9/9** gate.
- **MCP as a `CrossBoundaryEdge` protocol** (DEC-057) — `@mcp.tool()` providers +
  `ClientSession.call_tool("name")` consumers joined through
  `Endpoint(protocol='mcp', contract_id='mcp::<tool>')`. Bare-tool keying, separator-
  normalized. The **keystone proof**: zero surfacing-layer change — `trace`/`serve
  --ui`/HOTPATHS light up MCP for free.
- **Tool-registry dynamic dispatch** (DEC-058) — `registry[key]()` / `@registry.register`
  / dict-literal registries modeled as `Endpoint(protocol='registry')` with a
  provider-side `::*` wildcard fan-out (literal-key → INFERRED, dynamic-key →
  AMBIGUOUS-all), **capped** per registry, surfaced honestly.
- **The DI/ORM traceability tail** (DEC-059) — `INJECTS` (Symbol→Symbol) +
  `PERSISTS_TO` (Symbol→`DbTable`) + the one new-node exception (`DbTable`). Spring
  `@Autowired`/ctor + FastAPI `Depends`; SQLAlchemy/JPA/Django ORM. The Spring
  resolution ladder (concrete→EXTRACTED, single-impl→INFERRED, multi→AMBIGUOUS-all).
  `trace` now walks handler→inject→repo→model→table (the committed v0.4 boundary
  promise, delivered).
- **gRPC + messaging** (DEC-060/061) — gRPC `.proto` (tree-sitter-proto, zero new
  dep) as the spec + servicer providers + stub consumers; messaging `topic::`/`queue::`
  pub↔sub (Kafka/pika/`@KafkaListener`). The OpenAPI spec-reconcile generalized
  (`reconcile_spec_backed`).
- **Framework breadth** (DEC-062) — NestJS (`@Controller` + verb decorators) + JAX-RS
  (`@Path` + `@GET`/…) HTTP providers, with the enclosing-class guard.

### Notes
- Real-repo acceptance on all 6 steps (`docs/findings/v0.5/`): Superset, hermes-agent,
  spring-petclinic, grpc/rabbitmq/nest/jersey. Four v0.6 refinements logged.
- Deferred (carried to a future arc): Django provider; `PROVIDES` edge; server-/
  package-qualified MCP/gRPC keying; Redis/NATS/SNS-SQS + topic-exchange messaging;
  TypeORM/Prisma; multi-repo federation; memory hardening. See `docs/findings/v0.5/DEFERRED.md`.

## [0.4.0] — 2026-06-05

> v0.4 **"Cross-Stack & Visual"** — the cross-language wedge (a frontend call
> joins to its backend handler through an `Endpoint` node) plus a served graph
> explorer. Accepted at **8/9 §4.9 gate items** (the one shortfall — 0 ROUTES_TO
> on Superset's custom `SupersetClient`/Flask-AppBuilder stack — is framework
> coverage, scoped to v0.5; the join machinery is proven on clean repos). Pure-
> static floor and the 5-artifact + ≤5kb-AGENT_BRIEF contracts are unchanged.

### Added
- **Cross-stack `ROUTES_TO`** — `Endpoint` join node + `HANDLES` / `CALLS_ENDPOINT`
  / materialized `ROUTES_TO` edges (DEC-043). Provider extractors: FastAPI, Flask,
  Express, Spring MVC. Consumer extractors (7): fetch/axios, RTK Query, React
  Query, Angular HttpClient, jQuery, Python requests/httpx, Java RestTemplate/
  WebClient/OpenFeign. Three-tier join confidence — EXTRACTED only for spec-backed
  or unique-literal-both-sides (DEC-044/045/046/047).
- **OpenAPI codegen shortcut** (DEC-048) — a committed spec marks providers
  `spec_backed`, upgrading even templated-client joins to EXTRACTED; spec-only
  operations surface as documented-but-unlocated. JSON zero-dep; YAML behind the
  `[openapi]` extra.
- **`trace` (9th MCP tool)** + a HOTPATHS `## Cross-stack routes` section + an
  AGENT_BRIEF cross-stack rule (DEC-052) — surfacing the wedge.
- **`forensic serve --ui`** (DEC-053) — a read-only, 127.0.0.1-only stdlib HTTP
  server hosting a vendored Sigma.js (WebGL) whole-graph explorer with **mandatory
  level-of-detail** bounding + filtering (edge type / confidence / language /
  directory); `ROUTES_TO` highlighted. Vendored MIT bundles (Sigma.js 2.4.0,
  graphology 0.25.4 + library 0.8.0); no new Python runtime dep.
- **TS/TSX heritage capture** (DEC-050) — abstract classes, interface-extends,
  generic/member-expression supertypes (gitnexus EXTENDS 2→21; superset 1166→1320).
- **`example` file-role** (DEC-049) — tutorial/sample dirs stay in the graph but
  are demoted in PageRank + query shaping (fastapi shaped-query AMBIGUOUS 36 %→0 %).
- **Stable, line-number-free node IDs** (DEC-051) — survive an unrelated same-file
  edit (the v1.0 incremental/rename seam).

### Fixed
- **`example`-role false positive on JVM packages** (DEC-054 finding) — `samples`/
  `example`/`demo` as Java *package* components under a `src/main/<lang>/` root no
  longer trigger the `example` role. Previously the entire canonical Spring
  reference app (`org.springframework.samples.petclinic`) and any
  `com.example.demo` (Spring Initializr default) were demoted out of `source`.

### Acceptance (§4.9, Item L) — 8 of 9 gate items green
Findings: [`docs/findings/v0.4/`](docs/findings/v0.4/). Validated on Superset
(flagship) + purpose-built Spring+React & OpenAPI repos + gitnexus + fastapi.
- ✅ tests/ruff; codegen shortcut; TS-heritage; `example` role; `serve --ui` LOD
  (Superset's 348k co-change edges → 114-node default view); determinism; stable
  IDs; AGENT_BRIEF ≤5kb.
- ⚠️ **Cross-stack `ROUTES_TO` is proven on clean repos but 0 on Superset** — its
  custom `SupersetClient` frontend wrapper + Flask-AppBuilder backend are outside
  v0.4's generic extractor coverage. The join machinery works; framework coverage
  is the gap. **No fabricated joins.**

### Deferred to v0.5 (defined by the acceptance, DEC-054)
- A generic **configured-client consumer extractor** (`<Client>.get({endpoint})`)
  and a **Flask-AppBuilder provider extractor** — unlock the Superset join.
- The previously-deferred **NestJS / Django `urls.py` / JAX-RS** providers.
- Keep spec-generated (`AUTO-GENERATED`) clients in the graph so the codegen
  shortcut fires on them.

## [0.3.0] — 2026-05-31

> v0.3 **"Precision & Speed"** is the foundation pass before the v0.4
> cross-stack wedge (the DEC-034 re-sequence: a trustworthy `ROUTES_TO`
> edge needs method-call resolution first). Seven items A–G, all
> tests-green, accepted on six real repos. The graph, the MCP surface,
> and the 5-artifact contract are unchanged in shape — everything here
> is additive.

### Added

#### Speed — incremental + parallel parse (Items A+B, DEC-036/035)
- **Content-addressed parse cache** keyed on `(content_sha256, language,
  PARSER_VERSION, tags.scm hash)`, stored path-independently so identical
  files share one entry. `ParsePhase` split out of `StaticPhase`;
  incremental *parse* (graph still full-rebuild). `--no`-cache escape hatch.
- **Parallel parse** via `ProcessPoolExecutor` inside `ParsePhase`
  (`--workers N`, default `min(cpu-1,16)`, serial guard < 200 files).
  Determinism preserved by reassembling records in sorted `rel_path` order
  — byte-identical artifacts across `--workers 1` vs N and cold vs warm.
- **Result:** Omi cold extract **930 s → 406.6 s (−56 %)**; warm re-extract
  ≤ 1.9 s on every test repo.

#### Precision — receiver-type method resolution (Item C, DEC-037)
- Dotted/method calls (`self.m()`, `this.m()`, `Foo.m()`, `mod.m()`),
  previously dropped, are now resolved by **receiver-type inference** — all
  tagged `INFERRED` (never silently upgraded to `EXTRACTED`). CALLS edges
  gain a `via` property (`self|this|static|module|bare`). Unresolved dotted
  calls are **dropped, not flooded as AMBIGUOUS** (the deliberate choice
  that keeps the AMBIGUOUS ratio flat while recovering method edges).
- **Result:** method edges recovered that v0.2 dropped — Omi 1,736,
  Superset 1,919, ripgrep 1,528 — overwhelmingly precise INFERRED.

#### Rust — the 9th language (Item D, DEC-040)
- `tree-sitter` Rust grammar; `impl` methods bind non-lexically to their
  type (`impl Greeter { fn render }` ⇒ `render` MEMBER_OF `Greeter`);
  `impl Trait for Type` ⇒ IMPLEMENTS; `use` imports with
  crate/self/super intra-crate suffix-match; `self.`/`Type::` method calls
  feed Item C. (`mod`/`macro_rules!` and Cargo-aware resolution deferred.)

#### Hybrid NL query (Item E, DEC-038/041/042)
- The MCP `query` tool's natural-language branch is now a **three-retriever
  hybrid** fused by **Reciprocal Rank Fusion (k=60)** then output-shaped
  (boost implementation, demote test/vendored/generated):
  - **Lexical** — always-on SQLite **FTS5/BM25** sidecar (no new dep),
    exact-identifier-first then BM25 prefix, camelCase tokenization.
  - **Structural** — always-on graph proximity to query-named symbols +
    CALLS in-degree centrality.
  - **Semantic** — opt-in offline ONNX embeddings behind a new
    `[semantic]` extra; numpy memmap + brute-force cosine; **no network,
    bring-your-own local model**. Absent ⇒ two-retriever, said so.
- Results carry **per-hit provenance** `{symbol, file, line, score,
  retrievers, confidence}` plus `retrievers_active` + `degraded`
  (honest degraded mode). The pure-static floor (DEC-009) holds.

#### Mermaid visual export + 8th MCP tool (Item F, DEC-039)
- New `forensic graph <target> --format mermaid` CLI and **`visualize`
  MCP tool** (the 8th). Bounded subgraph (BFS to depth, node cap 40 with
  a summarize-and-truncate node, never a silent drop). **Edge style
  encodes confidence** in flowchart mode (solid=EXTRACTED, dashed=INFERRED,
  dotted=AMBIGUOUS) — making the taxonomy *visible*. flowchart vs
  classDiagram auto-picked by target kind.

### Acceptance (Item G)

- Six real repos, all 8 gate checks pass (`docs/findings/v0.3/`): **Apache
  Superset** (primary polyglot stress — Python+TS+React), **ripgrep**
  (Rust), re-runs of **Omi** + **spring-petclinic**, and the **fastapi** +
  **gitnexus** carryover (the v0.2 §5.4 debt). `examples/` committed for all
  six. The hybrid query on Superset returns the Python SQLAlchemy models +
  the TS frontend `Dashboard` from one phrase — staging the v0.4 wedge.

### Performance

- See the Items A+B note above. Cold extract is now materially below the
  v0.2 measurement on the same repo; the agent-facing budgets (cache-hit,
  MCP `context`/`impact`) were already met and are unchanged.

### Notes

- New optional dependency: `[semantic]` (`onnxruntime`, `tokenizers`,
  `numpy`) — opt-in only; the base install stays LLM-, network-, and
  numpy-free. FTS5 is stdlib `sqlite3` (no dep).
- DECs DEC-034 → DEC-042 written this arc (the v0.3 re-sequence + per-item
  decisions). 471 tests (1 skipped without the `[semantic]` extra).

## [0.2.0] — 2026-05-25

> v0.2 is a **product pivot**, not a v0.1 increment. v0.1 was a
> structural orienter (5 markdown artifacts from file-level
> dependencies + PageRank). v0.2 ships a real, persistent code
> knowledge graph plus an MCP server that exposes 7 composite tools
> for any AI coding agent — Claude Code, Cursor, Codex, Continue,
> Cline, Windsurf. The 5 markdown artifacts stay; they are now
> projections of the graph.

### Added

#### The graph (DEC-013, DEC-014)
- **Persistent embedded graph store** backed by LadybugDB (the live
  community fork of Kuzu, which Apple acquired and archived in Oct
  2025). Single-file DB at `<repo>/.deepdive/graph.lbug`. Behind a
  `GraphStore` ABC so the v1.0 ArcadeDB hedge swaps in cleanly.
- **Pipeline DAG of typed phases** replaces v0.1's single-function
  pipeline. Five phases at v0.2 (Inventory, Static, Flatten, History,
  BuildGraph, Emit) with explicit `depends_on` + typed outputs. Kahn
  topo-sort runs them; alternative backends or v0.3 framework
  resolvers slot in without restructuring.

#### The honest confidence taxonomy (DEC-007, DEC-015)
- **Every edge in the graph carries `confidence ∈ {EXTRACTED,
  INFERRED, AMBIGUOUS}`** — EXTRACTED for AST/git-deterministic
  edges, INFERRED for heuristic resolution, AMBIGUOUS when the
  resolver can't disambiguate.
- **Per-section + per-rule confidence labels** in the 5 markdown
  artifacts. The v0.1 "every fact below is EXTRACTED" blanket lie is
  gone. AGENT_BRIEF rules tag individually: load-bearing-file rules
  (PageRank-derived) → `[INFERRED]`; churn-point rules (raw git
  counts) → `[EXTRACTED]`; co-change rules → `[INFERRED]`.
- HOTPATHS shows a **confidence-mix column** per row — at-a-glance
  the reader sees "this top-callee resolves cleanly (4 EXTRACTED +
  1458 INFERRED)" vs "this is a same-name cross-file collision (449
  AMBIGUOUS)".

#### 8 languages (DEC-020)
- Doubled from 4 to 8: added **TypeScript, JavaScript, Java, Go**
  alongside the v0.1 Python, C, Dart, Swift. Hand-rolled `tags.scm`
  applying the DEC-012 + Dart-fix precision lessons — bare-call
  references only; dotted member calls dropped via the `_`-prefixed
  helper-capture mechanism. Zero new dependencies
  (`tree-sitter-language-pack` already bundled all five). Rust
  deferred to v0.3.

#### Full v0.2 graph build (item 8b, DEC-023 → DEC-028)
- **Nodes:** File, Symbol, Module, Commit, Author (+ synthetic
  per-file `<module>` Symbol so module-level CALLS have a valid
  caller endpoint).
- **Edges:** DEFINES, MEMBER_OF, IMPORTS, CALLS, EXTENDS, IMPLEMENTS,
  TOUCHED_BY_COMMIT, AUTHORED_BY, CO_CHANGES_WITH.
- **MEMBER_OF (DEC-023):** qualified-name parent chain
  (`Outer.Inner.method`); methods, fields, nested classes get a
  containment edge. Go's receiver-binding pattern (`func (g *Greeter)
  Greet()`) special-cased; every other language uses lexical scope.
- **IMPORTS + Module nodes (DEC-024):** per-language code-walk
  extractors covering 8 import shapes for Python alone plus
  TS/JS/Java/Go/Dart/Swift/C. Language-prefixed Module PK
  (`python:os` vs `go:os`) so cross-language same-name modules don't
  collide on the single-column PK real-ladybug supports.
- **CALLS resolver (DEC-025):** 4-step algorithm — (1) same-file
  lexical scope (EXTRACTED), (2) import-graph walk (EXTRACTED for
  explicit names; INFERRED for wildcard / whole-module), (3)
  receiver-type inference for method calls (INFERRED, partial v0.3
  work), (4) cross-file same-name fallback (INFERRED single,
  AMBIGUOUS multi — every candidate surfaced per DEC-015).
- **Commit + Author + TOUCHED_BY_COMMIT + AUTHORED_BY (DEC-026):**
  full per-commit metadata + file-touch lists from git, mailmap-
  canonical authors. All EXTRACTED — git is ground truth.
- **CO_CHANGES_WITH (DEC-027):** in-memory pair aggregation during
  the commit walk; threshold ≥2 (configurable) filters coincidence.
  INFERRED — computed signal, not a fact.
- **EXTENDS + IMPLEMENTS (DEC-028):** per-language inheritance
  extractors (Python multi-base, TS/Java `class_heritage`, Go
  interface-conformance declarations, Dart mixins/interfaces, Swift
  protocols-as-EXTENDS). Same 3-step resolver as CALLS.

#### MCP server with 7 composite tools (DEC-016, DEC-019, item 10)
- `forensic serve` starts a stdio-transport MCP server consumable by
  Claude Code, Cursor, Codex, Continue, Cline.
- **`impact(symbol, depth, direction, min_confidence)`** —
  blast-radius BFS over CALLS, depth-bucketed, confidence-filterable.
- **`context(symbol)`** — Glass-style single-call kitchen sink:
  definition + signature + callers + callees + parent/siblings/
  members + extends/implements + recent commits + dominant author +
  recent insights.
- **`archaeology(file_or_symbol)`** — churn, top authors with %, bus
  factor, co-change cluster, defect proximity, recent commits.
- **`flow(entry_point, max_depth)`** — DFS along CALLS with cycle
  detection.
- **`query(natural_language | cypher)`** — raw Cypher or substring
  search.
- **`record_insight(symbol, claim, evidence, verified_by)`** (DEC-019)
  — appends one durable insight to a per-repo store.
- **`recall_insights(symbol, since, limit)`** — newest-first
  substring match.

#### Agent-insight layer — JSONL default, opt-in Graphiti (DEC-019)
- Two-backend architecture behind an `InsightStore` ABC.
- **`JsonlInsightStore` is the always-available default** —
  append-fsync per record, no dependencies, file at
  `<repo>/.deepdive/insights.jsonl` (human-readable, hand-editable,
  git-friendly, survives a corrupt single line).
- **`GraphitiInsightStore` is opt-in** — requires the `[graphiti]`
  extra, falls through to JSONL when graphiti-core is unavailable or
  the DEC-005 2-of-5 threshold fails (≥50k LOC, ≥25 contributors,
  ≥18mo old, ≥200 PRs/12mo, ≥100 issues w/ discussion).
- `context(symbol)` always includes `recent_insights: list[Insight]`
  — empty if none, never absent (agent-facing contract stability).
- **Real-LLM Graphiti runtime acceptance is honestly deferred to user
  verification** per DEC-019's stated v0.2 scope: the structural wiring
  is real and unit-tested with mocked graphiti-core (40 tests); the
  end-to-end `add_episode` → `search` round-trip against a real LLM
  (Ollama local or OpenAI / Anthropic cloud) is the user's call to
  exercise on a threshold-passing repo with the appropriate credentials
  + the `[graphiti]` extra installed. The JSONL floor works fully
  end-to-end with zero LLM, zero network — that's the PRD §5.5
  honest-mode gate.

#### Multi-platform skill emission (DEC-031, item 13)
- `forensic extract` now writes **10 shims** into the target repo
  (was 4 in v0.1):
  - 4 editor shims: `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/
    codebase.mdc`, `.continue/rules/codebase.md`.
  - **5 single-intent skills** under `.claude/skills/codebase-<intent>/
    SKILL.md` for the five common agent workflows: `exploring`,
    `debugging`, `impact-analysis`, `refactoring`, `onboarding`.
    Each description includes a "Use when... Do NOT use..." anchor
    so adjacent skills don't fight over the same user phrase.
  - **`.claude-plugin/plugin.json`** Claude Code plugin manifest
    (name interpolates target repo so users with multiple analyzed
    repos can distinguish plugins).
- Write-if-absent for every one of the 10 targets — hand-edited
  shims are never overwritten.

#### Multi-repo registry (DEC-018)
- `~/.deepdive/registry.json` records every analyzed repo on
  successful extract. `forensic list` shows them.
- Multi-repo MCP serving deferred to v0.3 (the v0.2 tools take a
  single `graph_db_path` baked in at construction).

#### Markdown artifacts read from the graph (DEC-029, DEC-030)
- v0.2 emitters query LadybugDB via Cypher; the v0.1 in-memory
  NetworkX path is preserved as a fallback when the graph DB isn't
  populated. `build_graph_db` defaults to `True`.
- HOTPATHS "Dependency hot spots" + "Cross-file dependencies"
  rewritten to use symbol-level CALLS edges. MAP "Key definitions"
  rewritten with full qualified names + SymbolKind from the graph.
- AGENT_BRIEF "load-bearing file" + "central symbol" rules replaced
  in graph mode by a single "most-called symbol" rule when the
  symbol-level data is present.

#### File-role widening (DEC-021) and contributor pipeline fixes (DEC-022)
- Inventory classifies files into `{source, test, fixture,
  vendored, generated}`. Vendored detection via `third_party/`,
  `bundled/`, `external/`, `_vendor/`, embedded version strings;
  generated via `.g.dart`, `.freezed.dart`, `_pb.py`, `.generated.*`,
  plus a 512-byte content sniff for `GENERATED` / `DO NOT EDIT`
  markers. Both excluded from the symbol graph + PageRank.
- `git log --use-mailmap` for contributor canonicalization. `[bot]`
  and `-bot` accounts split into a separate `bots` list; ARCHAEOLOGY
  gains an optional "Automation" section.

#### Batched UNWIND graph writes (DEC-032)
- Every `LadybugStore.add_*` method has an `add_many_*` sibling
  using UNWIND-with-`$rows`, chunked at `_BATCH_SIZE=1000`. Single-
  row methods preserved for the MCP per-call store pattern and
  isolated tests.
- Direct bench: 1000 single-row CREATEs took 3188ms; UNWIND batched
  60ms (**53× speedup**). 10k MATCH+CREATE edges via UNWIND in
  550ms.
- `BuildGraphPhase.run` collects-then-batches — one `add_many_*`
  call per node/edge type. Sort order preserved across chunks; byte-
  identical graph hashes survive the refactor.

### Changed

- **`forensic extract` no longer runs Repomix by default (DEC-017,
  item 12).** The graph + MCP supersedes the role of "pack the repo
  for LLM." Repomix moved to `--legacy-repomix` flag. Node.js +
  Repomix installation no longer required for v0.2.
- **`ExtractConfig.build_graph_db` defaults to `True` (DEC-030).**
  Every extract writes both the graph DB and the markdown artifacts.
- **`_GIT_TIMEOUT_S` raised 300s → 600s** for cold-cache headroom on
  large repos.
- **`analyze_history` does one `git log --name-only` pass** when
  `include_commit_files=True` (the v0.2 default through
  BuildGraphPhase). Contributors + churn derived from the same walk.
  Old triple-pass behavior preserved for the v0.1 / `include_commit_
  files=False` callers.
- **Symbol-graph DEC-012 refinements:** production-only graph,
  language-scoped edges, local-definition shadowing — already in
  v0.1.1; documented here for completeness.

### Performance

Real-repo cold-extract numbers measured on commodity Windows 11
hardware (Intel, NVMe SSD):

| Repo | Files | Commits | Cold extract | Cache hit | MCP `context` | MCP `impact(depth=3)` |
|---|---|---|---|---|---|---|
| Omi (BasedHardware/omi) | 2103 src across 8 langs | ~18k | 930s | ≤5s | 146ms | 289ms |
| spring-petclinic | 30 Java | ~1.5k | 125s | ≤5s | <50ms | <50ms |
| tiny_fixture (v0.1) | 2 (Python+Dart) | small | 2.2s | <1s | <50ms | <50ms |

#### §5.2 budget relaxation — DEC-033

The PRD §5.2 cold-extract budgets shipped pre-implementation and were
authored against the v0.1 file-level orienter. With the v0.2 persistent
graph (8 languages × symbol-level CALLS / IMPORTS / EXTENDS / IMPLEMENTS
+ Commit / Author / TOUCHED_BY_COMMIT / AUTHORED_BY / CO_CHANGES_WITH
edges + per-edge confidence metadata), the v0.2.0 measured cold-extract
on Omi is **930s** vs. the original ≤120s budget. After DEC-032's
batched UNWIND writes (53× speedup on the LadybugDB side) and the
single-pass git-history walk in `analyze_history`, the dominant remaining
cost is the **sequential parse phase** (8 languages × ~5500 files,
one Tree-sitter parser at a time). Per **DEC-033** the cold-extract
budgets are relaxed to measured-honest numbers — Omi ≤1200s, GitNexus
≤2400s — while the **agent-facing budgets are unchanged**: cache-hit
≤5s, MCP `context` ≤500ms, MCP `impact(depth=3)` ≤2s. Those govern
the agent-loop UX and pass with order-of-magnitude headroom on the
same real graph.

**Parse-phase threading is the canonical v0.3 perf lever** — a per-language
ProcessPoolExecutor + sort-after-collect to preserve deterministic
golden fixtures. The v0.3 cycle baselines the new polyglot stress-test
set (Apache Superset, Backstage, Odoo) under threaded parse and either
tightens the cold-extract budget back toward §5.2's original 120s
intent or surfaces another lever (Tree-sitter parser pool reuse,
LadybugDB COPY FROM bulk-load).

### Dependencies

- **Added (core):**
  - `real-ladybug` ≥ 0.15.3 — embedded graph store (DEC-013). MIT.
  - `mcp` ≥ 1.27.1 — MCP server transport. MIT.
- **Added (`[graphiti]` extra, optional):**
  - `graphiti-core` ≥ 0.28 — opt-in agent-memory backend (DEC-019).
- **Removed:**
  - `kuzu` (was in v0.1's `[graphiti]` extra) — upstream archived
    after Apple acquisition Oct 2025; replaced by `real-ladybug`
    (DEC-013).
- **Demoted:**
  - Repomix is no longer auto-invoked (DEC-017); reachable via
    `--legacy-repomix` flag. Node.js + Repomix no longer required.

### Migration

For v0.1 users:
- The 5-artifact contract is **unchanged**: same filenames, same
  order, same `docs/codebase/` location.
- `forensic extract <repo>` now additionally produces
  `<repo>/.deepdive/graph.lbug` and 10 shim files (was 4 in v0.1).
  All shims write-if-absent.
- The first run is slower than v0.1 due to graph building; the
  graph is a one-time cost — subsequent queries via MCP are
  sub-second.
- v0.1 cache semantics preserved: `forensic extract` returns in
  ~seconds if no source changes are detected.
- Repomix users: pass `--legacy-repomix` to preserve the
  flatten-to-XML behavior.

## [0.1.0] — 2026-05-23

The structural orienter. Five markdown artifacts emitted from
Tree-sitter + ported Aider PageRank + plain-git history + Repomix
pack. Acceptance run on Omi (1,860 source files, 92.3s, $0, 100
tests passing). Three skills (`forensic-deepdive-extract`,
`-query`, `-update`). PageRank ported pure-Python (DEC-011). Symbol-
graph scoping refinements (DEC-012). Tag: `v0.1.0` (local, not
pushed).
