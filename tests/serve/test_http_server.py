"""`forensic serve --ui` read-only HTTP transport (DEC-053, v0.4 Item K).

Asserts the hard invariants: 127.0.0.1-only bind, read-only (POST/PUT/… → 405),
asset path-traversal blocked, the vendored bundle loads (the "UI bundle builds/
loads" smoke), and the `/api/*` endpoints return bounded JSON. Drives a real
`ThreadingHTTPServer` on an ephemeral loopback port in a background thread.
"""

from __future__ import annotations

import json
import shutil
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases
from forensic_deepdive.serve import http_server
from forensic_deepdive.serve.http_server import find_free_port, is_loopback_host, make_handler

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory):  # noqa: ANN201
    tmp_path = tmp_path_factory.mktemp("serve_http")
    repo = tmp_path / "openapi_codegen_sample"
    shutil.copytree(FIXTURES / "openapi_codegen_sample", repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)

    port = find_free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd, port
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(port: int, path: str) -> tuple[int, bytes, dict[str, str]]:
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    headers = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return resp.status, body, headers


def _request(port: int, method: str, path: str) -> int:
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path)
    status = conn.getresponse().status
    conn.close()
    return status


# --- loopback-only ----------------------------------------------------------


def test_is_loopback_host() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("localhost")
    assert is_loopback_host("::1")
    assert not is_loopback_host("0.0.0.0")
    assert not is_loopback_host("192.168.1.10")
    assert not is_loopback_host("example.com")


def test_bind_address_is_loopback(server) -> None:  # noqa: ANN001
    httpd, _ = server
    assert httpd.server_address[0] == "127.0.0.1"


def test_serve_ui_refuses_non_loopback(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        http_server.serve_ui(tmp_path / "x.lbug", host="0.0.0.0", open_browser=False)


# --- read-only --------------------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def test_writes_are_rejected(server, method: str) -> None:  # noqa: ANN001
    _, port = server
    assert _request(port, method, "/api/graph") == 405


# --- routing ----------------------------------------------------------------


def test_index_served(server) -> None:  # noqa: ANN001
    _, port = server
    status, body, headers = _get(port, "/")
    assert status == 200
    assert b"forensic" in body
    assert "text/html" in headers["content-type"]


def test_vendored_bundle_loads(server) -> None:  # noqa: ANN001
    """The 'UI bundle builds/loads' smoke — the vendored Sigma.js is served."""
    _, port = server
    status, body, headers = _get(port, "/assets/vendor/sigma.min.js")
    assert status == 200
    assert len(body) > 10_000
    assert "javascript" in headers["content-type"]
    assert _get(port, "/assets/app.js")[0] == 200
    assert _get(port, "/assets/app.css")[0] == 200


def test_asset_path_traversal_blocked(server) -> None:  # noqa: ANN001
    _, port = server
    status, _, _ = _get(port, "/assets/../../../../etc/passwd")
    assert status == 404
    # the URL-encoded form is normalised by http.client; assert a direct attempt too
    assert _get(port, "/assets/..%2f..%2fpyproject.toml")[0] == 404


def test_unknown_route_404(server) -> None:  # noqa: ANN001
    _, port = server
    assert _get(port, "/nope")[0] == 404


# --- api endpoints ----------------------------------------------------------


def test_api_meta(server) -> None:  # noqa: ANN001
    _, port = server
    status, body, _ = _get(port, "/api/meta")
    assert status == 200
    meta = json.loads(body)
    assert "python" in meta["languages"]
    assert meta["edge_type_counts"]["ROUTES_TO"] >= 1


def test_api_graph_bounded(server) -> None:  # noqa: ANN001
    _, port = server
    status, body, headers = _get(port, "/api/graph?max_nodes=6&max_edges=5")
    assert status == 200
    assert "application/json" in headers["content-type"]
    payload = json.loads(body)
    assert len(payload["nodes"]) <= 6
    assert len(payload["edges"]) <= 5


def test_api_graph_edge_type_filter(server) -> None:  # noqa: ANN001
    _, port = server
    _, body, _ = _get(port, "/api/graph?edge_types=ROUTES_TO")
    payload = json.loads(body)
    assert {e["attributes"]["etype"] for e in payload["edges"]} == {"ROUTES_TO"}


def test_api_node_detail(server) -> None:  # noqa: ANN001
    _, port = server
    _, body, _ = _get(port, "/api/node?key=sym:client.js::loadItem")
    detail = json.loads(body)
    assert detail["trace_downstream"]["chains"]


def test_api_node_requires_key(server) -> None:  # noqa: ANN001
    _, port = server
    _, body, _ = _get(port, "/api/node")
    assert "error" in json.loads(body)
