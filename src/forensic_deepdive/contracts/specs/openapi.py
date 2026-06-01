"""OpenAPI/Swagger spec detection + parsing — the codegen shortcut (DEC-048).

GitNexus has no OpenAPI spec detection and no codegen-aware HTTP shortcut (their
issue #306). When a repo ships a spec the frontend↔backend binding is
near-deterministic — operationId/path/method map 1:1 — so we emit **spec-backed**
provider :class:`~forensic_deepdive.contracts.base.Contract`s
(``spec_backed=True``, ``EXTRACTED``). The :class:`ContractPhase` reconciliation
then (a) marks any matching in-code provider ``spec_backed`` so its unique join
auto-upgrades to EXTRACTED (DEC-047 already wired that tier), and (b) keeps spec
ops with no in-code handler as **spec-only** Endpoints — the honest
documented-but-unlocated posture (no HANDLES, but the Endpoint still exists).

Dependency split (DEC-048, mirrors ``[semantic]``/DEC-042):
- **JSON is parsed with the stdlib — zero-dep.** Generated-client specs are
  usually JSON, so the EXTRACTED path works out of the box.
- **YAML needs the optional ``[openapi]`` extra** (``pyyaml``). Without it, a YAML
  spec is skipped **loudly** (returned in :attr:`SpecScan.skipped_yaml` for a
  findings-visible warning) — never a silent miss. YAML is read with
  ``yaml.safe_load`` only (``yaml.load`` is a code-execution surface).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    is_noise_path,
    normalize_provider_path,
)
from forensic_deepdive.contracts.http.scan import HTTP_VERBS
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.inventory import DEFAULT_IGNORE_DIRS

# Spec filename patterns: ``openapi``/``swagger`` (or ``*.openapi``/``*.swagger``)
# with a ``.json``/``.yaml``/``.yml`` suffix.
_SPEC_STEMS = frozenset({"openapi", "swagger"})
_SPEC_SUFFIXES = (".json", ".yaml", ".yml")
_YAML_SUFFIXES = frozenset({".yaml", ".yml"})


@dataclass(frozen=True, slots=True)
class SpecOperation:
    """One ``paths[<path>][<verb>]`` operation mined from a spec document."""

    method: str  # upper verb
    raw_path: str  # path as written (basePath-prefixed for Swagger 2.0)
    operation_id: str  # operationId, or "" when absent
    source: str  # spec file's repo-relative posix path


@dataclass(frozen=True, slots=True)
class SpecScan:
    """The repo's spec sweep: parsed operations + the YAML files skipped for want
    of the ``[openapi]`` extra (the caller logs these — loud degradation)."""

    operations: list[SpecOperation]
    skipped_yaml: list[str]


class _YamlExtraMissingError(Exception):
    """A ``.yaml``/``.yml`` spec was found but ``pyyaml`` (the ``[openapi]`` extra)
    is not installed."""


def _is_spec_name(name: str) -> bool:
    lower = name.lower()
    suffix = next((s for s in _SPEC_SUFFIXES if lower.endswith(s)), "")
    if not suffix:
        return False
    stem = lower[: -len(suffix)]
    return stem in _SPEC_STEMS or stem.endswith(".openapi") or stem.endswith(".swagger")


def detect_spec_files(repo_path: Path) -> list[Path]:
    """Return spec files under *repo_path*, sorted (deterministic). Prunes the
    inventory ignore-dirs + any dot-directory, mirroring ``take_inventory``."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in DEFAULT_IGNORE_DIRS
        ]
        for fn in filenames:
            if _is_spec_name(fn):
                found.append(Path(dirpath) / fn)
    return sorted(found)


