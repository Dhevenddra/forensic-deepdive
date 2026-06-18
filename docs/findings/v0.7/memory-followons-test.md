# Memory lane-(iii) follow-ons — v0.7 Step 4 acceptance (DEC-075)

The #4 v0.6 carryover seed. DEC-069 hardened lane-(iii) recall (FTS5/BM25 over the
authoritative JSONL, content-hash dedup, a git shadow-ref for portability). DEC-075 adds the
three documented follow-ons — **semantic RRF fusion**, a **recency decay** score, and an
**explicit shadow-ref push** — all **LLM-free**, on the unchanged `recall_insights` tool
(no signature/shape change; `insights/*` + the CLI command only).

## (a) Semantic RRF over insights (opt-in, offline, LLM-free)

A parallel **semantic** vector index over the same insights (`insight_vectors.npy` +
`insight_ids.json`, ids = content hashes so it agrees with the FTS5 index on identity),
reusing the **DEC-042 ONNX embedder verbatim** — no new dependency, behind the same
`[semantic]` extra + `FORENSIC_SEMANTIC_MODEL`. At recall the semantic ranked list is fused
with BM25 via the **DEC-038 RRF**. Absent the extra/model, `insight_semantic_available()` is
`False` and recall stays FTS5-only — **a true no-op**: `search(semantic=True)` ≡
`search(semantic=False)` (asserted). The whole module imports without the extra (the DEC-042
floor). The real ONNX fusion runs only when a model is configured (the established
CI-untested-by-design pattern, like the code-search semantic tier).

## (b) Recency decay (stdlib Ebbinghaus / half-life)

A pure-stdlib `decay_weight(recorded_at) = 0.5 ** (age_days / half_life_days)` (no `py-fsrs`,
no LLM) applied to the **fuzzy recall tail** (BM25 + semantic), so a newer insight outranks
an equally- (or slightly-more-) relevant older one. Proven: with two insights matching a
query where the **older** is more lexically relevant, `decay=False` keeps the older first
(BM25 wins), while `decay=True` promotes the much-newer one. **Fail-open** — an unparseable
or future timestamp, or a non-positive half-life, returns weight `1.0` (recency never
*suppresses* an insight, only gently reorders).

**Contract preserved:** the symbol-substring **precise-lookup** path (DEC-019/069) is
**never decayed or fused** — an exact symbol hit stays first, newest-first, even when it is
the older insight (asserted). Decay/semantic apply only to the fuzzy tail.

## (c) Explicit shadow-ref push (`forensic insights push`)

`push_shadow_ref` publishes `refs/forensic-deepdive/insights` to a remote via git plumbing —
**explicit only, never automatic** (the never-push discipline extends to the insight ref).
The CLI command `forensic insights push [REPO] [--remote R] [--dry-run]` first refreshes the
ref from the current JSONL, then pushes. Proven against a local **bare remote**: `--dry-run`
reports "would push" and does **not** move the remote ref; a real push lands it (the remote
then has the ref). Best-effort, honest messages: outside a git repo → "not a git
repository"; no ref yet → "no insight ref to push"; unknown remote → "not found".

## Keystone / floor

`insights/*` (new `decay.py`, `semantic_recall.py`; extended `recall_index.py`,
`shadow_ref.py`) + the `recall_insights` backend + the CLI command + one wire in
`record_insight` — the **9-tool/5-artifact contract and the `recall_insights` signature are
unchanged**; `base.join`/`trace`/emit/`serve` untouched. Pure-static floor holds: decay is
stdlib, push is git plumbing, semantic is opt-in behind the existing extra (zero runtime
LLM). **Goldens byte-identical** (no extraction/emit change). Tests: `test_insight_memory_v07.py`
(11) — decay monotonicity/half-life/fail-open, decay tail-reorder, substring-first
preserved, semantic no-op + import-safety, and push dry-run/real/no-ref/no-remote/outside-git.

## Takeaway

The three lane-(iii) follow-ons land LLM-free on the frozen tool surface: recall now fuses
opt-in semantic similarity and weighs recency (without breaking the precise-lookup
contract), and insights can be **explicitly** published for cross-clone portability — the
agent-memory layer the differentiator depends on, still pure-static at the floor.
