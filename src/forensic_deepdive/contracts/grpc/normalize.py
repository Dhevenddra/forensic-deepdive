"""gRPC ``contract_id`` key-builder (DEC-060, v0.5 Step 5; DEC-068, v0.6 Step 5).

Keyed on the **generated module identity** ``grpc::<module>::<Service>/<Method>`` where
``<module>`` is the protoc-emitted ``<protofile>_pb2_grpc`` module (DEC-068). A ``.proto``
``rpc M`` in ``service S`` of file ``route_guide.proto`` and a Python servicer/stub on
``route_guide_pb2_grpc.S`` both produce ``grpc::route_guide_pb2_grpc::S/M`` → an EXTRACTED
join, while a *different* proto's same-named service (``helloworld_pb2_grpc::Greeter/…``)
no longer collides with ``route_guide_pb2_grpc::Greeter/…``.

**CAVEAT (DEC-068).** The module-identity key is the Python *generated-code* identity, not
the gRPC **wire path** ``/<package>.<Service>/<Method>`` (which uses the ``.proto``
``package`` declaration). The two are deterministically related but not equal; treating
the module key as the wire path is an INFERRED equivalence and stays deferred (Go/Java
gRPC would key on the wire path). We recover the module from generated-Python AST only —
**no ``.proto`` parse for the module, no ``[proto]`` dep.**
"""

from __future__ import annotations

import posixpath
from collections.abc import Iterable

from forensic_deepdive.static.imports import Import


def grpc_contract_id(module: str, service: str, method: str) -> str:
    """The canonical ``grpc::<module>::<Service>/<Method>`` contract id (the registry's
    ``grpc`` key-builder). ``module`` is the generated ``*_pb2_grpc`` module identity."""
    return f"grpc::{module}::{service}/{method}"


def grpc_flat_module_id(basename: str, dir_prefix: str) -> str:
    """A flat/relative-imported ``*_pb2_grpc`` module is a **sibling** of the importing
    file, so two examples in different directories that both ``import helloworld_pb2_grpc``
    name *different* generated modules — the identity is **directory-qualified** (DEC-068).
    A package-imported module (dotted path) is shared and keeps its dotted identity."""
    return f"{dir_prefix}/{basename}" if dir_prefix else basename


def _qualify_module(module_path: str, dir_prefix: str) -> str:
    """Resolve an import's module path to a stable module identity: a dotted **absolute
    package** (``myapp.gen.foo_pb2_grpc``) is shared → kept as-is; a **flat** (``foo_pb2_grpc``)
    or **relative** (``.foo_pb2_grpc``) import is a sibling → directory-qualified."""
    mp = module_path or ""
    if not mp:
        return ""
    if mp.startswith("."):  # relative import — navigate up from the importing dir
        dots = len(mp) - len(mp.lstrip("."))
        rest = mp[dots:]
        base = dir_prefix
        for _ in range(dots - 1):
            base = posixpath.dirname(base)
        tail = rest.replace(".", "/")
        return f"{base}/{tail}" if (base and tail) else (tail or base)
    if "." in mp:  # absolute dotted package path — shared across directories
        return mp
    return grpc_flat_module_id(mp, dir_prefix)  # flat single-segment sibling


def grpc_module_alias_table(imports: Iterable[Import], rel_path: str) -> dict[str, str]:
    """Map every local name a file binds to its generated ``*_pb2_grpc`` **module identity**
    (directory-qualified for flat/relative imports, dotted for package imports), so a
    servicer base / stub ctor reference resolves regardless of import form (``import X``,
    ``import X as Y``, ``from . import X``, ``from pkg import X``, ``from X import Servicer``).
    Pass the imports already filtered to one file."""
    dir_prefix = posixpath.dirname(rel_path)
    table: dict[str, str] = {}
    for imp in imports:
        if imp.language != "python":
            continue
        mp = imp.module_path or ""
        if not imp.imported_names:  # import M [as A]
            bound = imp.module_alias or mp.rstrip(".").split(".")[-1]
            if bound:
                table[bound] = _qualify_module(mp, dir_prefix)
            continue
        for ime in imp.imported_names:  # from MOD import N [as A]
            bound = ime.alias or ime.name
            if not bound or bound == "*":
                continue
            if ime.name.endswith("_pb2_grpc") or ime.name.endswith("_pb2"):
                # submodule import: MOD.N (or relative .N) is the module
                sub = (
                    (mp + ime.name)
                    if mp.endswith(".")
                    else (f"{mp}.{ime.name}" if mp else ime.name)
                )
                table[bound] = _qualify_module(sub, dir_prefix)
            else:
                table[bound] = _qualify_module(mp, dir_prefix)  # from X_pb2_grpc import Servicer
    return table


def grpc_resolve_module(name: str, alias_table: dict[str, str], dir_prefix: str = "") -> str:
    """Resolve a local module/symbol reference to its generated module identity via the
    alias table; fall back to a directory-qualified flat id when no import record exists
    (still deterministic — servicer, stub, and proto in one directory resolve identically)."""
    if name in alias_table:
        return alias_table[name]
    return grpc_flat_module_id(name, dir_prefix)
