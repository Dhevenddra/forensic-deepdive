"""v0.4 Item L acceptance-gate metrics dumper (local-only, not shipped).

Usage: uv run python scripts/gate_metrics.py <repo_path_or_lbug> [agent_brief_path]

Dumps the gate-relevant numbers for one repo's built graph: file/symbol counts,
CALLS confidence split, EXTENDS/IMPLEMENTS, ROUTES_TO + confidence split,
Endpoint count (located vs spec-only), and AGENT_BRIEF size. Deterministic;
read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from forensic_deepdive.graph import LadybugStore


def _one(store: LadybugStore, cypher: str) -> int:
    rows = list(store.query(cypher))
    return int(rows[0][0]) if rows and rows[0] and rows[0][0] is not None else 0


def _conf_split(store: LadybugStore, rel: str) -> dict[str, int]:
    out = {"EXTRACTED": 0, "INFERRED": 0, "AMBIGUOUS": 0}
    for conf, n in store.query(f"MATCH ()-[r:{rel}]->() RETURN r.confidence, count(r)"):
        out[conf] = int(n)
    return out


def main() -> None:
    arg = Path(sys.argv[1])
    db = arg if arg.name.endswith(".lbug") else arg / ".deepdive" / "graph.lbug"
    out: dict[str, object] = {"db": str(db), "exists": db.exists()}
    with LadybugStore(db) as s:
        out["files"] = _one(s, "MATCH (f:File) RETURN count(f)")
        out["files_by_role"] = {
            role: int(n)
            for role, n in s.query("MATCH (f:File) RETURN f.role, count(f)")
        }
        out["symbols"] = _one(s, "MATCH (n:Symbol) RETURN count(n)")
        out["calls"] = _conf_split(s, "CALLS")
        out["extends"] = _one(s, "MATCH ()-[r:EXTENDS]->() RETURN count(r)")
        out["implements"] = _one(s, "MATCH ()-[r:IMPLEMENTS]->() RETURN count(r)")
        out["endpoints"] = _one(s, "MATCH (e:Endpoint) RETURN count(e)")
        out["endpoints_spec_backed"] = _one(
            s, "MATCH (e:Endpoint) WHERE e.spec_backed = true RETURN count(e)"
        )
        out["handles"] = _one(s, "MATCH ()-[r:HANDLES]->() RETURN count(r)")
        out["calls_endpoint"] = _conf_split(s, "CALLS_ENDPOINT")
        out["routes_to"] = _conf_split(s, "ROUTES_TO")
        out["co_changes"] = _one(s, "MATCH ()-[r:CO_CHANGES_WITH]->() RETURN count(r)")
        # documented-but-unlocated: endpoints with no HANDLES
        out["endpoints_unlocated"] = _one(
            s,
            "MATCH (e:Endpoint) WHERE NOT EXISTS { MATCH (:Symbol)-[:HANDLES]->(e) } "
            "RETURN count(e)",
        )

    calls = out["calls"]
    total_calls = sum(calls.values()) or 1
    out["calls_ambiguous_pct"] = round(100.0 * calls["AMBIGUOUS"] / total_calls, 1)
    rt = out["routes_to"]
    out["routes_to_total"] = sum(rt.values())

    ab = None
    if len(sys.argv) > 2:
        ab = Path(sys.argv[2])
    else:
        cand = db.parent.parent / "docs" / "codebase" / "AGENT_BRIEF.md"
        if cand.exists():
            ab = cand
    if ab and ab.exists():
        out["agent_brief_bytes"] = ab.stat().st_size

    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
