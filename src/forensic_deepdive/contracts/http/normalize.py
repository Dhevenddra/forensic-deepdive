"""HTTP path normalization + ``contractId`` (DEC-044, v0.4 Item E).

Copies GitNexus's normalization *algorithm* (research §2) but emits **our own**
confidence tags downstream — normalization itself is a pure, tag-free
equivalence-class function. No graph, no tree-sitter, no I/O (the DEC-009
pure-static floor). This is the ``contractId`` seam the registry's HTTP
``key_builder`` points at, replacing the Item-D placeholder.

The equivalence class this collapses (provider ≡ consumer instances)::

    /users/{id}  ≡  /users/${id}  ≡  /users/:id  ≡  /users/42 (consumer)
    ≡  f"/users/{id}" (extractor hands us /users/{id})
        →  http::GET::/users/{param}

Provider vs consumer differ in *aggressiveness*: a provider route is a
declaration (we keep literal numerics — ``/orders/42`` as a declared route is
distinct), a consumer URL is a runtime instance (numeric segments collapse to
``{param}``, template literals and absolute-URL hosts are stripped).
"""

from __future__ import annotations

import re

# --- param-syntax collapses (order matters; see _collapse_params) -------------
# Express ``:id`` (greedy to the next slash), FastAPI/Spring ``{id}``,
# Next.js ``[id]``, and the consumer-only template literal ``${id}``.
_RE_TEMPLATE = re.compile(r"\$\{[^}]+\}")  # ${id}  (consumer only — must run first)
_RE_ANGLE = re.compile(r"<[^>]+>")  # <id> / <int:id>  (Flask — must run before colon)
_RE_COLON = re.compile(r":[^/]+")  # :id    (Express)
_RE_BRACE = re.compile(r"\{[^}]+\}")  # {id}   (FastAPI/Spring)
_RE_BRACKET = re.compile(r"\[[^\]]+\]")  # [id]   (Next.js)
# A whole digit-run segment: preceded by ``/`` and followed by ``/`` or end.
# ``/v1``, ``/2fa``, ``/api/v2`` are preserved (the run must start right after a
# slash and be entirely digits). Consumer only.
_RE_NUMERIC = re.compile(r"(?<=/)\d+(?=/|$)")

# scheme://authority  and  protocol-relative //authority
_RE_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

# Health-check / infra paths that are not real application contracts.
_NOISE_PATHS = frozenset(
    {
        "/health",
        "/healthz",
        "/healthcheck",
        "/ping",
        "/status",
        "/livez",
        "/readyz",
        "/ready",
        "/live",
        "/metrics",
        "/favicon.ico",
    }
)


def _pathname(path: str) -> str:
    """Strip an absolute or protocol-relative URL down to its pathname
    (``https://api.example.com/users/1`` → ``/users/1``). Relative paths pass
    through untouched."""
    if _RE_SCHEME.match(path):
        rest = _RE_SCHEME.sub("", path, count=1)
    elif path.startswith("//"):
        rest = path[2:]
    else:
        return path
    slash = rest.find("/")
    return rest[slash:] if slash != -1 else "/"


def _base_normalize(path: str) -> str:
    """Shared prefix of both normalizers: strip query+fragment, lowercase,
    ensure a leading slash, drop a trailing slash (root ``/`` preserved)."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    path = path.lower()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return path


def _collapse_params(path: str, *, consumer: bool) -> str:
    """Collapse param syntaxes to a single ``{param}`` token. Order is the whole
    subtlety: ``${id}`` must collapse before the generic ``{id}`` rule (else it
    degrades to ``${param}``); numerics collapse last and only for consumers."""
    if consumer:
        path = _RE_TEMPLATE.sub("{param}", path)
    path = _RE_ANGLE.sub("{param}", path)  # Flask <int:id> — before colon (it contains ':')
    path = _RE_COLON.sub("{param}", path)
    path = _RE_BRACE.sub("{param}", path)
    path = _RE_BRACKET.sub("{param}", path)
    if consumer:
        path = _RE_NUMERIC.sub("{param}", path)
    return path


def normalize_provider_path(path: str) -> str:
    """Normalize a *route-declaration* path (GitNexus ``normalizeHttpPath``).

    strip query → lowercase → leading-slash → drop trailing slash → collapse
    ``:id`` / ``{id}`` / ``[id]`` / ``<id>`` / ``<int:id>`` → ``{param}``. Literal
    numeric segments are **kept** (a declared ``/orders/42`` route is distinct)."""
    return _collapse_params(_base_normalize(path), consumer=False)


def normalize_consumer_path(path: str) -> str:
    """Normalize a *call-site* URL (GitNexus ``normalizeConsumerPath``).

    Provider rules **plus**: absolute/protocol-relative URL → pathname first,
    template-literal ``${x}`` → ``{param}``, and numeric segments
    ``/orders/42`` → ``/orders/{param}`` (a runtime instance of an id)."""
    return _collapse_params(_base_normalize(_pathname(path)), consumer=True)


def http_contract_id(method: str, normalized_path: str) -> str:
    """``http::<METHOD>::<normalized_path>`` (DEC-043/044). ``method`` is
    uppercased; pass ``"*"`` for the method-agnostic key (see
    :func:`http_wildcard_id`). The path must already be normalized by one of the
    functions above — this is the registry's HTTP ``key_builder``."""
    return f"http::{method.upper()}::{normalized_path}"


def http_wildcard_id(normalized_path: str) -> str:
    """The method-agnostic key ``http::*::<normalized_path>`` — Item H's fallback
    when a consumer's verb can't be inferred but the path matches a provider."""
    return http_contract_id("*", normalized_path)


def is_noise_path(normalized_path: str) -> bool:
    """True when a normalized path is not a real application contract: empty/root,
    a known health-check/infra path, or **param-only** (every segment is
    ``{param}``, so it would match every route — a false-join fan-out source)."""
    if not normalized_path or normalized_path == "/":
        return True
    if normalized_path in _NOISE_PATHS:
        return True
    segments = [s for s in normalized_path.split("/") if s]
    return bool(segments) and all(s == "{param}" for s in segments)
