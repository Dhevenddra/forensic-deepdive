# ARCHITECTURE.md

> The "why" behind the design. If `DECISIONS.md` is the index, this is the long-form. Read when revisiting a major design call.

## System summary

`forensic-deepdive` is a four-layer pipeline that produces five durable markdown artifacts. Each layer is an independent module; each artifact is a separate emitter. Tools are composed, not built.

## Data flow

```
Repo path / URL
    │
    ▼
Layer 0: Inventory
    │  ├── Languages, LOC, build files
    │  ├── Tooling sniff (pyproject.toml, package.json, pubspec.yaml, Cargo.toml)
    │  └── Decide Graphiti threshold (2-of-5)
    │
    ▼
Layer 1: Static                  Layer 2: Flatten              Layer 3a: Graphiti (above threshold)
    │  ├── Tree-sitter parse      │  ├── Repomix --compress     │  ├── Ingest commits as time-bounded episodes
    │  ├── Build symbol graph     │  └── yek --fast (v0.2)      │  ├── Ingest PRs as episodes
    │  ├── PageRank w/ personalization                          │  ├── Ingest issues as episodes
    │  ├── ast-grep hotpath queries                             │  └── Custom entity types
    │  └── ty diagnostics (Python ≥30%)                         │
    │                                                          Layer 3b: plain-git (below threshold)
    │                                                              ├── git log, git shortlog
    │                                                              └── GitHub REST: PRs, issues, releases
    │
    ▼
Layer 4: Emitter
    │  ├── MAP.md
    │  ├── HOTPATHS.md
    │  ├── ARCHAEOLOGY.md
    │  ├── MENTAL_MODEL.md
    │  └── AGENT_BRIEF.md  ──┬─► CLAUDE.md (shim)
    │                       ├─► AGENTS.md (shim)
    │                       ├─► .cursor/rules/codebase.mdc (shim)
    │                       └─► .continue/rules/codebase.md (shim)
```

## Tool decisions table

| Tool | Verdict | Why |
|---|---|---|
| Tree-sitter (`tree-sitter-language-pack`) | **Adopt** | 305 grammars, every Omi-stack language. |
| Aider repo-map (port the PageRank algorithm) | **Adopt — port, don't depend** | Battle-tested; NetworkX is tiny; tags.scm queries lift cleanly. |
| ast-grep | **Adopt** | Cross-language HOTPATHS.md tracing. |
| Repomix (default Layer 2) | **Adopt** | `--compress` + secretlint + AI-friendly output. |
| yek (`--fast` backend) | **v0.2** | 230× faster on Next.js; git-history weighting. |
| ty (Astral) | **Optional Python enricher** | 10-60× faster than mypy/Pyright per Astral's launch blog. |
| Ruff | **Adopt** | Read pyproject.toml → bake lint policy into AGENT_BRIEF.md. |
| Graphiti | **Defer to v0.2, gate behind threshold** | Bi-temporal + hybrid retrieval; Apache-2.0; Kuzu embedded backend. |
| DeepWiki / DeepWiki-Open | **Skip as dep, study as reference** | Different architectural bet (RAG vs PageRank). |
| Graphify | **Optional v0.2 backend (`--with-graphify`)** | Multi-modal enrichment when available; stole confidence-tagging idea. |
| stack-graphs | **Skip** | Archived Sep 9, 2025. |
| SCIP / LSIF | **Defer to v2.0** | Per-language build integration too costly for v0.1. |
| semgrep | **Skip** | Security tool, restrictive rules license. |
| Plain git + GitHub REST | **Build (v0.1 Layer 3 default)** | Below Graphiti threshold, sufficient. |
| Claude Code Skills | **Adopt as primary distribution** | Skill-first hybrid. |
| MCP server | **v0.2 secondary** | For query-after-ingest. |
| Python `typer` CLI | **Build — load-bearing** | Non-Claude harnesses get equal footing. |

## Distribution — skill+CLI hybrid (defended against MCP-as-primary)

Five reasons MCP-as-primary loses:

1. **Daemon overhead.** "Run `forensic .`, five files commit" beats "configure your MCP client to point at port 9876."
2. **Per-tool surface area.** Each MCP client has its own JSON config. Artifacts read natively by all of them.
3. **Skill installation is one line** (`claude /plugin install forensic-deepdive`).
4. **CLI is load-bearing for non-Claude users.** Aider, Cursor, Continue, Cline, Codex CLI — all benefit from a CLI regardless of harness.
5. **MCP is right for query-after-ingest.** A thin MCP server is legitimate v0.2 secondary. Not primary.

## Skill split — three skills

Anthropic's docs identify the description as the load-bearing selector. Multi-intent descriptions lose to three sharp single-intent ones.

- `forensic-deepdive-extract` — first-time analysis.
- `forensic-deepdive-query` — answering questions from existing artifacts.
- `forensic-deepdive-update` — incremental refresh after churn.

## Local-only mode — co-equal, not bolted-on

