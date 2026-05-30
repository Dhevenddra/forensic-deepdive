"""Opt-in offline ONNX semantic retriever (DEC-042).

The only tier that needs a model, and the only one behind the ``[semantic]``
extra (``onnxruntime`` + ``tokenizers`` + ``numpy``). Everything here lazy-imports
those inside functions, so importing this module never hard-requires the extra —
the pure-static floor (DEC-009) is preserved.

No network, no API. v0.3 does **not** auto-download the model: the path is
resolved from ``FORENSIC_SEMANTIC_MODEL``. If the runtime or the model is absent,
:func:`semantic_available` returns ``False`` and the orchestrator runs with two
retrievers and says so.

Storage: a numpy memmap ``vectors.npy`` + parallel ``ids.json`` under the index
dir (sorted-qn order, matching the lexical index). Query: brute-force cosine
(HNSW is a later optimization — research §3 / PRD §4.5).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from forensic_deepdive.query.lexical import SymbolRecord

_VECTORS_NAME = "vectors.npy"
_IDS_NAME = "ids.json"
_MODEL_ENV = "FORENSIC_SEMANTIC_MODEL"


@dataclass(frozen=True, slots=True)
class SemanticHit:
    qualified_name: str
    score: float  # cosine similarity in [-1, 1]; higher is better


def _runtime_importable() -> bool:
    """True iff the ``[semantic]`` extra is installed."""
    import importlib.util

    return all(
        importlib.util.find_spec(mod) is not None for mod in ("onnxruntime", "tokenizers", "numpy")
    )


def _model_dir() -> Path | None:
    """Resolve the local model directory, or ``None`` (no auto-download)."""
    raw = os.environ.get(_MODEL_ENV)
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() else None


def semantic_available(index_dir: Path | None = None) -> bool:
    """True iff semantic search can run: the extra is importable, a local model
    is configured, and (when *index_dir* is given) a vector index exists."""
    if not _runtime_importable() or _model_dir() is None:
        return False
    if index_dir is not None:
        return (Path(index_dir) / _VECTORS_NAME).is_file()
    return True


# ---------------------------------------------------------------------------
# Embedding (lazy — only reachable when the extra is present)
# ---------------------------------------------------------------------------


class _Embedder:
    """Thin ONNX wrapper. Constructed only when the extra + model are present."""

    def __init__(self, model_dir: Path) -> None:
        import onnxruntime as ort  # noqa: PLC0415 — lazy by design
        from tokenizers import Tokenizer  # noqa: PLC0415

        self._tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self._session = ort.InferenceSession(
            str(model_dir / "model.onnx"), providers=["CPUExecutionProvider"]
        )

    def encode(self, texts: Sequence[str]) -> Any:
        import numpy as np  # noqa: PLC0415

        encs = [self._tokenizer.encode(t) for t in texts]
        max_len = max((len(e.ids) for e in encs), default=1)
        ids = np.zeros((len(encs), max_len), dtype=np.int64)
        mask = np.zeros((len(encs), max_len), dtype=np.int64)
        for i, e in enumerate(encs):
            ids[i, : len(e.ids)] = e.ids
            mask[i, : len(e.ids)] = e.attention_mask
        inputs = {"input_ids": ids, "attention_mask": mask}
        out = self._session.run(None, inputs)[0]  # (n, seq, dim)
        # Mean-pool over tokens with the attention mask.
        m = mask[:, :, None].astype(out.dtype)
        pooled = (out * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        return pooled / np.clip(norms, 1e-9, None)


# ---------------------------------------------------------------------------
# Build / search
# ---------------------------------------------------------------------------


def build_semantic_index(index_dir: Path, records: Iterable[SymbolRecord]) -> Path | None:
    """Embed each record's content and write ``vectors.npy`` + ``ids.json``.

    Returns the index dir, or ``None`` if the extra/model is unavailable (the
    caller treats that as "semantic stays off").
    """
    if not semantic_available():
        return None
    import numpy as np  # noqa: PLC0415

    from forensic_deepdive.query.lexical import _content_for  # noqa: PLC0415

    model_dir = _model_dir()
    assert model_dir is not None  # guaranteed by semantic_available()
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    ordered = sorted(records, key=lambda r: r.qualified_name)
    if not ordered:
        return None
    embedder = _Embedder(model_dir)
    vectors = embedder.encode([_content_for(r) for r in ordered]).astype("float32")
    np.save(index_dir / _VECTORS_NAME, vectors)
    (index_dir / _IDS_NAME).write_text(
        json.dumps([r.qualified_name for r in ordered]), encoding="utf-8"
    )
    return index_dir


class SemanticIndex:
    """Read-only handle over a built vector index. Brute-force cosine."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = Path(index_dir)

    def search(self, query: str, *, limit: int = 50) -> list[SemanticHit]:
        if not semantic_available(self.index_dir):
            return []
        import numpy as np  # noqa: PLC0415

        model_dir = _model_dir()
        assert model_dir is not None
        ids: list[str] = json.loads((self.index_dir / _IDS_NAME).read_text(encoding="utf-8"))
        vectors = np.load(self.index_dir / _VECTORS_NAME, mmap_mode="r")
        q = _Embedder(model_dir).encode([query])[0]
        sims = vectors @ q  # vectors are L2-normalized, so dot == cosine
        order = np.argsort(-sims)[:limit]
        return [SemanticHit(qualified_name=ids[i], score=float(sims[i])) for i in order]
