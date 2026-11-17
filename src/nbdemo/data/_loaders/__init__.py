"""Loaders, one module per file format.

A loader module defines ``native(dataset)`` and/or ``dataframe(dataset)``. A dataset's ``[forms]`` table
names the module for each. Modules import their libraries inside those functions, so importing a loader
never needs an extra.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

from nbdemo.data._errors import MissingExtraError

FORMATS = ("wfdb", "sigmf", "csv")


def get(kind: str, fmt: str) -> Callable[[Any], Any]:
    """Return the ``native`` or ``dataframe`` function of a format's loader."""
    return getattr(import_module(f"nbdemo.data._loaders.{fmt}"), kind)  # type: ignore[no-any-return]


def require(module: str, extra: str) -> Any:
    """Import ``module``, or raise :py:class:`~nbdemo.data.MissingExtraError` naming the extra that installs it."""
    try:
        return import_module(module)
    except ImportError as error:
        raise MissingExtraError(f"{module} is not installed; install it with: pip install 'nbdemo[{extra}]'") from error
