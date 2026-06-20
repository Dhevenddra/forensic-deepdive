"""Build a pure-static, graph-derived seed for an exploration agent (DEC-087).

``build_seed(db_path, issue_text)`` maps an issue/task statement to the files and
symbols deepdive's graph thinks are most relevant — composing the existing
always-on retrievers (no new analysis, no LLM, no network):

1. **Issue → candidates.** The natural-language hybrid query (DEC-038/041/084 —
   lexical FTS5/BM25 + structural CALLS-proximity, semantic tier optional) ranks
   symbols for the issue text. After DEC-084 the lexical floor name-matches
   inflected query terms, so this works in the pure-static ``degraded`` mode.
2. **Candidate files.** The ranked symbols' files, de-duplicated in rank order —
   the localization *prediction* scored against a gold patch's files.
3. **Hot spots.** The most-depended-on symbols by distinct-caller in-degree
   (DEC-085) — global priors an explorer should treat with care.

The result renders to a compact string (:meth:`RepoSeed.to_prompt`) suitable for
FastContext's query / ``system_prompt`` seeding seam. The model that consumes it
is external (``experiments/fastcontext/``); this module stays zero-LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forensic_deepdive.query import hybrid_query

_CONF_RANK = {"EXTRACTED": 3, "INFERRED": 2, "AMBIGUOUS": 1}


@dataclass(frozen=True, slots=True)
class SeedCandidate:
    """One graph symbol surfaced into the seed."""

    qualified_name: str
    file: str
    line: int
    kind: str
    confidence: str

    @property
    def short_name(self) -> str:
        return self.qualified_name.rsplit("::", 1)[-1]


@dataclass(frozen=True, slots=True)
class RepoSeed:
    """The pure-static seed payload for one (repo, issue) pair."""

    issue_excerpt: str
    candidate_files: list[str]
    candidate_symbols: list[SeedCandidate]
    hotpaths: list[SeedCandidate]
    degraded: bool

    def to_prompt(self) -> str:
        """Render the FastContext seeding string. Deterministic; safe to embed in
        a query or a ``system_prompt`` override. Empty sections are omitted so a
        seed for an unlocalizable issue degrades to just the global hot spots."""
        lines: list[str] = [
            "## Repository context (precomputed by static analysis — verify before relying on it)",
        ]
        if self.candidate_files:
            lines.append("")
            lines.append("Likely-relevant files for this task:")
            lines += [f"- {f}" for f in self.candidate_files]
        if self.candidate_symbols:
            lines.append("")
            lines.append("Likely-relevant symbols:")
            lines += [
                f"- `{c.short_name}` — {c.file}:{c.line} [{c.confidence}]"
                for c in self.candidate_symbols
            ]
        if self.hotpaths:
            lines.append("")
            lines.append("Most-depended-on symbols (change signatures with care):")
            lines += [f"- `{c.short_name}` — {c.file}:{c.line}" for c in self.hotpaths]
        if self.degraded:
            lines.append("")
            lines.append(
                "_Note: semantic tier not installed — these candidates are lexical + "
                "structural only._"
            )
        return "\n".join(lines)


def build_seed(
    db_path: Path,
    issue_text: str,
    *,
    max_files: int = 10,
    max_symbols: int = 10,
    max_hotpaths: int = 8,
    semantic: bool = False,
) -> RepoSeed:
    """Compose the existing graph retrievers into a :class:`RepoSeed` for
    *issue_text* against the graph at *db_path*. Pure-static and deterministic
    (the underlying queries are). ``semantic`` opts into the ONNX tier when the
    ``[semantic]`` extra is installed; the default stays on the zero-dependency
    lexical + structural floor."""
    pool = max(max_files, max_symbols) * 3
    result = hybrid_query(db_path, issue_text, semantic=semantic, limit=pool)
    hits = result.get("results", [])

    candidate_symbols: list[SeedCandidate] = [
        SeedCandidate(
            qualified_name=h["qualified_name"],
            file=h["file"],
            line=int(h["line"]),
            kind=h["kind"],
            confidence=h["confidence"],
        )
        for h in hits[:max_symbols]
    ]

    # Candidate files: each hit's file, de-duplicated in rank order. This is the
    # localization prediction scored against a gold patch's touched files.
    seen_files: set[str] = set()
    candidate_files: list[str] = []
    for h in hits:
        fp = h["file"]
        if fp and fp not in seen_files:
            seen_files.add(fp)
            candidate_files.append(fp)
        if len(candidate_files) >= max_files:
            break

    hotpaths = _hotpaths(db_path, max_hotpaths)

    return RepoSeed(
        issue_excerpt=issue_text.strip()[:280],
        candidate_files=candidate_files,
        candidate_symbols=candidate_symbols,
        hotpaths=hotpaths,
        degraded=bool(result.get("degraded", True)),
    )


def _hotpaths(db_path: Path, limit: int) -> list[SeedCandidate]:
    """Top symbols by distinct-caller CALLS in-degree (DEC-085 honest count) —
    the repo's load-bearing callees, a global prior for any task."""
    from forensic_deepdive.graph import LadybugStore  # local import: avoid cycle

    try:
        with LadybugStore(db_path) as store:
            rows = list(
                store.query(
                    "MATCH (caller:Symbol)-[r:CALLS]->(callee:Symbol) "
                    "RETURN callee.qualified_name, callee.file_path, callee.line_start, "
                    "callee.kind, count(DISTINCT caller) AS callers "
                    "ORDER BY callers DESC, callee.qualified_name "
                    f"LIMIT {int(limit)}"
                )
            )
    except Exception:  # pragma: no cover — degrade to no hot spots if the db is unusable
        return []
    return [
        SeedCandidate(
            qualified_name=qn,
            file=fp,
            line=int(ls),
            kind=kind,
            confidence="INFERRED",  # "load-bearing" is a ranking interpretation (DEC-015)
        )
        for qn, fp, ls, kind, _callers in rows
    ]


def localization_score(predicted_files: list[str], gold_files: set[str]) -> dict[str, float]:
    """Set-based precision / recall / F1 of a predicted file set against the gold
    files a patch actually touched — FastContext's standalone file-localization
    metric. Pure function (no I/O, no model). Paths are compared verbatim, so the
    caller must normalize them to the same root first.

    Returns ``{precision, recall, f1, true_positives, predicted, gold}``. With no
    gold files the task is unscoreable → all zeros (the caller should skip it)."""
    pred_set = set(predicted_files)
    gold = set(gold_files)
    if not gold:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "true_positives": 0.0,
            "predicted": float(len(pred_set)),
            "gold": 0.0,
        }
    tp = len(pred_set & gold)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(gold)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": float(tp),
        "predicted": float(len(pred_set)),
        "gold": float(len(gold)),
    }
