"""Opt-in offline ONNX semantic recall over insights (DEC-075, v0.7 Step 4).

Lane-(iii) memory follow-on. The FTS5/BM25 recall index (DEC-069) is lexical; this adds a
parallel **semantic** vector index over the same insights so a query with *no lexical
overlap* ("auth flow" → an insight about "login token validation") can still surface. It
reuses the existing DEC-042 ``[semantic]`` ONNX embedder verbatim — **LLM-free, offline,
opt-in** (behind the same extra + ``FORENSIC_SEMANTIC_MODEL``); absent ⇒ recall stays
FTS5-only and says nothing (the pure-static floor holds, DEC-009).

The recall backend (``InsightRecallIndex``) fuses this with BM25 via the DEC-038 RRF. Each
insight's vector id is its **content hash** (the DEC-069 dedup key), so the two indexes
agree on identity. Vectors co-locate with the FTS5 ``.db`` under ``index/``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from forensic_deepdive.insights.store import Insight
from forensic_deepdive.query.lexical import _tokenize

_VECTORS_NAME = "insight_vectors.npy"
_IDS_NAME = "insight_ids.json"


def insight_semantic_dir(index_path: Path) -> Path:
    """The semantic-vector dir derived from the FTS5 index path (co-located under
    ``index/``)."""
    return Path(index_path).parent


def _content_for(ins: Insight) -> str:
    """The embedded text — symbol + claim + evidence, tokenized (camelCase-split,
    lowercased; the DEC-041/069 tokenizer) so identifiers and prose embed coherently."""
    return " ".join(_tokenize(ins.symbol) + _tokenize(ins.claim) + _tokenize(ins.evidence))


def insight_semantic_available(index_dir: Path) -> bool:
    """True iff the ``[semantic]`` extra + a configured model + a built insight-vector
    file are all present (so semantic recall can actually run)."""
    from forensic_deepdive.query.semantic import semantic_available

    return semantic_available() and (Path(index_dir) / _VECTORS_NAME).is_file()


def build_insight_semantic_index(index_dir: Path, insights: Iterable[Insight]) -> Path | None:
    """Embed each (content-hash-deduped) insight and write ``insight_vectors.npy`` +
    ``insight_ids.json`` (ids = content hashes, sorted for determinism). Returns the dir, or
    ``None`` when the extra/model is unavailable (semantic recall simply stays off). Reuses
    the DEC-042 embedder — no new code path, no new dependency."""
    from forensic_deepdive.query.semantic import _Embedder, _model_dir, semantic_available

    if not semantic_available():
        return None
    import numpy as np  # noqa: PLC0415 — lazy: only when the extra is present

    by_hash: dict[str, Insight] = {}
    for ins in insights:
        by_hash.setdefault(ins.content_hash(), ins)
    if not by_hash:
        return None
    ordered = sorted(by_hash.items(), key=lambda kv: kv[0])
    model_dir = _model_dir()
    assert model_dir is not None  # guaranteed by semantic_available()
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    vectors = (
        _Embedder(model_dir).encode([_content_for(ins) for _, ins in ordered]).astype("float32")
    )
    np.save(index_dir / _VECTORS_NAME, vectors)
    (index_dir / _IDS_NAME).write_text(json.dumps([h for h, _ in ordered]), encoding="utf-8")
    return index_dir


def ensure_insight_semantic_index(index_path: Path, jsonl_path: Path) -> Path | None:
    """Rebuild the insight-vector index from the authoritative JSONL when the ``[semantic]``
    extra+model are present and the vectors are missing/stale (DEC-075). A no-op (returns
    ``None``) without the extra — the FTS5 lexical index always works. Mirrors
    ``ensure_recall_index`` but is opt-in + best-effort (embedding is the only costly bit)."""
    from forensic_deepdive.query.semantic import semantic_available

    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists() or not semantic_available():
        return None
    index_dir = insight_semantic_dir(index_path)
    vectors = index_dir / _VECTORS_NAME
    stale = (not vectors.is_file()) or (jsonl_path.stat().st_mtime > vectors.stat().st_mtime)
    if not stale:
        return index_dir
    from forensic_deepdive.insights.jsonl_store import JsonlInsightStore

    return build_insight_semantic_index(index_dir, JsonlInsightStore(jsonl_path).iter_all())


class InsightSemanticIndex:
    """Read-only handle over the built insight-vector index. Brute-force cosine (the
    DEC-042 approach); returns content hashes ranked by similarity (best first)."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = Path(index_dir)

    def search(self, query: str, *, limit: int = 50) -> list[str]:
        """Ranked content hashes most semantically similar to *query* (best first), or
        ``[]`` when semantic recall is unavailable."""
        if not insight_semantic_available(self.index_dir):
            return []
        import numpy as np  # noqa: PLC0415

        from forensic_deepdive.query.semantic import _Embedder, _model_dir

        model_dir = _model_dir()
        assert model_dir is not None
        ids: list[str] = json.loads((self.index_dir / _IDS_NAME).read_text(encoding="utf-8"))
        vectors = np.load(self.index_dir / _VECTORS_NAME, mmap_mode="r")
        q = _Embedder(model_dir).encode([query])[0]
        sims = vectors @ q  # L2-normalized rows → dot == cosine
        order = np.argsort(-sims)[:limit]
        return [ids[i] for i in order]
