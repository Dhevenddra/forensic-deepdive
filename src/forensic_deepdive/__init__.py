"""forensic-deepdive: produce 5 durable markdown artifacts for any codebase."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: the installed package metadata (from pyproject).
    # Avoids the v0.1→v0.3 drift where this literal was never bumped.
    __version__ = version("forensic-deepdive")
except PackageNotFoundError:  # running from a source tree without metadata
    __version__ = "0.5.0"
