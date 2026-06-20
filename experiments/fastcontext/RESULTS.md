# FastContext usefulness experiment — RESULTS (DEC-087, GATE A)

**Status: PARTIAL — apparatus complete and self-test green; the headline
measurements are PENDING hardware. GATE A remains OPEN. No number here is
fabricated.**

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

## Arm A — standalone localization F1 (PENDING the dataset run)

The harness is ready; the real number needs a SWE-bench Multilingual subset + repo
clone access (CPU-only, no model). Reproduce:

```
uv sync --group experiment
uv run python experiments/fastcontext/localization_eval.py \
    --dataset princeton-nlp/SWE-bench_Multilingual --n 50 --seed 0 \
    --out experiments/fastcontext/arm_a.json
```

| metric | value | n | seed | date |
|---|---|---|---|---|
| mean file-localization F1 | _PENDING_ | — | — | — |
| mean precision | _PENDING_ | | | |
| mean recall | _PENDING_ | | | |

Baseline to compare against: FastContext's trained standalone ~73.7 file-level F1 on
SWE-bench Verified (their paper). Note this is the **seed's** localization, a prior —
not the trained explorer's, and not end-to-end resolution.

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

**OPEN.** The reproducible apparatus exists and the model-free wiring is proven, but
no end-to-end Q2 measurement has been produced. Per KICKOFF §5 / DEC-081, `uv publish`
(DEC-092) stays blocked until either (a) Arm B lands a real end-to-end number, or
(b) the team explicitly decides to publish on the assisted-analysis value with **no
autonomous-execution overclaim** and moves the seeding measurement to v0.9 — recording
that decision here. This file is updated, never massaged, when a run completes.
