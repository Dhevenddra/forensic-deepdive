"""HTTP as the first instance of the CrossBoundaryEdge abstraction (DEC-043/044).

``normalize`` is the path→``contractId`` equivalence-class layer (Item E); the
``providers``/``consumers`` extractor subpackages land in Items F/G and the
codegen spec shortcut in Item I.
"""

from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    http_wildcard_id,
    is_noise_path,
    normalize_consumer_path,
    normalize_provider_path,
)

__all__ = [
    "http_contract_id",
    "http_wildcard_id",
    "is_noise_path",
    "normalize_consumer_path",
    "normalize_provider_path",
]
