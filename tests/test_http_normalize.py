"""HTTP path normalization + contractId (DEC-044, v0.4 Item E).

The headline acceptance is the equivalence class: four param syntaxes plus a
consumer numeric instance all collapse to one contractId.
"""

from __future__ import annotations

import pytest

from forensic_deepdive.contracts.http.normalize import (
    http_contract_id,
    http_wildcard_id,
    is_noise_path,
    normalize_consumer_path,
    normalize_provider_path,
)


# --- the headline equivalence class ------------------------------------------
def test_equivalence_class_all_collapse_to_one_contract_id():
    """``/users/{id}`` ≡ ``/users/${id}`` ≡ ``/users/:id`` ≡ ``/users/42``
    (consumer) ≡ ``f"/users/{id}"`` all → ``http::GET::/users/{param}``."""
    target = "http::GET::/users/{param}"

    # provider declarations (the extractor hands us the raw decorator/annotation path)
    assert http_contract_id("get", normalize_provider_path("/users/{id}")) == target
    assert http_contract_id("get", normalize_provider_path("/users/:id")) == target
    assert http_contract_id("get", normalize_provider_path("/users/[id]")) == target
    # f"/users/{id}" — by the time normalize sees it, it's the brace form
    assert http_contract_id("GET", normalize_provider_path("/users/{id}")) == target

    # consumer call sites — including the template literal and a numeric instance
    assert http_contract_id("get", normalize_consumer_path("/users/${id}")) == target
    assert http_contract_id("get", normalize_consumer_path("/users/{id}")) == target
    assert http_contract_id("get", normalize_consumer_path("/users/:id")) == target
    assert http_contract_id("get", normalize_consumer_path("/users/42")) == target


# --- provider normalization ---------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/Users/{ID}", "/users/{param}"),  # lowercase + brace
        ("/users/:id", "/users/{param}"),  # express colon
        ("/users/<int:user_id>", "/users/{param}"),  # flask typed angle
        ("/users/<user_id>", "/users/{param}"),  # flask plain angle
        ("/posts/[slug]", "/posts/{param}"),  # nextjs bracket
        ("/users/{id}/posts/{postId}", "/users/{param}/posts/{param}"),  # multi
        ("/users/", "/users"),  # trailing slash dropped
        ("/", "/"),  # root preserved
        ("/users?page=2", "/users"),  # query stripped
        ("/users#frag", "/users"),  # fragment stripped
        ("users", "/users"),  # leading slash added
    ],
)
def test_normalize_provider_path(raw, expected):
    assert normalize_provider_path(raw) == expected


def test_provider_keeps_numeric_segments():
    """A declared ``/orders/42`` route is a distinct literal — providers do NOT
    collapse numerics (only consumers do)."""
    assert normalize_provider_path("/orders/42") == "/orders/42"


# --- consumer normalization ---------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/users/${id}", "/users/{param}"),  # template literal
        ("/orders/42", "/orders/{param}"),  # numeric instance
        ("/orders/42/items/7", "/orders/{param}/items/{param}"),  # multi numeric
        ("/api/v2/users", "/api/v2/users"),  # version segment preserved
        ("/2fa/setup", "/2fa/setup"),  # not a whole digit-run segment
        ("/users/${id}/posts/42", "/users/{param}/posts/{param}"),  # mixed
    ],
)
def test_normalize_consumer_path(raw, expected):
    assert normalize_consumer_path(raw) == expected


def test_consumer_absolute_url_pathname_extraction():
    assert normalize_consumer_path("https://api.example.com/users/42") == "/users/{param}"
    assert normalize_consumer_path("http://localhost:8000/users/${id}") == "/users/{param}"
    # protocol-relative
    assert normalize_consumer_path("//cdn.example.com/assets/1") == "/assets/{param}"
    # absolute URL with query
    assert normalize_consumer_path("https://api.example.com/users?page=2") == "/users"


def test_template_collapses_before_brace():
    """``${id}`` must collapse before the generic brace rule, never degrade to
    ``${param}``."""
    assert normalize_consumer_path("/users/${id}") == "/users/{param}"
    assert "${param}" not in normalize_consumer_path("/users/${id}")


# --- contract id + wildcard ---------------------------------------------------
def test_http_contract_id_uppercases_method():
    assert http_contract_id("get", "/users/{param}") == "http::GET::/users/{param}"
    assert http_contract_id("Post", "/users") == "http::POST::/users"


def test_http_wildcard_id():
    assert http_wildcard_id("/users/{param}") == "http::*::/users/{param}"
    assert http_wildcard_id("/users/{param}") == http_contract_id("*", "/users/{param}")


# --- noise filter -------------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    [
        "",
        "/",
        "/health",
        "/healthz",
        "/ping",
        "/metrics",
        "/favicon.ico",
        "/{param}",  # param-only — matches everything
        "/{param}/{param}",
    ],
)
def test_is_noise_path_true(path):
    assert is_noise_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/users",
        "/users/{param}",  # has a literal anchor
        "/api/health/details",  # not the bare health path
        "/orders/{param}/items",
    ],
)
def test_is_noise_path_false(path):
    assert is_noise_path(path) is False


# --- determinism --------------------------------------------------------------
def test_determinism():
    for _ in range(5):
        assert normalize_consumer_path("/Users/${ID}/Posts/42") == "/users/{param}/posts/{param}"
        assert normalize_provider_path("/Users/{ID}/") == "/users/{param}"


# --- registry wiring: the placeholder is gone, the real builder is live -------
def test_registry_uses_real_contract_id():
    from forensic_deepdive.contracts.registry import REGISTRY

    builder = REGISTRY["http"].key_builder
    assert builder("get", "/users/{param}") == "http::GET::/users/{param}"
