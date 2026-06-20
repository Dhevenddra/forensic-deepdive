# experiments/fastcontext — the v0.8 usefulness experiment (DEC-087, GATE A)

This directory holds the FastContext usefulness experiment — the apparatus for the
DEC-081 publish blocker (*does deepdive's graph make an exploration agent localize /
resolve real issues measurably better?*). **It is experiment code, not shipped:** it
is excluded from the wheel (DEC-088) and is not CI-gated. The model / LLM / Docker /
SWE-bench machinery lives **only here** — `src/forensic_deepdive/` stays pure-static,
zero-LLM, zero-network (the DEC-009 floor). deepdive's contribution is the
pure-static, graph-derived **seed** in `forensic_deepdive.seed` (unit-tested in the
normal suite).

## The two arms

| Arm | What it measures | Needs |
|---|---|---|
| **A — standalone localization** | deepdive seed's **file-level localization F1** vs each SWE-bench instance's gold-patch files (FastContext's own standalone metric, ~73.7 F1 in their paper) | CPU only + the dataset + ability to clone the target repos. **Runnable without any model.** |
| **B — end-to-end resolution** | seeded-FastContext vs FastContext-alone: SWE-bench resolution rate + main-agent tokens, under Mini-SWE-Agent | A GPU that can serve **FC-4B-RL** at long context **and** a frontier **main-agent** API endpoint + credentials |

Arm A is the in-reach, model-free measurement and is the first real number. Arm B is
the headline end-to-end claim and is **gated on hardware** (see below).

## Hardware assessment (recorded honestly — DEC-087)

Measured on the development machine (2026-06-20):

- **GPU: NVIDIA RTX 3050 4GB Laptop (≈3.9 GB free).** This **cannot** serve FC-4B-RL
  for FastContext's intended workload. A 4B model is ~8 GB at bf16; ~2.3 GB as int4
  weights — which fits, but leaves only ~1.5 GB for the KV cache, i.e. a few thousand
  tokens of context. FastContext is built around long-context, multi-turn exploration
  (file reads up to 2000 lines, contexts to 262 K tokens), so a 4 GB card OOMs or is
  uselessly truncated. The FC-30B model is entirely out. **Substituting a smaller /
  different explorer model would not be FastContext** (it is a trained RL policy) — that
  would be a mislabeled result, so it is deliberately **not** done.
- **Docker 29.x: available.** The SWE-bench harness can be stood up.
- **HuggingFace: reachable.** Dataset + weights are accessible.
- **Frontier main-agent API: not provisioned here.** Mini-SWE-Agent's main agent needs a
  strong model (the paper used GPT-5.4 / GLM-5.1 / Kimi-K2.6) via an OpenAI-compatible
  endpoint with credentials.

**Conclusion:** Arm B (end-to-end resolution) requires a GPU with ≥ ~16 GB (to serve
FC-4B-RL at a useful context, per the research-note serving flags) **and** a frontier
main-agent endpoint. It is therefore **deferred to adequate hardware; GATE A remains
OPEN.** No end-to-end number is fabricated. Arm A is run instead as the first honest,
reproducible measurement of the seed's localization quality.

## Running Arm A — standalone localization (no model)

```bash
# Prove the wiring end-to-end on a bundled synthetic instance (no network, no dataset):
uv run --group experiment python experiments/fastcontext/localization_eval.py --self-test

# Real run on a SWE-bench Multilingual subset (needs the dataset + repo clone access):
uv run --group experiment python experiments/fastcontext/localization_eval.py \
    --dataset swe-bench-multilingual --n 50 --seed 0 --out experiments/fastcontext/arm_a.json
```

`localization_eval.py` reuses the unit-tested `build_seed` / `localization_score`; the
only experiment-specific glue is dataset iteration + per-instance repo checkout +
aggregation. The seed is pure-static, so the localization number is fully deterministic
for a fixed repo state + subset.

## Running Arm B — end-to-end (needs the GPU + main-agent endpoint)

`seeded_runner.py` wires FastContext's `make_fastcontext_agent(system_prompt=…)` with the
deepdive seed and runs it under Mini-SWE-Agent. See its module docstring for the SGLang
serve command, the `BASE_URL`/`MODEL`/`API_KEY` env contract, and the two-arm invocation.
Build against FastContext's shipped `--citation` flag (not the doc's `--format concise`,
a known doc/code discrepancy — research.md Thread 1).

## Vendoring

`microsoft/fastcontext` is **MIT** (repo + 4B/30B weights) — compatible with deepdive's
Apache-2.0. Pin it as an `experiment`-group git dependency or clone into `vendor/`
(gitignored); confirm `LICENSE` in-tree. Not vendored yet — Arm B is hardware-gated.
