# FastContext usefulness experiment — RESULTS (DEC-087, GATE A)

**Status: PARTIAL — apparatus complete; Arm A (localization) has a real PILOT
number (n=8); the headline end-to-end Arm B remains PENDING hardware. GATE A
remains OPEN. No number here is fabricated or massaged.**

This file is the binding record for the DEC-081 publish blocker. It will be filled
with the real numbers when each arm is run; until then it states exactly what is
proven, what is pending, and why.

## What is proven now (in-sandbox, model-free)

- **The deepdive seed-builder** (`forensic_deepdive.seed.build_seed`) is implemented,
  pure-static (zero-LLM, zero-network), and unit-tested in the normal suite
  (`tests/test_seed.py`): an issue text localizes to the correct file via the
  always-on lexical + structural query, and the seed renders deterministically.
- **The localization metric** (`localization_score`) is implemented and unit-tested
  (precision / recall / F1 set math).
- **The Arm-A harness** (`localization_eval.py`) runs end-to-end on a bundled
  synthetic instance:

  ```
  $ uv run python experiments/fastcontext/localization_eval.py --self-test
  ... "f1": 1.0, "predicted_files": ["payment.py"], "gold_files": ["payment.py"]
  SELF-TEST: PASS
  ```

## Arm A — standalone localization (PILOT run, 2026-06-21)

A real, reproducible pilot of the **pure-static seed's** standalone file-localization
against SWE-bench Multilingual gold patches. Model-free, CPU-only. Reproduce:

```
uv sync --group experiment
uv run python experiments/fastcontext/localization_eval.py \
    --dataset SWE-bench/SWE-bench_Multilingual \
    --repos axios/axios,immutable-js/immutable-js,burntsushi/ripgrep \
    --n 8 --seed 0 --out experiments/fastcontext/arm_a.json
```

| metric | value | n | seed | date |
|---|---|---|---|---|
| mean file-localization F1 | **0.108** | 8 | 0 | 2026-06-21 |
| mean precision | 0.062 | 8 | 0 | |
| mean recall (recall@10) | **0.438** | 8 | 0 | |
| gold file present in the seed's candidates | **4 / 8** | 8 | 0 | |

**Honest reading.** The F1 is low (0.108) and *expected to be*: the seed is a
**zero-shot static prior** (lexical + structural matching of the issue text, no
semantic tier, no model), not a trained explorer — FastContext's trained standalone
~73.7 F1 is not a fair comparator for a prior. The seed returns up to 10 candidate
files while gold is usually 1–2, so precision (hence F1) is structurally capped even
on a hit; the **seed-relevant** metric is **recall@10** — does the right file land in
the candidate set the explorer would narrow from. Here it does **~44%** of the time
(4/8 instances) on this subset.

**Caveats (do not over-read).** Small **n=8 pilot**, not the full 300; a **3-repo
subset** (axios/immutable-js/ripgrep — JS/TS/Rust, chosen for tractable shallow
fetches, not the large apache/* monorepos in the set); this is the **seed's**
standalone localization, **NOT** FastContext's and **NOT** end-to-end resolution; the
seed ran **degraded** (no `[semantic]` extra). This is a signal that the static prior
alone is a *weak* localizer — whether *seeding it into FastContext* helps end-to-end
is the Arm-B question, still open. A larger multilingual run (`--n 50+`, the full repo
spread, on a machine with a clone/compute budget) is the documented next step.

## Arm B — end-to-end resolution (DEFERRED — hardware-gated)

Seeded-FastContext vs FastContext-alone, SWE-bench resolution rate + main-agent token
consumption, under Mini-SWE-Agent.

**Not run.** The development GPU is an RTX 3050 4GB, which cannot serve FC-4B-RL at a
useful context (see README.md hardware assessment), and no frontier main-agent
endpoint is provisioned. Requires a GPU with ≥ ~16 GB + a frontier main-agent API +
Docker. Deferred to adequate hardware.

| arm | resolution rate | main-agent tokens | n | date |
|---|---|---|---|---|
| FastContext-alone | _PENDING_ | _PENDING_ | — | — |
| deepdive-seeded | _PENDING_ | _PENDING_ | — | — |

## GATE A verdict

**OPEN.** The apparatus is proven and Arm A now has a real pilot number (the static
seed is a *weak* standalone localizer — recall@10 ~0.44 on an n=8 subset), but the
**headline Q2 — does deepdive-seeding make an explorer resolve real issues better
end-to-end — has NOT been measured** (Arm B is hardware-gated). Per KICKOFF §5 /
DEC-081, `uv publish` (DEC-092) stays blocked until either (a) Arm B lands a real
end-to-end number, or (b) the team explicitly decides to publish on the
assisted-analysis value with **no autonomous-execution overclaim** and moves the
seeding measurement to v0.9 — recording that decision here. The Arm-A pilot does
**not** by itself unlock publish: a weak standalone localizer could still help or hurt
seeding, which only Arm B settles. This file is updated, never massaged, when a run
completes.
