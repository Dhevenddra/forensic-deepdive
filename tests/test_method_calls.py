"""Tests for dotted method-call extraction (v0.3 Item C / DEC-037, layer C2).

In-memory source per language. Asserts the ``(receiver, method,
enclosing_scope)`` triples extracted from ``receiver.method(...)`` sites, plus
the cache round-trip of the new ``method_calls`` records.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.method_calls import MethodCall, extract_method_calls
from forensic_deepdive.static.parse import ParsedFile, parse_source
from forensic_deepdive.static.parse_cache import ParseCache, content_hash, parse_and_extract


def _calls(language: str, src: bytes) -> list[MethodCall]:
    tree = parse_source(src, language)
    parsed = ParsedFile(
        path=Path(f"x.{language}"),
        rel_path=f"x.{language}",
        language=language,
        source=src,
        tree=tree,
    )
    return extract_method_calls(parsed)


def _triples(calls: list[MethodCall]) -> set[tuple[str, str, str]]:
    return {(c.receiver, c.method, c.enclosing_scope) for c in calls}


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def test_python_self_and_local_and_static() -> None:
    src = b"""
class Greeter:
    def greet(self):
        self.render()
        helper = Formatter()
        helper.format()
        Logger.warn()

def top():
    Greeter().greet()
"""
    triples = _triples(_calls("python", src))
    assert ("self", "render", "Greeter.greet") in triples
    assert ("helper", "format", "Greeter.greet") in triples
    assert ("Logger", "warn", "Greeter.greet") in triples
    # bare-name `Greeter()` and chained `.greet()` — receiver of greet() is the
    # `Greeter()` call expression (complex receiver), scoped to top().
    assert any(m == "greet" and scope == "top" for _r, m, scope in triples)


def test_python_bare_calls_are_not_method_calls() -> None:
    # A bare call has no receiver — it stays on the DEC-025 path, not here.
    assert _calls("python", b"def f():\n    g()\n") == []


# ---------------------------------------------------------------------------
# TypeScript / JavaScript
# ---------------------------------------------------------------------------


def test_typescript_this_and_object() -> None:
    src = b"""
class Widget {
  render(): void {
    this.draw();
    const svc = new Service();
    svc.start();
  }
}
"""
    triples = _triples(_calls("typescript", src))
    assert ("this", "draw", "Widget.render") in triples
    assert ("svc", "start", "Widget.render") in triples


def test_javascript_object_call() -> None:
    triples = _triples(_calls("javascript", b"function run() {\n  api.fetch();\n}\n"))
    assert ("api", "fetch", "run") in triples


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------


def test_java_this_and_static() -> None:
    src = b"""
class Service {
  void handle() {
    this.process();
    Logger.info();
  }
}
"""
    triples = _triples(_calls("java", src))
    assert ("this", "process", "Service.handle") in triples
    assert ("Logger", "info", "Service.handle") in triples


# ---------------------------------------------------------------------------
# Out-of-scope languages: no method calls (no regression, no new edges)
# ---------------------------------------------------------------------------


def test_go_method_calls_are_out_of_scope() -> None:
    assert _calls("go", b"package m\nfunc run() {\n\tfmt.Println()\n}\n") == []


# ---------------------------------------------------------------------------
# Cache round-trip of the new method_calls records
# ---------------------------------------------------------------------------


def test_method_calls_survive_cache_round_trip(tmp_path: Path) -> None:
    src = b"class C:\n    def m(self):\n        self.helper()\n"
    abs_path = tmp_path / "c.py"
    abs_path.write_bytes(src)
    fresh = parse_and_extract(abs_path, "c.py", "python", src)
    assert fresh.method_calls and fresh.method_calls[0].method == "helper"

    cache = ParseCache(tmp_path / "parse")
    sha = content_hash(src)
    cache.put(sha, "python", fresh)
    got = cache.get("c.py", sha, "python")
    assert got is not None
    assert [(m.receiver, m.method, m.enclosing_scope) for m in got.method_calls] == [
        (m.receiver, m.method, m.enclosing_scope) for m in fresh.method_calls
    ]
