"""Hybrid natural-language query over the code knowledge graph (DEC-038).

Three retrievers fused by Reciprocal Rank Fusion (k=60) then output-shaped:

* :mod:`.lexical` — always-on SQLite FTS5/BM25 sidecar (DEC-041). The
  deterministic, offline floor that replaces the v0.2 substring branch.
* structural — always-on, graph-grounded (lives in :mod:`.nl`): the lexical
  exact-name hits seed anchors, expanded one hop via CALLS/MEMBER_OF and ranked
  by CALLS in-degree.
* :mod:`.semantic` — opt-in offline ONNX embeddings behind the ``[semantic]``
  extra (DEC-042). Absent ⇒ two-retriever, said-so.

:mod:`.fuse` holds the RRF + shaping math; :mod:`.nl` is the orchestrator the
MCP ``query`` tool's NL branch calls.
"""

from __future__ import annotations

from forensic_deepdive.query.artifacts import (
    ARTIFACT_FILENAMES,
    QueryHit,
    QueryResult,
    query_artifacts,
    resolve_artifacts_dir,
)
from forensic_deepdive.query.fuse import RRF_K, reciprocal_rank_fusion, shape
from forensic_deepdive.query.lexical import (
    LexicalHit,
    LexicalIndex,
    SymbolRecord,
    build_lexical_index,
    build_lexical_index_from_store,
    lexical_index_path_for_db,
)
from forensic_deepdive.query.nl import hybrid_query

__all__ = [
    "ARTIFACT_FILENAMES",
    "RRF_K",
    "LexicalHit",
    "LexicalIndex",
    "QueryHit",
    "QueryResult",
    "SymbolRecord",
    "build_lexical_index",
    "build_lexical_index_from_store",
    "hybrid_query",
    "lexical_index_path_for_db",
    "query_artifacts",
    "reciprocal_rank_fusion",
    "resolve_artifacts_dir",
    "shape",
]
