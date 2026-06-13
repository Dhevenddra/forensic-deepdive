# Lane-(iii) memory hardening — v0.6 Step 6 acceptance (DEC-069)

The DEC-019 agent-insight store appends to a JSONL log and `recall_insights` does a linear
substring scan. Step 6 hardens lane (iii) — **local-first, zero-LLM** recall — with a
derived FTS5/BM25 index, content-hash dedup, and git shadow-ref portability, all behind the
**existing** `recall_insights`/`record_insight` tools (no 10th tool, no signature change).
The single sanctioned `mcp_server` touch.

## The keystone / floor held

`base.join`/`trace`/emit/`serve` untouched; the only `mcp_server` change is the
`recall_insights` backend (JSONL-scan → FTS5) + `record_insight` (dedup + index refresh +
shadow-ref sync). **Pure-static floor intact** — stdlib `sqlite3` FTS5/BM25 + git plumbing,
**zero runtime LLM** (the differentiator vs every general-memory tool, all of which require
an LLM/embeddings — research §6B).

## What landed

- **Derived FTS5/BM25 recall index** (`insights/recall_index.py`) reusing the DEC-041
  lexical sidecar (`<repo>/.forensic-deepdive/index/insights.db`). The JSONL stays
  **authoritative**; the index is derived + **rebuildable** (wipe-and-rebuild from the
  files, rebuilt-when-stale by mtime). Recall: symbol substring first (the DEC-019
  contract), then **BM25** over `symbol+claim+evidence` (camelCase-tokenized, so NL words
  match identifiers).
- **Content-hash dedup** (`Insight.content_hash()` = SHA-256 of
  `symbol|claim|evidence|verified_by`, the DEC-036 discipline): identical insights collapse
  to one; `record_insight` skips a duplicate (`deduplicated: True`).
- **Git shadow-ref** (`insights/shadow_ref.py`): sync the JSONL to
  `refs/forensic-deepdive/insights` via `hash-object`/`mktree`/`commit-tree`/`update-ref` —
  a non-branch/non-tag ref that carries insights with the repo (pushable/fetchable) without
  cluttering `git log` or the tree. The store **survives a clone** (fetch the ref → restore).

## Acceptance (`tests/test_insight_recall.py`, 9 tests)

| capability | proof |
|---|---|
| record → recall through FTS5/BM25 | `record_insight`→`recall_insights` round-trips; BM25 over the *claim* text surfaces an insight with no symbol substring match |
| symbol substring still works (DEC-019) | `recall("owner_list")` returns the symbol match first |
| `since` / `limit` honored | recency filter + cap |
| index rebuilds from files | delete `insights.db` → `ensure_recall_index` rebuilds from the JSONL → recall works again |
| dedup collapses identicals | two identical insights → one row (earliest kept); re-`record_insight` → `deduplicated: True` |
| survives a clone via the shadow-ref | save → `git clone` + fetch `refs/forensic-deepdive/insights` → `load_from_shadow_ref` → insight recovered in the clone |
| best-effort outside git | `save_to_shadow_ref` returns `False`, JSONL floor still works |

## §8.10 dogfooding (begins here)

From Step 6 onward the build records its own key insights into the hardened store — the
project uses its own memory layer during its own build. A round-trip on real v0.6 build
insights confirms the path end to end.

## Takeaway

`recall_insights` gains BM25 ranking, content-hash dedup, and clone-portability — entirely
on the pure-static floor (stdlib `sqlite3` + git plumbing, no LLM), behind the unchanged
9-tool / 5-artifact contract. forensic-deepdive is the code-domain-specialized,
LLM-free peer to the general-memory tools.
