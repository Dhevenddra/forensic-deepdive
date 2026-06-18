"""CLI package.

The Typer app lives in :mod:`forensic_deepdive.cli.app` (re-exported here so the
``forensic_deepdive.cli:app`` entry point and ``from forensic_deepdive.cli import app``
keep working). The Console-only presentation layer (DEC-078, v0.7 Track B) lives in
:mod:`forensic_deepdive.cli.style`.
"""

from forensic_deepdive.cli.app import app

__all__ = ["app"]
