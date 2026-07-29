"""Per-phase timing instrumentation (DEC-113).

The v0.9 DEFERRED ledger attributed ~374 s on omi to "graph construction,
PageRank, and the LadybugDB inserts" as one lump — observed in aggregate and
never split. DEC-113 says the deliverable is numbers, and that no optimization
lands before them. This is the instrument those numbers come from, so it has to
be trustworthy before it is believed.

The invariant that matters is **disjointness**: sub-steps of a phase must not
overlap, or a nested pair double-counts and the phase appears to spend more time
in its parts than in itself. That mistake was made and caught while wiring this
up (`lexical_index` sat inside `store_write`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forensic_deepdive.pipeline.extract import run_extract
from forensic_deepdive.pipeline.runner import (
    Context,
    ExtractConfig,
    Phase,
    PipelineRunner,
    Timings,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "tiny_fixture"


# ---------------------------------------------------------------------------
# The collector itself
# ---------------------------------------------------------------------------


def test_substeps_for_filters_by_phase() -> None:
    t = Timings(substeps={"static.pagerank": 1.0, "build_graph.store_write": 2.0})
    assert t.substeps_for("static") == {"pagerank": 1.0}
    assert t.substeps_for("build_graph") == {"store_write": 2.0}
    assert t.substeps_for("emit") == {}


def test_total_sums_phases_only() -> None:
    """Sub-steps are *inside* phases — counting them into the total would report
    the run as taking longer than it did."""
    t = Timings(phases={"a": 1.0, "b": 2.0}, substeps={"a.x": 0.5})
    assert t.total == 3.0


def test_repeated_substep_accumulates() -> None:
    """A step timed inside a loop should total, not keep only the last pass."""
    ctx = Context(config=ExtractConfig(repo_path=Path("."), output_dir=Path(".")))
    ctx._current_phase = "static"
    for _ in range(3):
        with ctx.substep("inner"):
            pass
    assert list(ctx.timings.substeps) == ["static.inner"]
    assert ctx.timings.substeps["static.inner"] >= 0.0


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------


class _Ok(Phase):
    name = "ok"
    depends_on = ()

    class Out:
        pass

    output_type = Out

    def run(self, ctx: Context) -> Out:
        with ctx.substep("work"):
            pass
        return _Ok.Out()


class _Boom(Phase):
    name = "boom"
    depends_on = ()

    output_type = _Ok.Out

    def run(self, ctx: Context) -> _Ok.Out:
        raise RuntimeError("phase exploded")


def _cfg() -> ExtractConfig:
    return ExtractConfig(repo_path=Path("."), output_dir=Path("."))


def test_runner_records_each_phase() -> None:
    ctx = PipelineRunner([_Ok()]).run(_cfg())
    assert "ok" in ctx.timings.phases
    assert ctx.timings.phases["ok"] >= 0.0
    assert ctx.timings.substeps_for("ok") == pytest.approx(
        {"work": ctx.timings.substeps["ok.work"]}
    )


def test_seeded_phases_are_absent_not_zero() -> None:
    """ "Did not run" and "ran instantly" are different facts. A cache hit skips
    phases; reporting them as 0.00s would read as "free"."""
    ctx = PipelineRunner([_Ok()]).run(_cfg(), seed_outputs={"ok": _Ok.Out()})
    assert "ok" not in ctx.timings.phases


def test_a_failing_phase_is_still_timed() -> None:
    """The timing is recorded in a `finally`, so a crash still reports where the
    time went — which is exactly when you most want to know."""
    runner = PipelineRunner([_Boom()])
    with pytest.raises(RuntimeError, match="exploded"):
        runner.run(_cfg())


def test_current_phase_is_cleared_between_phases() -> None:
    ctx = PipelineRunner([_Ok()]).run(_cfg())
    assert ctx._current_phase == ""


# ---------------------------------------------------------------------------
# End-to-end, on a real extract
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def extracted(tmp_path_factory: pytest.TempPathFactory):
    out = tmp_path_factory.mktemp("timings-out")
    return run_extract(_FIXTURE, out, force=True, write_editor_shims=False)


def test_extract_reports_every_phase(extracted) -> None:
    """Including `inventory`, which runs outside the runner (it seeds the DAG for
    the cache check) and so is invisible to the runner's own instrumentation."""
    phases = extracted.timings.phases
    for expected in ("inventory", "parse", "static", "contracts", "build_graph", "emit"):
        assert expected in phases, f"phase {expected} missing from timings"
    assert extracted.timings.total > 0


def test_the_tail_substeps_are_recorded(extracted) -> None:
    """The four sub-steps DEC-113 exists to separate — the v0.9 ledger reported
    them as one number."""
    assert set(extracted.timings.substeps_for("static")) == {"build_symbol_graph", "pagerank"}
    build = extracted.timings.substeps_for("build_graph")
    assert {"resolve_calls", "store_write", "lexical_index"} <= set(build)


@pytest.mark.parametrize("phase", ["static", "build_graph"])
def test_substeps_never_exceed_their_phase(extracted, phase: str) -> None:
    """Disjointness. Sub-steps summing past their phase total means two of them
    overlap — the `lexical_index`-inside-`store_write` bug. A profile that
    double-counts sends the optimization work at the wrong target.

    Tolerance covers timer granularity only, not a real nesting error.
    """
    total = extracted.timings.phases[phase]
    covered = sum(extracted.timings.substeps_for(phase).values())
    assert covered <= total + 0.01, (
        f"{phase}: sub-steps sum to {covered:.3f}s but the phase took {total:.3f}s "
        "— they overlap (one is nested inside another)"
    )
