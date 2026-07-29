"""Regenerate ``examples/<name>/`` with the current forensic-deepdive.

Extracts into a temp output dir — never into the source repo, so no shims are
dropped on the test checkouts — then copies back only the five contract
artifacts (plus ``AGENT_BRIEF_DEEP.md`` when overflow produced one).

Until v0.10 this lived at ``C:\\Dev\\scratch\\regen_examples.py``: unversioned,
on one machine, holding the eleven name→path mappings that the release depends
on. That made a release step a single-machine secret. It is in-repo now
(DEFERRED §1.4).

Usage::

    export FORENSIC_EXAMPLES_SRC=/c/Dev/scratch     # where the test repos live
    uv run python scripts/regen_examples.py          # all of them
    uv run python scripts/regen_examples.py omi superset
    uv run python scripts/regen_examples.py --list

Exit codes are **distinct**, which the previous version conflated into a bare 1
(a successful omi run exited 1 because a *different* directory was stale, so the
code had to be ignored and the output read by eye):

===  ===========================================================
0    every requested repo regenerated; hygiene sweep clean
1    at least one extract failed — the artifacts may be stale
2    every extract succeeded, but the hygiene sweep found a problem
3    usage error (unset source root, unknown example name)
===  ===========================================================

The sweep duplicates ``tests/test_release_hygiene.py`` (DEC-112) on purpose: the
suite is the enforcement, this is the immediate feedback while regenerating.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EXAMPLES = PROJECT / "examples"

ARTIFACTS = ("MAP.md", "HOTPATHS.md", "ARCHAEOLOGY.md", "MENTAL_MODEL.md", "AGENT_BRIEF.md")
BRIEF_CAP_BYTES = 5120
DEC_TOKEN = re.compile(r"DEC-\d{3}")

_SRC_ENV = "FORENSIC_EXAMPLES_SRC"

# examples/<name> -> path RELATIVE to the source root. Three are not the obvious
# <name>: they are subdirectories of a larger upstream sample repo.
SOURCES: dict[str, str] = {
    "fastapi": "fastapi",
    "gitnexus": "gitnexus",
    "grpc-route-guide": "grpc-examples/examples/python/route_guide",
    "hermes-agent": "hermes-agent",
    "jersey-helloworld": "jersey-examples/examples/helloworld",
    "nestjs-cats-app": "nest-samples/sample/01-cats-app",
    "omi": "omi",
    "rabbitmq-tutorials": "rabbitmq-tutorials",
    "ripgrep": "ripgrep",
    "spring-petclinic": "spring-petclinic",
    "superset": "superset",
}


def _source_root() -> Path | None:
    """The per-machine test-repo root, or None (with a message) if unusable.

    Returning rather than ``sys.exit``-ing keeps usage failures on exit code 3;
    ``sys.exit(str)`` would report them as 1, the "an extract failed" code.
    """
    raw = os.environ.get(_SRC_ENV)
    if not raw:
        print(
            f"error: ${_SRC_ENV} is not set.\n"
            "It must point at the directory holding the test repos, e.g.\n"
            f"    export {_SRC_ENV}=/c/Dev/scratch\n"
            "The mappings live in SOURCES; the root is per-machine on purpose.",
            file=sys.stderr,
        )
        return None
    root = Path(raw).expanduser()
    if not root.is_dir():
        print(f"error: ${_SRC_ENV} points at a non-directory: {root}", file=sys.stderr)
        return None
    return root


def regen(name: str, repo: Path) -> tuple[bool, str]:
    """Extract *repo* and copy its artifacts into ``examples/<name>/``."""
    if not repo.is_dir():
        return False, f"source missing: {repo}"
    dest = EXAMPLES / name
    with tempfile.TemporaryDirectory(prefix=f"fd-{name}-") as tmp:
        out = Path(tmp) / "codebase"
        proc = subprocess.run(
            [
                "uv", "run", "--project", str(PROJECT), "forensic", "extract",
                str(repo), "--output", str(out), "--force",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT),
        )  # fmt: skip
        if proc.returncode != 0:
            return False, f"extract failed rc={proc.returncode}: {proc.stderr[-300:]}"
        missing = [a for a in ARTIFACTS if not (out / a).exists()]
        if missing:
            return False, f"missing artifacts: {missing}"
        dest.mkdir(parents=True, exist_ok=True)
        for artifact in ARTIFACTS:
            shutil.copy2(out / artifact, dest / artifact)
        deep = out / "AGENT_BRIEF_DEEP.md"
        if deep.exists():
            shutil.copy2(deep, dest / "AGENT_BRIEF_DEEP.md")
    return True, f"ok (AGENT_BRIEF {(dest / 'AGENT_BRIEF.md').stat().st_size} b)"


def sweep() -> int:
    """Report ledger-token leaks and over-cap briefs. Returns the problem count."""
    problems = 0

    print("\n=== DEC-token sweep over examples/ ===")
    for path in sorted(EXAMPLES.rglob("*.md")):
        found = DEC_TOKEN.findall(path.read_text(encoding="utf-8", errors="replace"))
        if found:
            problems += 1
            print(f"  LEAK {path.relative_to(PROJECT)}: {sorted(set(found))}")
    print(f"  {problems} file(s) citing internal ledger IDs")

    print("\n=== AGENT_BRIEF 5 KB cap ===")
    for path in sorted(EXAMPLES.glob("*/AGENT_BRIEF.md")):
        size = path.stat().st_size
        over = size > BRIEF_CAP_BYTES
        problems += over
        print(f"  {'OVER CAP' if over else 'OK':8} {size:6d}  {path.parent.name}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("names", nargs="*", help="example names (default: all)")
    parser.add_argument("--list", action="store_true", help="list known examples and exit")
    args = parser.parse_args()

    if args.list:
        for name, rel in SOURCES.items():
            print(f"  {name:20} {rel}")
        return 0

    unknown = [n for n in args.names if n not in SOURCES]
    if unknown:
        print(f"error: unknown example(s): {unknown}\nknown: {sorted(SOURCES)}", file=sys.stderr)
        return 3

    root = _source_root()
    if root is None:
        return 3
    failures = []
    for name in args.names or list(SOURCES):
        ok, msg = regen(name, root / SOURCES[name])
        print(f"[{'OK ' if ok else 'FAIL'}] {name}: {msg}", flush=True)
        if not ok:
            failures.append(name)

    problems = sweep()

    if failures:
        print(f"\n{len(failures)} extract(s) FAILED: {failures}", file=sys.stderr)
        return 1
    if problems:
        print(f"\nextracts fine, but {problems} hygiene problem(s) remain", file=sys.stderr)
        return 2
    print("\nall good")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
