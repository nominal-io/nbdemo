"""The aero datasets. Import one by name; see :py:func:`nbdemo.data.catalog` for the list."""

from __future__ import annotations

from nbdemo.data import _domain
from nbdemo.data._dataset import Dataset


def __getattr__(name: str) -> Dataset:
    if name.startswith("__"):
        raise AttributeError(name)
    return _domain.get(__name__.rpartition(".")[2], name)


def __dir__() -> list[str]:
    return _domain.names(__name__.rpartition(".")[2])
