"""Packaging contract guards (DEC-088).

These catch the class of bug that only shows up in a *built wheel*, not an
editable/dev install:

- the vendored UI assets must resolve via ``importlib.resources`` (the mechanism
  the served HTTP handler now uses), so they're found however the package is
  installed;
- the console-script entry-point target must import;
- the tree-sitter / language-pack ABI pair must interoperate (a clean install of
  a mismatched pair raised ``ModuleNotFoundError`` then a ``Language``/``Parser``
  ABI ``TypeError`` — DEC-088).

The full clean-room check (build the wheel, install into a fresh venv, run
``forensic info`` + ``extract``) is done in CI on three platforms; these unit
guards keep the import-surface contract from regressing between those runs.
"""

from __future__ import annotations

from importlib.resources import files


def test_ui_assets_resolve_via_importlib_resources() -> None:
    """index.html + the vendored Sigma.js/graphology bundles must be reachable as
    package resources (not via __file__ path math)."""
    assets = files("forensic_deepdive.serve").joinpath("assets")
    assert assets.joinpath("index.html").is_file()
    assert assets.joinpath("app.js").is_file()
    assert assets.joinpath("app.css").is_file()
    vendor = assets.joinpath("vendor")
    assert vendor.joinpath("sigma.min.js").is_file()
    assert vendor.joinpath("graphology.umd.min.js").is_file()


def test_http_server_assets_dir_is_resolved_and_present() -> None:
    """The module global the handler actually serves from must point at a real
    directory containing the entry page."""
    from forensic_deepdive.serve.http_server import ASSETS_DIR

    assert ASSETS_DIR.is_dir()
    assert (ASSETS_DIR / "index.html").is_file()


def test_console_script_entrypoint_imports() -> None:
    """`[project.scripts] forensic = "forensic_deepdive.cli:app"` must import."""
    from forensic_deepdive.cli import app

    assert app is not None


def test_tree_sitter_abi_pair_interoperates() -> None:
    """The standalone tree-sitter Parser must accept the language-pack's Language
    (the DEC-088 ABI-pair regression) and the 0.25+ Query API must exist."""
    from tree_sitter import Parser, Query, QueryCursor  # noqa: F401 — import is the assertion

    from forensic_deepdive.static.parse import parse_source

    tree = parse_source(b"def f():\n    return 1\n", "python")
    assert tree.root_node.type == "module"
