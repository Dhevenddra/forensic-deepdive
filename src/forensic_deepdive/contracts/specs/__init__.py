"""Contract-spec detection (DEC-048, v0.4 Item I — the codegen shortcut).

OpenAPI/Swagger is the only spec format in v0.4 (`.proto`/GraphQL/tRPC are a v0.5
seam). A shipped spec is the authoritative provider list — it upgrades matching
in-code joins to EXTRACTED (the differentiator GitNexus lacks)."""

from __future__ import annotations

from forensic_deepdive.contracts.specs.openapi import (
    SpecOperation,
    SpecScan,
    collect_spec_operations,
    detect_spec_files,
    reconcile_with_specs,
)

__all__ = [
    "SpecOperation",
    "SpecScan",
    "collect_spec_operations",
    "detect_spec_files",
    "reconcile_with_specs",
]
