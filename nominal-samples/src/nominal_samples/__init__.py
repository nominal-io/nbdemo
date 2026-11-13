"""Sample datasets for Nominal's open-source projects.

Datasets are grouped by domain: :py:mod:`~nominal_samples.aero`, :py:mod:`~nominal_samples.med` and
:py:mod:`~nominal_samples.rf`.
Import one from its domain; each has a path, and where it makes sense a native object and a DataFrame::

    from nominal_samples.med import ecg_mitbih_119

    ecg_mitbih_119.path    # a Path, to pass to your own loader
    ecg_mitbih_119.native  # a wfdb.Record
    ecg_mitbih_119.df      # a pandas.DataFrame
"""

from __future__ import annotations

from nominal_samples import _domain, aero, med, rf
from nominal_samples._dataset import Dataset, FileSpec
from nominal_samples._errors import (
    ChecksumError,
    FormUnavailable,
    ManifestError,
    MissingExtraError,
    SamplesError,
)
from nominal_samples._fetch import cache_dir

__all__ = [
    "ChecksumError",
    "Dataset",
    "FileSpec",
    "FormUnavailable",
    "ManifestError",
    "MissingExtraError",
    "SamplesError",
    "aero",
    "cache_dir",
    "catalog",
    "domains",
    "get",
    "med",
    "rf",
]


def domains() -> list[str]:
    """Return the names of the domains."""
    return _domain.domains()


def catalog(domain: str | None = None) -> list[Dataset]:
    """Return every dataset, or the datasets of one domain.

    Args:
        domain: A domain name such as ``"rf"``; ``None`` for all domains.

    Returns:
        The datasets, ordered by domain and name. Reads manifests only; nothing is downloaded.
    """
    return [_domain.get(d, n) for d in ([domain] if domain else _domain.domains()) for n in _domain.names(d)]


def get(dataset_id: str) -> Dataset:
    """Return a dataset by its ``"<domain>/<name>"``, for when the name is only known at run time.

    Args:
        dataset_id: For example ``"med/ecg_mitbih_119"``.

    Raises:
        AttributeError: There is no such dataset.
    """
    domain, _, name = dataset_id.partition("/")
    return _domain.get(domain, name)