- Layers 1, 2, and Layer-3-plain-git are **fully offline**. Zero changes.
- **Graphiti local-mode (v0.2):** point at Ollama via OpenAI-compatible API. Graphiti's README explicitly warns: *"Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini). Using other services may result in incorrect output schemas and ingestion failures. This is particularly problematic when using smaller models."* So local-mode ships:
  - **Curated model list:** Qwen2.5-Coder-32B and Llama-3.3-70B for sufficient-VRAM machines.
  - **`small-local` fallback:** Qwen2.5-Coder-7B for laptops with ~16GB RAM, accepting degraded archaeology accuracy.
  - **Graceful per-episode skip-and-log** when structured-output parsing fails.
- **Backend for Graphiti in local mode:** Kuzu (embedded — no server, no Docker) by default.
- **Trigger:** `--local` flag, env var `FORENSIC_DEEPDIVE_LOCAL=1`, or auto-detected when no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` and Ollama is reachable on `localhost:11434`.

## Cost / token budget for a 500k-LOC repo

Reference: Repomix on `GoogleCloudPlatform/python-docs-samples` (109M chars, 56M tokens raw → ~2.8M tokens with `--compress`). 500k LOC scales linearly down.

| Layer | Operation | Tokens | Cost (Sonnet) | Cost (Haiku) | Cost (Ollama) |
|---|---|---|---|---|---|
| 1 | Tree-sitter + PageRank | 0 | $0 | $0 | $0 |
| 2 | Repomix `--compress` | 0 | $0 | $0 | $0 |
| 3 plain-git | git + REST | 0 | $0 | $0 | $0 |
| 3 Graphiti | ~500 episodes × ~3k in + ~600 out | 1.5M in / 0.3M out | ~$8 | ~$1 | $0 |
| 4 | Optional MENTAL_MODEL.md prose | ~50k in / 20k out | ~$0.50 | ~$0.07 | $0 |
| **Total cloud default** | | | **~$8–10** | **~$1** | **$0** |

Well under the $50 ceiling. Re-runs are cheap due to SHA256-based caching.

## Update semantics — staleness gating, not blind regeneration

- **File-level**: SHA256 cache in `.forensic-deepdive/cache/file_hashes.json`. Only changed files are re-parsed.
- **Section-level:**
  - MAP.md invalidates if any top-50 PageRank node changed.
  - HOTPATHS.md invalidates if any active ast-grep query's match-set changed.
  - ARCHAEOLOGY.md appends incrementally since `last_ingest_commit_sha`.
  - MENTAL_MODEL.md is the stickiest — regenerated only on ≥20% symbol-graph churn or `--force-mental-model`. New hires need stability.
  - AGENT_BRIEF.md invalidates on dependency-manifest changes (`pyproject.toml`, `package.json`, `pubspec.yaml`, `Cargo.toml`), `.github/workflows/` changes, hand-written `CONVENTIONS.md`/`STYLE.md` changes, or top-10 PageRank node changes.
- Every artifact carries a `<!-- forensic-deepdive: generated 2026-05-20T14:32Z from commit abc1234 -->` header for audit.

## Polyglot strategy — unified abstraction across C/Python/Dart/Swift/Rust/TS

The abstraction is the **`Symbol`**, normalized across all 305 Tree-sitter grammars via per-language `tags.scm` queries (Aider's pattern, ported):

```python
@dataclass
class Symbol:
    kind: Literal["function", "class", "method", "interface", "struct", "enum", "module", "trait"]
    name: str
    file: Path
    line: int
    signature: str       # synthesized from CST
    language: str
    references: list["SymbolRef"]
```

For polyglot coupling points (Omi's BLE Audio Streaming Service UUID `19B10000-E8F2-537E-4F6C-D104768A1214` referenced from C firmware, Dart mobile, Swift desktop), we add synthetic **`cross_language_concept`** symbols whenever the same string literal (UUID, env var, API endpoint, MCP method name) appears in ≥2 languages. These get an outsized PageRank boost — they are the *actual* interface boundaries.

## Confidence taxonomy (stolen from Graphify, DEC-007)

Every emitted rule and every fact in MAP/HOTPATHS/ARCHAEOLOGY/MENTAL_MODEL carries one of:

- **EXTRACTED** — deterministic from AST or git. Confidence implicitly 1.0.
- **INFERRED** — LLM-synthesized with explicit confidence 0.0–1.0.
- **AMBIGUOUS** — flagged for human review; not actionable without verification.

v0.1 emits everything EXTRACTED (no LLM rule synthesis yet). v0.2 adds INFERRED for MENTAL_MODEL.md prose and AMBIGUOUS for cases where evidence is conflicting.

## Anti-patterns this architecture explicitly rejects

- **Stuffing the whole codebase into LLM context.** Distillation over retention.
- **Treating the README as ground truth.** README documents intent; code documents reality.
- **One mega-prompt that does everything.** Small composable tools, orchestrated.
- **Embedding-based RAG as the primary retrieval mechanism.** PageRank over symbol graph is deterministic, debuggable, and respects code structure. Embeddings are v2.0 considered-but-not-decided.
- **MCP server as primary distribution.** Daemon dependency kills cross-tool adoption.
- **One monolithic SKILL.md.** Description-based selection fails on multi-intent skills.