def _load_doc(path: Path) -> object:
    """Parse a spec file to a Python object. ``.json`` uses the stdlib (zero-dep);
    ``.yaml``/``.yml`` needs the ``[openapi]`` extra (``yaml.safe_load`` only) and
    raises :class:`_YamlExtraMissingError` when it's absent."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in _YAML_SUFFIXES:
        try:
            import yaml
        except ModuleNotFoundError as exc:  # the [openapi] extra is not installed
            raise _YamlExtraMissingError from exc
        return yaml.safe_load(raw)
    return json.loads(raw)


def _operations_from_doc(doc: object, rel: str) -> list[SpecOperation]:
    if not isinstance(doc, dict):
        return []
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return []
    # Swagger 2.0 basePath (deterministic, cheap). OpenAPI 3 `servers` → v0.5.
    base = doc.get("basePath")
    prefix = base if isinstance(base, str) else ""
    ops: list[SpecOperation] = []
    for raw_path, item in paths.items():
        if not isinstance(raw_path, str) or not isinstance(item, dict):
            continue
        full_path = prefix + raw_path
        for verb, operation in item.items():
            if not isinstance(verb, str) or verb.lower() not in HTTP_VERBS:
                continue
            operation_id = ""
            if isinstance(operation, dict) and isinstance(operation.get("operationId"), str):
                operation_id = operation["operationId"]
            ops.append(
                SpecOperation(
                    method=verb.upper(),
                    raw_path=full_path,
                    operation_id=operation_id,
                    source=rel,
                )
            )
    return ops


def collect_spec_operations(repo_path: Path) -> SpecScan:
    """Detect + parse every spec under *repo_path*. JSON parses zero-dep; YAML
    without the ``[openapi]`` extra is skipped loudly (recorded, not parsed).
    Malformed/unreadable specs are skipped silently (not a degradation note)."""
    operations: list[SpecOperation] = []
    skipped: list[str] = []
    for path in detect_spec_files(repo_path):
        rel = path.relative_to(repo_path).as_posix()
        try:
            doc = _load_doc(path)
        except _YamlExtraMissingError:
            skipped.append(rel)
            continue
        except (json.JSONDecodeError, OSError, UnicodeError):
            continue
        operations.extend(_operations_from_doc(doc, rel))
    operations.sort(key=lambda o: (o.source, o.raw_path, o.method))
    return SpecScan(operations=operations, skipped_yaml=sorted(skipped))


def _spec_contract_ids(operations: list[SpecOperation]) -> dict[str, SpecOperation]:
    """Map each spec op's ``contract_id`` → its (first, by sorted order)
    SpecOperation, dropping noise paths."""
    by_id: dict[str, SpecOperation] = {}
    for op in operations:
        normalized = normalize_provider_path(op.raw_path)
        if is_noise_path(normalized):
            continue
        by_id.setdefault(http_contract_id(op.method, normalized), op)
    return by_id


def reconcile_with_specs(
    providers: list[Contract], operations: list[SpecOperation]
) -> list[Contract]:
    """Fold spec operations into the provider set (DEC-048).

    (1) Any in-code provider whose ``contract_id`` is spec-backed is rebuilt with
    ``spec_backed=True`` → its unique join upgrades to EXTRACTED (DEC-047).
    (2) A spec op with no in-code provider becomes a **spec-only** provider with a
    synthetic ``symbol_id`` (``<spec>::<operationId|method path>``) — not a real
    graph symbol, so its HANDLES edge is filtered out, but the Endpoint node is
    still emitted (documented-but-unlocated). Deterministic (spec ops appended in
    sorted contract_id order)."""
    spec_by_id = _spec_contract_ids(operations)
    if not spec_by_id:
        return providers

    in_code_ids = {p.contract_id for p in providers}
    result = [
        replace(p, spec_backed=True) if (p.contract_id in spec_by_id and not p.spec_backed) else p
        for p in providers
    ]

    for contract_id in sorted(spec_by_id):
        if contract_id in in_code_ids:
            continue
        op = spec_by_id[contract_id]
        symbol = op.operation_id or f"{op.method} {op.raw_path}"
        result.append(
            Contract(
                role=ContractRole.PROVIDER,
                contract_id=contract_id,
                symbol_id=f"{op.source}::{symbol}",
                confidence=Confidence.EXTRACTED,
                evidence=f"openapi {op.method} {op.raw_path} ({op.source})",
                protocol="http",
                method=op.method,
                normalized_path=normalize_provider_path(op.raw_path),
                raw_path=op.raw_path,
                framework="openapi",
                spec_backed=True,
                rel_path=op.source,
            )
        )
    return result
