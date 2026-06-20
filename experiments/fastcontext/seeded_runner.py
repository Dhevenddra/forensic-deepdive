"""Arm B — deepdive-seeded FastContext exploration (DEC-087, hardware-gated).

Wires the pure-static deepdive seed into FastContext's first-turn seeding seam
(Option 1, KICKOFF §6 / research.md Thread 1g): build the seed string from the
graph, then construct the FastContext agent with a ``system_prompt`` override that
embeds it. The two arms differ only by whether the seed is injected, so the
comparison is clean.

**This is hardware-gated and not runnable on a 4 GB GPU (see README.md).** It
requires:

1. An OpenAI-compatible endpoint serving **FC-4B-RL** (the trained explorer), e.g.::

       python -m sglang.launch_server --model-path microsoft/FastContext-1.0-4B-RL \\
           --tool-call-parser qwen --context-length 262144 --dtype bfloat16

   then ``export BASE_URL=… MODEL=microsoft/FastContext-1.0-4B-RL API_KEY=…``.
2. FastContext installed (MIT): ``uv pip install git+https://github.com/microsoft/fastcontext``.
3. For end-to-end resolution, Mini-SWE-Agent + a frontier **main-agent** endpoint +
   Docker (the SWE-bench harness). Build against the shipped ``--citation`` flag.

deepdive stays pure-static: the only thing this module adds to FastContext is the
seed *string*. No deepdive runtime imports an LLM.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from forensic_deepdive.seed import build_seed  # noqa: E402

_SEED_PREAMBLE = (
    "Before searching, consider this precomputed static-analysis context for the "
    "repository. Treat it as a prior to verify, not ground truth:\n\n{seed}\n"
)


def seeded_system_prompt(db_path: Path, issue_text: str, base_system_prompt: str) -> str:
    """Compose FastContext's base system prompt with the deepdive seed (Arm B).
    Pure-static — safe to call without any model present (it only reads the graph)."""
    seed = build_seed(db_path, issue_text)
    return base_system_prompt + "\n\n" + _SEED_PREAMBLE.format(seed=seed.to_prompt())


async def run_seeded(db_path: Path, issue_text: str, work_dir: Path, *, max_turns: int = 6) -> str:
    """Run deepdive-seeded FastContext on one issue, returning its ``<final_answer>``
    citation block. Requires FastContext + a served explorer endpoint."""
    try:
        from fastcontext.agent.agent_factory import make_fastcontext_agent  # type: ignore
        from fastcontext.agent.system import SYSTEM_PROMPT  # type: ignore
    except ImportError as exc:  # pragma: no cover — Arm B is hardware-gated
        raise SystemExit(
            "FastContext is not installed. Arm B needs it + a served FC-4B-RL "
            "endpoint (see this module's docstring). Use localization_eval.py "
            "--self-test for the model-free Arm A wiring check."
        ) from exc
    for var in ("BASE_URL", "MODEL", "API_KEY"):
        if not os.environ.get(var):
            raise SystemExit(f"Arm B needs ${var} set to the FC-4B-RL endpoint.")
    agent = make_fastcontext_agent(
        work_dir=str(work_dir),
        system_prompt=seeded_system_prompt(db_path, issue_text, SYSTEM_PROMPT),
    )
    return await agent.run(prompt=issue_text, max_turns=max_turns, citation=True)


if __name__ == "__main__":  # pragma: no cover — manual, hardware-gated
    import argparse

    ap = argparse.ArgumentParser(description="deepdive-seeded FastContext (Arm B)")
    ap.add_argument("--db", type=Path, required=True, help="extracted graph .lbug path")
    ap.add_argument("--issue", required=True, help="issue / task statement")
    ap.add_argument("--work-dir", type=Path, default=Path.cwd())
    ap.add_argument(
        "--print-seed-only", action="store_true", help="print the seed and exit (no model)"
    )
    args = ap.parse_args()
    if args.print_seed_only:
        print(build_seed(args.db, args.issue).to_prompt())
    else:
        print(asyncio.run(run_seeded(args.db, args.issue, args.work_dir)))
