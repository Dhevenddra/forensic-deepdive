"""Registry-dispatch provider extractors (DEC-058, v0.5 Step 3).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` emitting provider
(``HANDLES``) records for registration sites (``@registry.register("x")`` /
``TOOLS = {"x": fn}`` / ``registry[name] = fn``). ``PROVIDER_EXTRACTORS`` is the
ordered list the dispatch registration wires in (``contracts.dispatch.register``).
"""

from forensic_deepdive.contracts.dispatch.providers.registrations import (
    extract_registry_providers,
)

PROVIDER_EXTRACTORS = [
    extract_registry_providers,
]

__all__ = [
    "PROVIDER_EXTRACTORS",
    "extract_registry_providers",
]
