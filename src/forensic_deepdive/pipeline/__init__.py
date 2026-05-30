"""Extract pipeline — the v0.2 typed-phase DAG (DEC-014).

Public surface preserved from v0.1::

    from forensic_deepdive.pipeline import run_extract, ExtractResult

v0.2-only types are exposed for callers that want to compose new phases or
inspect the DAG directly::

    from forensic_deepdive.pipeline import (
        Context, ExtractConfig, Phase, PipelineRunner,
        InventoryPhase, StaticPhase, FlattenPhase, HistoryPhase, EmitPhase,
        default_phases,
    )
"""

from forensic_deepdive.pipeline.extract import ExtractResult, run_extract
from forensic_deepdive.pipeline.phases import (
    BuildGraphOutput,
    BuildGraphPhase,
    EmitOutput,
    EmitPhase,
    FlattenOutput,
    FlattenPhase,
    HistoryOutput,
    HistoryPhase,
    InventoryOutput,
    InventoryPhase,
    ParseOutput,
    ParsePhase,
    StaticOutput,
    StaticPhase,
    default_phases,
)
from forensic_deepdive.pipeline.runner import (
    Context,
    DAGCycleError,
    DuplicatePhaseError,
    ExtractConfig,
    MissingDependencyError,
    Phase,
    PhaseOutputTypeError,
    PipelineRunner,
)

__all__ = [
    "BuildGraphOutput",
    "BuildGraphPhase",
    "Context",
    "DAGCycleError",
    "DuplicatePhaseError",
    "EmitOutput",
    "EmitPhase",
    "ExtractConfig",
    "ExtractResult",
    "FlattenOutput",
    "FlattenPhase",
    "HistoryOutput",
    "HistoryPhase",
    "InventoryOutput",
    "InventoryPhase",
    "MissingDependencyError",
    "ParseOutput",
    "ParsePhase",
    "Phase",
    "PhaseOutputTypeError",
    "PipelineRunner",
    "StaticOutput",
    "StaticPhase",
    "default_phases",
    "run_extract",
]
