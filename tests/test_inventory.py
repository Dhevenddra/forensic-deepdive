"""Tests for the repository inventory stage."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.inventory import classify_role, take_inventory

FIXTURES = Path(__file__).parent / "fixtures"


def test_inventory_python_sample() -> None:
    inventory = take_inventory(FIXTURES / "python_sample")
    assert inventory.file_count == 2
    assert inventory.language_breakdown == {"python": 2}
    assert {item.rel_path for item in inventory.source_files} == {"app.py", "greeter.py"}


def test_inventory_skips_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("z = 3\n", encoding="utf-8")
    inventory = take_inventory(tmp_path)
    assert {item.rel_path for item in inventory.source_files} == {"src/main.py"}


def test_inventory_skips_unknown_extensions(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("# hi\n", encoding="utf-8")
    (tmp_path / "data.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "code.py").write_text("a = 1\n", encoding="utf-8")
    inventory = take_inventory(tmp_path)
    assert {item.rel_path for item in inventory.source_files} == {"code.py"}


def test_inventory_skips_oversized_files(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("# " + "x" * 500, encoding="utf-8")
    inventory = take_inventory(tmp_path, max_file_bytes=10)
    assert inventory.source_files == []


def test_classify_role() -> None:
    assert classify_role("src/app.py") == "source"
    assert classify_role("tests/test_cache.py") == "test"
    assert classify_role("conftest.py") == "test"
    assert classify_role("pkg/utils.spec.js") == "test"
    assert classify_role("tests/fixtures/sample/greeter.py") == "fixture"
    assert classify_role("testdata/blob.py") == "fixture"


def test_classify_role_vendored() -> None:
    """DEC-021. Vendored paths take precedence over test/fixture markers."""
    assert classify_role("third_party/opus/celt/celt.c") == "vendored"
    assert classify_role("third-party/foo.py") == "vendored"
    assert classify_role("external/lib/bar.go") == "vendored"
    assert classify_role("_vendor/x.py") == "vendored"
    # Embedded version string in a path segment.
    assert classify_role("opus-1.3.1/celt/celt.c") == "vendored"
    assert classify_role("zstd-1.5.5/lib/common.c") == "vendored"
    # Bare semver-ish but not in a path segment doesn't trigger.
    assert classify_role("src/release-2026.py") != "vendored"


def test_classify_role_generated_by_filename() -> None:
    """DEC-021. Filename patterns for the common code-generators."""
    assert classify_role("lib/model.g.dart") == "generated"
    assert classify_role("lib/model.freezed.dart") == "generated"
    assert classify_role("lib/router.gr.dart") == "generated"
    assert classify_role("proto/service.pb.dart") == "generated"
    assert classify_role("pkg/foo_pb.py") == "generated"
    assert classify_role("pkg/foo_pb2.py") == "generated"
    assert classify_role("pkg/foo_pb2_grpc.py") == "generated"
    assert classify_role("internal/proto/foo.pb.go") == "generated"
    assert classify_role("src/foo.generated.ts") == "generated"
    assert classify_role("src/foo.gen.go") == "generated"


def test_classify_role_precedence() -> None:
    """Vendored beats fixture; test beats generated-by-filename in tests/."""
    # vendored beats fixture
    assert classify_role("third_party/lib/fixtures/data.py") == "vendored"
    # tests/ beats generated-by-filename — generated detection comes after
    # test segments in the precedence chain.
    assert classify_role("tests/snapshot_pb.py") == "test"


def test_classify_role_example() -> None:
    """DEC-049. Example/tutorial trees get their own role (kept in the graph,
    demoted later)."""
    assert classify_role("examples/quickstart.py") == "example"
    assert classify_role("docs_src/tutorial/body/tutorial001.py") == "example"
    assert classify_role("samples/demo_app.ts") == "example"
    assert classify_role("tutorials/intro.py") == "example"
    assert classify_role("demo/main.go") == "example"


def test_classify_role_example_precedence() -> None:
    """DEC-049. example sits BELOW the excluded roles: a test/generated file
    inside an examples/ tree keeps its stronger role."""
    assert classify_role("examples/test_quickstart.py") == "test"
    assert classify_role("examples/model.g.dart") == "generated"
    assert classify_role("examples/fixtures/data.py") == "fixture"
    assert classify_role("third_party/examples/lib.py") == "vendored"


def test_inventory_assigns_vendored_and_generated(tmp_path: Path) -> None:
    """End-to-end: vendored + generated land in their own buckets and are
    NOT counted in language_breakdown (which is production-source only)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "third_party").mkdir()
    (tmp_path / "third_party" / "lib.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "model.g.dart").write_text("class _Foo {}\n", encoding="utf-8")
    inv = take_inventory(tmp_path)
    paths = {item.rel_path: item.role for item in inv.files}
    assert paths == {
        "src/main.py": "source",
        "third_party/lib.py": "vendored",
        "lib/model.g.dart": "generated",
    }
    assert inv.language_breakdown == {"python": 1}
    assert len(inv.vendored_files) == 1
    assert len(inv.generated_files) == 1


def test_inventory_example_role_in_graph_files_not_source(tmp_path: Path) -> None:
    """DEC-049: example files are in graph_files (fed to the graph) but NOT in
    source_files / language_breakdown (production count stays source-only)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "demo.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("z = 3\n", encoding="utf-8")
    inv = take_inventory(tmp_path)

    assert len(inv.example_files) == 1
    assert len(inv.source_files) == 1  # production source only
    assert inv.language_breakdown == {"python": 1}  # example not counted
    # graph_files = source ∪ example (test excluded).
    graph_paths = {item.rel_path for item in inv.graph_files}
    assert graph_paths == {"src/main.py", "examples/demo.py"}


def test_inventory_detects_generated_by_marker(tmp_path: Path) -> None:
    """DEC-021. A file whose path looks source but whose first ~512 bytes
    say "GENERATED / DO NOT EDIT" gets reclassified."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "# Code generated by genny. DO NOT EDIT.\nx = 1\n", encoding="utf-8"
    )
    (tmp_path / "src" / "real.py").write_text("# normal code\ny = 2\n", encoding="utf-8")
    inv = take_inventory(tmp_path)
    by_path = {item.rel_path: item.role for item in inv.files}
    assert by_path == {"src/main.py": "generated", "src/real.py": "source"}


def test_inventory_assigns_roles(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "tests" / "fixtures").mkdir()
    (tmp_path / "tests" / "fixtures" / "sample.py").write_text("z = 3\n", encoding="utf-8")

    inventory = take_inventory(tmp_path)
    assert {item.rel_path for item in inventory.source_files} == {"src/main.py"}
    assert {item.rel_path for item in inventory.test_files} == {"tests/test_main.py"}
    assert {item.rel_path for item in inventory.fixture_files} == {"tests/fixtures/sample.py"}
    # language_breakdown counts production source only (DEC-012)
    assert inventory.language_breakdown == {"python": 1}
