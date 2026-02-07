"""Version helper – single source of truth via ``importlib.metadata``.

Usage::

    from maylang_cli._version import __version__
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("maylang-cli")
except PackageNotFoundError:  # pragma: no cover – editable / dev installs
    __version__ = "0.0.0-dev"
