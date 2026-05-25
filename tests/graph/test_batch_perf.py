"""DEC-032 regression guard: batched UNWIND must beat single-row writes
by at least ~5×. The benchmark that motivated DEC-032 measured ~53×
(1000 single-row CREATEs took ~3.2s; UNWIND took ~60ms). A ≥5× floor
catches any future engine change that re-introduces the per-row
round-trip cost without locking us into a brittle absolute time budget.

Skipped in CI if the environment opts out via FORENSIC_SKIP_BENCH=1
(slow machines / CI runners can be ~10× slower than dev, and the
relative-speedup test is what matters)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from forensic_deepdive.graph import LadybugStore, Symbol, SymbolKind

pytestmark = pytest.mark.skipif(
    os.environ.get("FORENSIC_SKIP_BENCH") == "1",
    reason="bench skipped by FORENSIC_SKIP_BENCH=1",
)


def _symbol(qn: str) -> Symbol:
    return Symbol(
        qualified_name=qn,
        kind=SymbolKind.FUNCTION,
        file_path="bench.py",
        line_start=1,
        line_end=1,
        signature="",
    )


def test_unwind_beats_single_row_by_at_least_5x(tmp_path: Path) -> None:
    """Insert 500 symbols both ways. UNWIND must be ≥5× faster."""
    n = 500
    syms = [_symbol(f"bench.py::S{i:04d}") for i in range(n)]

    # Single-row path
    t0 = time.perf_counter()
    with LadybugStore(tmp_path / "single.lbug") as store:
        for s in syms:
            store.add_symbol(s)
    t_single = time.perf_counter() - t0

    # Batch (UNWIND) path
    t0 = time.perf_counter()
    with LadybugStore(tmp_path / "batch.lbug") as store:
        store.add_many_symbols(syms)
    t_batch = time.perf_counter() - t0

    # Avoid division by zero on absurdly fast hardware.
    assert t_batch > 0
    speedup = t_single / t_batch
    # Loose floor — the bench saw 53×; a 5× minimum is comfortable headroom
    # on slow CI runners. Below this means we lost the win.
    assert speedup >= 5.0, (
        f"UNWIND speedup regressed: {speedup:.1f}× "
        f"(single={t_single * 1000:.0f}ms, batch={t_batch * 1000:.0f}ms)"
    )
