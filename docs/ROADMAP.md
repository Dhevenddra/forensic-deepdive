# ROADMAP.md

> Phased build plan. v0.1 next weekend; v0.2 by end of May / early June; v1.0 mid-July to early-August 2026.

Budget: 10–15 hrs/week through end of May 2026; less after. $0 hardware. <$30/month cloud.

## v0.1 — runnable next weekend (target May 24-25, 2026)

Layers 1+2+4 + AGENT_BRIEF.md emitter end-to-end on Omi, cloud-default. Plain-git Layer 3 stub.

| Day | Hours | Deliverable |
|---|---|---|
| Wed | 3 | `typer` CLI skeleton; inventory; Tree-sitter integration via `tree-sitter-language-pack`. |
| Thu | 3 | Port Aider's `RepoMap` (PageRank + tags.scm); test on tiny fixture. |
| Fri | 3 | Repomix subprocess backend; SHA256 cache layer. |
| Sat | 5 | Emitter: MAP.md, HOTPATHS.md (ast-grep), AGENT_BRIEF.md template renderer. |
| Sun | 5 | Plain-git ARCHAEOLOGY.md; basic MENTAL_MODEL.md emitter; shim writers; end-to-end on Omi. |
| Mon | 2 | Three skills committed; README; v0.1 git tag. |

**v0.1 done = :**
- `uv tool install -e .` works on macOS + Linux.
- `forensic --version` returns `0.1.0`.
- `forensic extract ~/code/omi` finishes in ≤15 min for ≤$5.
- Five artifacts emit with `<!-- generated -->` headers.
- AGENT_BRIEF.md ≤5kb (`wc -c` check).
- Three skills load in Claude Code.
- `examples/omi/AGENT_BRIEF.md` committed.
- `pytest -x` passes; `ruff check` clean.

**Explicitly out of v0.1:** Graphiti, MCP server, Ollama detection, yek backend, incremental update, ImportFloodStrategy, full confidence taxonomy, Graphify backend, ty/ruff enrichers, second worked example.

## v0.2 — this month (target end-of-May / early June 2026)

| Week | Hours | Deliverable |
|---|---|---|
| 1 | 10 | Graphiti integration (`graphiti-core` ≥0.28). Kuzu embedded backend default; FalkorDB Docker option. Custom entity types. |
| 2 | 10 | Local-only co-equal: Ollama detection, LM Studio detection, curated structured-output model list, graceful per-episode skip on parse failure. |
| 3 | 10 | yek backend (`--fast`). Incremental update (`forensic update`). Section-level staleness gating. Confidence-tagged edges (full taxonomy). |
| 4 | 10 | Second worked example: **Home Assistant** (>21,000 contributors per GitHub State of the Octoverse 2024; first commit Sep 17, 2013; Python-dominant). MCP server v1. Optional `--with-graphify` backend. ImportFloodStrategy. ty + ruff Python enrichers. |

**v0.2 done = :**
- `forensic extract . --with-graphiti --local` runs end-to-end on Omi using Ollama only, $0 API cost, ≤4 hours.
- `forensic update` correctly section-stales.
- Second worked example committed.
- MCP server tested with Claude Desktop config.
- README has copy-pasteable local-only section.

## v1.0 — publishable (target mid-July to early-August 2026)

### Hardening
- Diagnostics modeled on ty's bar (designed for both humans and agents).
- Graceful GitHub-API rate-limit fallback.
- Graceful Ollama-structured-output failure.

### Documentation
- Full ARCHITECTURE.md in-repo (already drafted).
- Populated comparison table page.
- Local-only quick-start page.
- Stress-test report on Omi + Home Assistant.
- Gallery of ≥4 worked examples (Omi, Home Assistant, Supabase, Pydantic).

### Positioning
- README finalized.
- One launch blog post.

### Launch criteria (all must pass)
1. Three independent users run it on a repo Dhevenddra doesn't control and call the AGENT_BRIEF.md useful (screenshot or testimonial).
2. ≥4 worked examples committed.
3. Comparison table populated (Aider repo-map, Sourcegraph, DeepWiki, Cursor @codebase, Continue codebase indexing, Graphify).
4. Apache-2.0 license.
5. README structure complete.
6. CI passing (ruff lint, ty type-check, pytest on Python 3.11/3.12/3.13).
7. Issue templates + CONTRIBUTING.md.
8. Three skill descriptions tuned — verified ≥85% correct-skill selection on a held-out variant set of user questions.

### Channels
- HN Show.
- Anthropic Discord #show-and-tell.
- Twitter/X 60-second screen capture.
- DeepWiki badge on our own repo.

## Risks & mitigations

- **Time:** v0.1 at 8-10 hrs is tight; pad with Monday. v0.2 at ~40 hrs is realistic over 4 weeks.
- **Money:** at ~$1/extract on Haiku and ~30 dev-extracts/month, we hit ~$30. Mitigation: local-only must be co-equal so dev doesn't burn budget.
- **Hardware ($0 budget):** Qwen2.5-Coder-32B Q4 needs ~20GB unified memory. Ship a `small-local` mode using Qwen2.5-Coder-7B for dev on smaller machines, accepting degraded Graphiti accuracy.
- **Graphiti structured-output local-mode** is the biggest risk. Mitigations: curated model list + graceful per-episode skip + prompt schemas tuned for minimum complexity.

## Thresholds that would change the plan

- **`forensic-deepdive` PyPI name taken** → fall back to `forensic-cli`.
- **Graphiti local-mode failure rate >30% on Qwen2.5-Coder-32B in v0.2 week 2** → degrade to cloud-only in v0.2; ship plain-git as local default; document.
- **AGENT_BRIEF.md ignored >1 in 5 sessions in v1.0 user testing** → shrink to <3kb; split into AGENT_BRIEF_CORE.md + AGENT_BRIEF_DEEP.md.
- **PageRank symbol-collision <60% precision on Omi's MAP.md** → bring ImportFloodStrategy forward into v0.1.
