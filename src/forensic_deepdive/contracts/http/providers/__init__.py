"""HTTP route-provider extractors (DEC-045, v0.4 Item F).

Each extractor is a pure ``(ContractContext) -> list[Contract]`` function.
``PROVIDER_EXTRACTORS`` is the ordered list the HTTP registration wires into the
registry (see ``contracts.http.register``). FastAPI is the first instance;
Express/Spring/Flask join this list as they land.
"""

from forensic_deepdive.contracts.http.providers.express import extract_express_providers
from forensic_deepdive.contracts.http.providers.fastapi import extract_fastapi_providers
from forensic_deepdive.contracts.http.providers.flask import extract_flask_providers
from forensic_deepdive.contracts.http.providers.spring import extract_spring_providers

PROVIDER_EXTRACTORS = [
    extract_fastapi_providers,
    extract_flask_providers,
    extract_express_providers,
    extract_spring_providers,
]

__all__ = [
    "PROVIDER_EXTRACTORS",
    "extract_express_providers",
    "extract_fastapi_providers",
    "extract_flask_providers",
    "extract_spring_providers",
]
