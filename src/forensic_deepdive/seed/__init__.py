"""Pure-static, graph-derived context seeding (DEC-087).

The deepdive contribution to the FastContext usefulness experiment: a
**zero-LLM, zero-network** seed payload built entirely from the existing graph
(the always-on lexical + structural NL query, the CALLS in-degree hot spots) that
an external exploration agent can be primed with. The LLM / model endpoint that
consumes this seed lives only in ``experiments/fastcontext/`` — never here — so
the DEC-009 pure-static floor is preserved.

Public surface:

- :func:`build_seed` — ``(db_path, issue_text) -> RepoSeed``.
- :class:`RepoSeed` / :class:`SeedCandidate` — the structured payload, with
  :meth:`RepoSeed.to_prompt` rendering the FastContext seeding string.
- :func:`localization_score` — set-based precision/recall/F1 of a predicted file
  set against a gold file set (FastContext's standalone file-localization metric).
"""

from __future__ import annotations

from forensic_deepdive.seed.fastcontext_seed import (
    RepoSeed,
    SeedCandidate,
    build_seed,
    localization_score,
)

__all__ = ["RepoSeed", "SeedCandidate", "build_seed", "localization_score"]
