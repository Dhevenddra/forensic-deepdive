"""Arm A — standalone file-localization eval for the deepdive seed (DEC-087).

Measures how well the pure-static seed localizes the files a real issue touches:
for each SWE-bench instance, extract the repo at its base commit, build the seed
from the issue text, and score the seed's candidate files against the gold patch's
files (FastContext's own standalone metric). Model-free, deterministic, CPU-only.

This is experiment code (not shipped, not CI-gated). Its load-bearing primitives —
``build_seed`` and ``localization_score`` — are unit-tested in the normal suite
(``tests/test_seed.py``); the glue here is dataset iteration + per-instance repo
checkout + aggregation.

    # Prove the full wiring on a bundled synthetic instance (no network/dataset):
    uv run --group experiment python experiments/fastcontext/localization_eval.py --self-test

    # Real run on a SWE-bench subset (needs `datasets` + repo-clone access):
    uv run --group experiment python experiments/fastcontext/localization_eval.py \
        --dataset SWE-bench/SWE-bench_Multilingual --n 50 --seed 0 \
        --out experiments/fastcontext/arm_a.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

# Allow running as a plain script (no package install) by adding src/ to the path.
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from forensic_deepdive.pipeline import (  # noqa: E402
    ExtractConfig,
    PipelineRunner,
    default_phases,
)
from forensic_deepdive.seed import build_seed, localization_score  # noqa: E402

_DIFF_PATH_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def files_from_patch(patch: str) -> set[str]:
    """The set of repo-relative files a unified-diff patch modifies (the gold
    localization target). Reads the ``+++ b/<path>`` headers; ``/dev/null``
    (pure deletions) is skipped."""
    return {m.group(1).strip() for m in _DIFF_PATH_RE.finditer(patch) if m.group(1) != "/dev/null"}


def score_instance(
    repo_path: Path, issue_text: str, gold_files: set[str], *, work_dir: Path
) -> dict:
    """Extract *repo_path*, build the seed for *issue_text*, and score its
    candidate files against *gold_files*. Returns the localization_score dict
    plus the predicted files (for inspection)."""
    db_path = work_dir / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo_path.resolve(),
        output_dir=work_dir / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    seed = build_seed(db_path, issue_text)
    score = localization_score(seed.candidate_files, gold_files)
    score["predicted_files"] = seed.candidate_files
    score["gold_files"] = sorted(gold_files)
    return score


def run_self_test() -> int:
    """Exercise the full per-instance flow on a bundled synthetic instance — no
    network, no dataset, no model. Proves the harness wiring end-to-end."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        repo = tmp / "shop"
        repo.mkdir()
        (repo / "payment.py").write_text(
            "def process_payment(order):\n    return _charge(order)\n\n\n"
            "def _charge(order):\n    return order\n"
        )
        (repo / "auth.py").write_text("def login(user):\n    return True\n")
        score = score_instance(
            repo,
            "process_payment double-charges on refund",
            {"payment.py"},
            work_dir=tmp / "work",
        )
        print(json.dumps(score, indent=2))
        ok = score["f1"] > 0.0 and "payment.py" in score["predicted_files"]
        print("SELF-TEST:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


def _checkout(repo_url: str, base_commit: str, dest: Path) -> None:
    """Fetch ONLY *base_commit*'s tree into *dest* (Arm A real run). A shallow
    per-commit fetch (`git init` + `fetch --depth 1 <commit>`) avoids cloning the
    full history of large monorepos — we only need the working tree at that commit
    to extract + localize. Falls back to a shallow full clone + checkout if the
    server rejects fetch-by-sha."""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    try:
        subprocess.run(
            ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", repo_url, base_commit],
            check=True,
        )
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["git", "clone", "-q", repo_url, str(dest)], check=True)
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", base_commit], check=True)


def run_swebench(dataset: str, n: int, seed: int, out: Path, repos: set[str] | None = None) -> int:
    """Real Arm-A run over a SWE-bench subset. Requires the `datasets` package and
    network access to fetch the target repos. Writes a JSON report and prints the
    aggregate mean localization F1 — the first honest seed-quality number.

    *repos* (optional) restricts to a set of ``owner/name`` repos — useful for a
    tractable run on smaller repos rather than the large monorepos in the set."""
    try:
        import random

        from datasets import load_dataset  # type: ignore[import-untyped]
    except ImportError:
        print(
            "ERROR: `datasets` not installed. Add the experiment group:\n"
            "  uv sync --group experiment\n"
            "or run with --self-test (no dataset needed).",
            file=sys.stderr,
        )
        return 2

    rows = list(load_dataset(dataset, split="test"))
    if repos:
        rows = [r for r in rows if r.get("repo") in repos]
    random.Random(seed).shuffle(rows)
    rows = rows[:n]
    results: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for i, inst in enumerate(rows):
            gold = files_from_patch(inst.get("patch", ""))
            if not gold:
                continue  # unscoreable (e.g. pure deletion) — skip honestly
            issue = inst.get("problem_statement", "") or inst.get("issue", "")
            repo_url = f"https://github.com/{inst['repo']}.git"
            dest = base / f"inst_{i}"
            try:
                _checkout(repo_url, inst["base_commit"], dest)
                score = score_instance(dest, issue, gold, work_dir=base / f"work_{i}")
            except Exception as exc:  # record failures honestly, don't silently drop
                results.append({"instance_id": inst.get("instance_id", i), "error": str(exc)})
                continue
            score["instance_id"] = inst.get("instance_id", i)
            results.append(score)
            print(f"[{i + 1}/{len(rows)}] {score.get('instance_id')}: F1={score['f1']:.3f}")

    scored = [r for r in results if "f1" in r]
    summary = {
        "dataset": dataset,
        "n_requested": n,
        "n_scored": len(scored),
        "seed": seed,
        "mean_f1": statistics.mean(r["f1"] for r in scored) if scored else 0.0,
        "mean_precision": statistics.mean(r["precision"] for r in scored) if scored else 0.0,
        "mean_recall": statistics.mean(r["recall"] for r in scored) if scored else 0.0,
        "results": results,
    }
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nmean file-localization F1 = {summary['mean_f1']:.4f} over {len(scored)} instances")
    print(f"report -> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="deepdive seed localization eval (Arm A)")
    parser.add_argument("--self-test", action="store_true", help="run the bundled wiring check")
    parser.add_argument("--dataset", default="SWE-bench/SWE-bench_Multilingual")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=Path("experiments/fastcontext/arm_a.json"))
    parser.add_argument(
        "--repos", default="", help="comma-separated owner/name filter (e.g. tractable small repos)"
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_test()
    repos = {r.strip() for r in args.repos.split(",") if r.strip()} or None
    return run_swebench(args.dataset, args.n, args.seed, args.out, repos)


if __name__ == "__main__":
    raise SystemExit(main())
