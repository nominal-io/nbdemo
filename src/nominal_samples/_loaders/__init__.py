"""Loaders, one module per file format.

A loader module defines ``native(dataset)`` and/or ``dataframe(dataset)``. A dataset's ``[forms]`` table
names the module for each. Modules import their libraries inside those functions, so importing a loader
never needs an extra.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

from nominal_samples._errors import MissingExtraError

FORMATS = ("wfdb", "sigmf", "csv")


def get(kind: str, fmt: str) -> Callable[[Any], Any]:
    """Return the ``native`` or ``dataframe`` function of a format's loader."""
    return getattr(import_module(f"nominal_samples._loaders.{fmt}"), kind)  # type: ignore[no-any-return]


def require(module: str, extra: str) -> Any:
    """Import ``module``, or raise `MissingExtraError` naming the extra that installs it."""
    try:
        return import_module(module)
    except ImportError as error:
        raise MissingExtraError(
            f"{module} is not installed; install it with: pip install 'nominal-samples[{extra}]'"
        ) from error
