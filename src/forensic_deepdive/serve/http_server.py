"""Read-only stdlib HTTP transport for `forensic serve --ui` (DEC-053).

No `uvicorn`/`starlette`/`flask` — a `ThreadingHTTPServer` + a
`BaseHTTPRequestHandler` subclass (zero new Python runtime dep). Hard rules:

* **127.0.0.1 only.** The CLI validates the host is loopback and refuses
  `0.0.0.0`/non-loopback; :func:`serve_ui` re-checks before binding.
* **Read-only.** Only ``GET`` is routed; every other method → ``405``. There
  are no mutation endpoints.
* **No path traversal.** ``/assets/*`` is served from the packaged asset dir;
  the resolved path must stay under the asset root or it's a ``404``.

Routes (all ``GET``):
  ``/``                 → the Sigma.js explorer (``assets/index.html``)
  ``/assets/<path>``    → vendored JS/CSS (traversal-guarded)
  ``/api/meta``         → filter-UI metadata
  ``/api/graph?...``    → bounded/filtered graphology graph
  ``/api/node?key=...`` → a node's context/trace side panel
"""

from __future__ import annotations

import ipaddress
import json
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from forensic_deepdive.serve.graph_api import build_graph_payload, build_meta, build_node_detail

if TYPE_CHECKING:
    from collections.abc import Callable

ASSETS_DIR = Path(__file__).parent / "assets"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def is_loopback_host(host: str) -> bool:
    """True iff *host* is a loopback address/name — the only hosts `serve --ui`
    will bind. Refuses ``0.0.0.0``, ``::``, and any routable address."""
    h = (host or "").strip()
    if h in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def make_handler(db_path: Path) -> type[BaseHTTPRequestHandler]:
    """Build a request-handler class closed over *db_path*. Factored out so the
    test suite can drive it without binding a socket."""
    resolved_db = Path(db_path)
    asset_root = ASSETS_DIR.resolve()

    class _Handler(BaseHTTPRequestHandler):
        server_version = "forensic-deepdive-serve/0.4"

        # --- read-only enforcement: only GET (and HEAD) are allowed ---------
        def do_POST(self) -> None:  # noqa: N802
            self._reject_write()

        def do_PUT(self) -> None:  # noqa: N802
            self._reject_write()

        def do_DELETE(self) -> None:  # noqa: N802
            self._reject_write()

        def do_PATCH(self) -> None:  # noqa: N802
            self._reject_write()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._reject_write()

        def _reject_write(self) -> None:
            self._send_json(
                {"error": "this server is read-only; only GET is allowed"},
                status=HTTPStatus.METHOD_NOT_ALLOWED,
                extra_headers={"Allow": "GET"},
            )

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            route = parsed.path
            params = parse_qs(parsed.query)
            try:
                if route == "/" or route == "/index.html":
                    self._send_asset("index.html")
                elif route.startswith("/assets/"):
                    self._send_asset(route[len("/assets/") :])
                elif route == "/api/meta":
                    self._send_json(build_meta(resolved_db))
                elif route == "/api/graph":
                    self._send_json(self._graph(params))
                elif route == "/api/node":
                    self._send_json(self._node(params))
                else:
                    self._send_json(
                        {"error": "not found", "path": route}, status=HTTPStatus.NOT_FOUND
                    )
            except BrokenPipeError:  # client navigated away mid-response
                pass
            except Exception as exc:  # noqa: BLE001 — never 500 with a stack trace
                self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # --- handlers -------------------------------------------------------
        def _graph(self, params: dict[str, list[str]]) -> dict[str, Any]:
            edge_types = params.get("edge_types")
            if edge_types and len(edge_types) == 1 and "," in edge_types[0]:
                edge_types = edge_types[0].split(",")
            return build_graph_payload(
                resolved_db,
                edge_types=edge_types,
                min_confidence=_one(params, "min_confidence", "AMBIGUOUS"),
                language=_one(params, "language", None),
                directory=_one(params, "directory", None),
                max_nodes=_int(params, "max_nodes", 300),
                max_edges=_int(params, "max_edges", 1500),
                focus=_one(params, "focus", None),
            )

        def _node(self, params: dict[str, list[str]]) -> dict[str, Any]:
            key = _one(params, "key", None) or _one(params, "qn", None)
            if not key:
                return {"error": "pass key= or qn="}
            return build_node_detail(resolved_db, key)

        # --- asset serving with a traversal guard ---------------------------
        def _send_asset(self, rel: str) -> None:
            candidate = (asset_root / rel).resolve()
            if asset_root not in candidate.parents and candidate != asset_root:
                self._send_json({"error": "forbidden"}, status=HTTPStatus.NOT_FOUND)
                return
            if not candidate.is_file():
                self._send_json({"error": "not found", "asset": rel}, status=HTTPStatus.NOT_FOUND)
                return
            body = candidate.read_bytes()
            ctype = _CONTENT_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # --- json helper ----------------------------------------------------
        def _send_json(
            self,
            payload: dict[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet by default
            return

    return _Handler


def serve_ui(
    db_path: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    on_ready: Callable[[str], None] | None = None,
) -> None:
    """Start the read-only graph-explorer HTTP server. Blocks until Ctrl-C.

    Refuses any non-loopback *host* (the 127.0.0.1-only invariant). *on_ready*
    receives the served URL once bound (used by the CLI to print it)."""
    if not is_loopback_host(host):
        raise ValueError(
            f"refusing to bind a non-loopback host {host!r}; "
            "`serve --ui` is 127.0.0.1-only (never 0.0.0.0)."
        )
    bind = "127.0.0.1" if host in ("localhost", "") else host
    handler = make_handler(Path(db_path))
    httpd = ThreadingHTTPServer((bind, port), handler)
    # the OS may have assigned a port if 0 was passed
    actual_port = httpd.socket.getsockname()[1]
    url = f"http://{bind}:{actual_port}/"
    if on_ready is not None:
        on_ready(url)
    if open_browser:
        _try_open_browser(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()


def _try_open_browser(url: str) -> None:
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:  # noqa: BLE001 — opening a browser is best-effort
        pass


def find_free_port(host: str = "127.0.0.1") -> int:
    """A free localhost port (test helper / ``--port 0`` resolution)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def _one(params: dict[str, list[str]], key: str, default: str | None) -> str | None:
    vals = params.get(key)
    return vals[0] if vals and vals[0] != "" else default


def _int(params: dict[str, list[str]], key: str, default: int) -> int:
    vals = params.get(key)
    if not vals:
        return default
    try:
        return int(vals[0])
    except (ValueError, TypeError):
        return default
