"""Tests for the v0.2 pipeline DAG runner.

DEC-014. Covers topology validation (missing deps, cycles, duplicates),
typed-output retrieval, seed-outputs, and the phase-output-type check.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from forensic_deepdive.pipeline import (
    Context,
    DAGCycleError,
    DuplicatePhaseError,
    ExtractConfig,
    MissingDependencyError,
    Phase,
    PhaseOutputTypeError,
    PipelineRunner,
)

# ---------------------------------------------------------------------------
# Tiny stub phases for runner-shape tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Out:
    value: str


def _make_phase(
    phase_name: str,
    deps: tuple[str, ...] = (),
    *,
    output_type: type = _Out,
    body: object = None,
) -> Phase:
    """Build a one-off Phase subclass on the fly. Tests use this so the
    runner-shape suite doesn't have to import the v0.1 phases (which have
    real side effects)."""

    body_value = body if body is not None else _Out(value=phase_name)
    expected_type = output_type

    class _Stub(Phase):
        name = phase_name
        depends_on = deps
        output_type = expected_type

        def run(self, ctx: Context):  # type: ignore[override]
            return body_value() if callable(body_value) else body_value

    _Stub.__name__ = f"{phase_name.title()}Phase"
    return _Stub()


def _config(tmp_path: Path) -> ExtractConfig:
    return ExtractConfig(repo_path=tmp_path, output_dir=tmp_path / "out")


# ---------------------------------------------------------------------------
# Construction-time validation
# ---------------------------------------------------------------------------


def test_runner_validates_dag_at_construction():
    # Topology errors must surface as soon as the runner is built, not
    # halfway through a run.
    with pytest.raises(MissingDependencyError, match="ghost"):
        PipelineRunner([_make_phase("a", deps=("ghost",))])


def test_runner_detects_cycles():
    with pytest.raises(DAGCycleError):
        PipelineRunner(
            [
                _make_phase("a", deps=("b",)),
                _make_phase("b", deps=("a",)),
            ]
        )


def test_runner_detects_self_cycle():
    with pytest.raises(DAGCycleError, match="a"):
        PipelineRunner([_make_phase("a", deps=("a",))])


def test_runner_rejects_duplicate_phase_names():
    with pytest.raises(DuplicatePhaseError, match="dup"):
        PipelineRunner([_make_phase("dup"), _make_phase("dup")])


def test_subclass_without_output_type_rejected():
    with pytest.raises(TypeError, match="output_type"):

        class _Bad(Phase):
            name = "bad"
            # No output_type — must raise.

            def run(self, ctx):
                return None


def test_subclass_without_name_is_treated_as_abstract():
    # Useful for shared base classes; only the leaf with ``name`` must
    # declare ``output_type``.
    class _Mid(Phase):
        def run(self, ctx):  # pragma: no cover — abstract intermediate
            return None

    assert not hasattr(_Mid, "name")


# ---------------------------------------------------------------------------
# Topo order
# ---------------------------------------------------------------------------


def test_topo_order_respects_dependencies():
    runner = PipelineRunner(
        [
            _make_phase("emit", deps=("a", "b")),
            _make_phase("a"),
            _make_phase("b"),
        ]
    )
    names = [p.name for p in runner.order]
    assert names.index("a") < names.index("emit")
    assert names.index("b") < names.index("emit")


def test_topo_order_is_deterministic_across_ties():
    # When several phases are simultaneously ready, the runner preserves the
    # order they were declared in. The DAG below has 'a' and 'b' both with
    # zero in-degree; declaration order says a first.
    p_a = _make_phase("a")
    p_b = _make_phase("b")
    p_c = _make_phase("c", deps=("a", "b"))
    runner = PipelineRunner([p_a, p_b, p_c])
    assert [p.name for p in runner.order] == ["a", "b", "c"]

    # Swap declaration order — topo order swaps too.
    runner2 = PipelineRunner([p_b, p_a, p_c])
    assert [p.name for p in runner2.order] == ["b", "a", "c"]


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


def test_run_populates_context_with_typed_outputs(tmp_path):
    runner = PipelineRunner(
        [
            _make_phase("a", body=_Out(value="from-a")),
            _make_phase("b", body=_Out(value="from-b")),
        ]
    )
    ctx = runner.run(_config(tmp_path))
    assert ctx.outputs["a"] == _Out(value="from-a")
    assert ctx.outputs["b"] == _Out(value="from-b")


def test_downstream_phase_reads_upstream_output(tmp_path):
    captured: dict[str, str] = {}

    class _Up(Phase):
        name = "up"
        output_type = _Out

        def run(self, ctx):
            return _Out(value="hello")

    class _Down(Phase):
        name = "down"
        depends_on = ("up",)
        output_type = _Out

        def run(self, ctx):
            captured["read"] = ctx.get(_Up).value
            return _Out(value="ok")

    PipelineRunner([_Up(), _Down()]).run(_config(tmp_path))
    assert captured["read"] == "hello"


def test_wrong_return_type_raises_phase_output_type_error(tmp_path):
    @dataclass(frozen=True, slots=True)
    class _Expected:
        x: int

    class _Bad(Phase):
        name = "bad"
        output_type = _Expected

        def run(self, ctx):
            return _Out(value="wrong type")

    with pytest.raises(PhaseOutputTypeError, match="_Expected"):
        PipelineRunner([_Bad()]).run(_config(tmp_path))


# ---------------------------------------------------------------------------
# Seed outputs (used by the cache-hit short-circuit in run_extract)
# ---------------------------------------------------------------------------


def test_seed_outputs_skip_phase_execution(tmp_path):
    ran: list[str] = []

    class _A(Phase):
        name = "a"
        output_type = _Out

        def run(self, ctx):
            ran.append("a")
            return _Out(value="default")

    class _B(Phase):
        name = "b"
        depends_on = ("a",)
        output_type = _Out

        def run(self, ctx):
            ran.append("b")
            return _Out(value=ctx.get(_A).value)

    ctx = PipelineRunner([_A(), _B()]).run(
        _config(tmp_path),
        seed_outputs={"a": _Out(value="seeded")},
    )
    # _A skipped, _B saw the seeded value.
    assert ran == ["b"]
    assert ctx.outputs["b"] == _Out(value="seeded")


def test_seed_outputs_do_not_mutate_caller_dict(tmp_path):
    seed = {"a": _Out(value="x")}
    PipelineRunner([_make_phase("a")]).run(_config(tmp_path), seed_outputs=seed)
    assert seed == {"a": _Out(value="x")}


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


def test_context_has_returns_true_only_after_phase_runs(tmp_path):
    class _A(Phase):
        name = "a"
        output_type = _Out

        def run(self, ctx):
            return _Out(value="x")

    ctx = Context(config=_config(tmp_path))
    assert not ctx.has(_A)
    ctx.put("a", _Out(value="x"))
    assert ctx.has(_A)


def test_context_get_missing_raises_keyerror(tmp_path):
    class _A(Phase):
        name = "a"
        output_type = _Out

        def run(self, ctx):
            return _Out(value="x")

    with pytest.raises(KeyError, match="a"):
        Context(config=_config(tmp_path)).get(_A)
