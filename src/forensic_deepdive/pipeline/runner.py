"""DAG runner for the forensic-deepdive extract pipeline.

DEC-014. Three pieces:

* :class:`Phase` — the ABC every stage subclasses. Declares a ``name`` (used by
  the topo sort), a tuple of ``depends_on`` names, an ``output_type`` dataclass
  (the typed contract with downstream phases), and a ``run(ctx)`` method.
* :class:`Context` — carries the immutable :class:`ExtractConfig` and a
  name-keyed map of phase outputs. Downstream phases read upstream outputs via
  :meth:`Context.get`, which is typed against the upstream phase's
  ``output_type``.
* :class:`PipelineRunner` — topologically sorts a list of phases (Kahn's
  algorithm), validates the DAG once at construction, and runs phases
  sequentially. Supports pre-seeded outputs so the cache-hit short-circuit
  can skip phases without restructuring the runner.

The runner is deliberately sequential in v0.2. PRD §4.3 leaves room for
per-language parse parallelism as a later optimization — the DAG shape is
the load-bearing part, not the concurrency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtractConfig:
    """Immutable inputs to one extract run. Constructed by the orchestration
    layer (``extract.run_extract``) and read by phases via ``ctx.config``."""

    repo_path: Path
    output_dir: Path
    force: bool = False
    flatten: bool = True
    write_editor_shims: bool = True
    fetch_github: bool = False
    github_token: str | None = None


# ---------------------------------------------------------------------------
# Phase ABC
# ---------------------------------------------------------------------------


class Phase(ABC):
    """Single stage of the extract DAG.

    Subclasses declare the three class-level fields and implement ``run``::

        class FooPhase(Phase):
            name = "foo"
            depends_on = ("inventory",)
            output_type = FooOutput

            def run(self, ctx: Context) -> FooOutput:
                inv = ctx.get(InventoryPhase)
                ...
                return FooOutput(...)
    """

    name: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    output_type: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Skip the validation for abstract intermediate classes that don't
        # declare a concrete ``name``. Concrete leaves must.
        if "name" not in cls.__dict__:
            return
        if not isinstance(cls.name, str) or not cls.name:
            raise TypeError(f"{cls.__name__}.name must be a non-empty string")
        if not isinstance(cls.depends_on, tuple):
            raise TypeError(f"{cls.__name__}.depends_on must be a tuple of phase names")
        if "output_type" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must declare an output_type")

    @abstractmethod
    def run(self, ctx: Context) -> Any:
        """Produce this phase's output. Must return an instance of
        ``self.output_type``; the runner type-checks the return value."""


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclass
class Context:
    """Carries config + accumulated phase outputs through one run.

    Phases call :meth:`get` (typed) or :meth:`get_by_name` (untyped) to read
    upstream outputs. The runner writes outputs via :meth:`put`; phases do
    not mutate the map directly.
    """

    config: ExtractConfig
    outputs: dict[str, Any] = field(default_factory=dict)

    def get(self, phase_class: type[Phase]) -> Any:
        """Return the output of *phase_class*. Raises :class:`KeyError` if the
        phase hasn't run (i.e. it's not in the runner's DAG, or it's
        downstream of the calling phase)."""
        return self.outputs[phase_class.name]

    def get_by_name(self, phase_name: str) -> Any:
        return self.outputs[phase_name]

    def has(self, phase_class: type[Phase]) -> bool:
        return phase_class.name in self.outputs

    def put(self, phase_name: str, value: Any) -> None:
        self.outputs[phase_name] = value


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class DAGCycleError(ValueError):
    """The phase set contains a dependency cycle."""


class MissingDependencyError(ValueError):
    """A phase declares a ``depends_on`` name that no other phase satisfies."""


class DuplicatePhaseError(ValueError):
    """Two phases share the same ``name``."""


class PhaseOutputTypeError(TypeError):
    """A phase returned a value of the wrong type for its declared
    ``output_type``."""


class PipelineRunner:
    """Topo-sorts and runs a list of :class:`Phase` instances.

    Construct once with the full phase list; the DAG is validated at
    construction time so all topology errors surface up front. Call
    :meth:`run` with an :class:`ExtractConfig` to execute.
    """

    def __init__(self, phases: Iterable[Phase]) -> None:
        self._phases: list[Phase] = list(phases)
        self._by_name: dict[str, Phase] = {}
        for phase in self._phases:
            if phase.name in self._by_name:
                raise DuplicatePhaseError(
                    f"two phases share name {phase.name!r}: "
                    f"{type(self._by_name[phase.name]).__name__} and "
                    f"{type(phase).__name__}"
                )
            self._by_name[phase.name] = phase
        self._order: list[Phase] = self._toposort()

    @property
    def order(self) -> list[Phase]:
        """The topologically sorted execution order. Read-only view."""
        return list(self._order)

    def run(
        self,
        config: ExtractConfig,
        *,
        seed_outputs: Mapping[str, Any] | None = None,
    ) -> Context:
        """Run every phase in topological order. Returns the final context.

        Args:
            config: The immutable run inputs.
            seed_outputs: Pre-populated phase outputs (keyed by phase name).
                Phases whose names appear here are skipped — useful for the
                cache-hit short-circuit and for testing downstream phases in
                isolation with a fixture for upstream output.
        """
        ctx = Context(config=config, outputs=dict(seed_outputs or {}))
        for phase in self._order:
            if phase.name in ctx.outputs:
                continue
            output = phase.run(ctx)
            if not isinstance(output, phase.output_type):
                raise PhaseOutputTypeError(
                    f"{type(phase).__name__}.run returned "
                    f"{type(output).__name__}, expected "
                    f"{phase.output_type.__name__}"
                )
            ctx.put(phase.name, output)
        return ctx

    # ------------------------------------------------------------------

    def _toposort(self) -> list[Phase]:
        # Validate every depends_on points at a declared phase.
        for phase in self._phases:
            for dep in phase.depends_on:
                if dep not in self._by_name:
                    raise MissingDependencyError(
                        f"phase {phase.name!r} depends on {dep!r}, which is not in the runner"
                    )

        # Kahn's algorithm. Stable order: when several phases are ready at
        # the same depth, run them in declaration order (the order they
        # appeared in the constructor's iterable) — this makes test repos
        # deterministic across runs.
        indeg: dict[str, int] = {p.name: len(p.depends_on) for p in self._phases}
        # downstream[X] is the list of phases that depend on X
        downstream: dict[str, list[str]] = {p.name: [] for p in self._phases}
        for phase in self._phases:
            for dep in phase.depends_on:
                downstream[dep].append(phase.name)

        # Declaration order preserved via index lookups.
        decl_index = {p.name: i for i, p in enumerate(self._phases)}
        ready: deque[str] = deque(
            sorted(
                (name for name, n in indeg.items() if n == 0),
                key=decl_index.__getitem__,
            )
        )
        ordered: list[Phase] = []
        while ready:
            name = ready.popleft()
            ordered.append(self._by_name[name])
            for child in downstream[name]:
                indeg[child] -= 1
                if indeg[child] == 0:
                    # Reinsert in declaration order to keep determinism.
                    ready.append(child)
                    ready = deque(sorted(ready, key=decl_index.__getitem__))
        if len(ordered) != len(self._phases):
            unresolved = sorted(set(self._by_name) - {p.name for p in ordered})
            raise DAGCycleError("pipeline DAG contains a cycle involving: " + ", ".join(unresolved))
        return ordered
