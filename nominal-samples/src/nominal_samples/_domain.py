from __future__ import annotations

from pathlib import Path

from nominal_samples._dataset import Dataset

_ROOT = Path(__file__).parent
_cache: dict[tuple[str, str], Dataset] = {}


def domains() -> list[str]:
    """Return the names of the domains, such as ``"aero"``."""
    return sorted(
        p.name for p in _ROOT.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").exists()
    )


def names(domain: str) -> list[str]:
    """Return the names of the datasets in a domain."""
    return sorted(p.parent.name for p in (_ROOT / domain).glob("*/dataset.toml"))


def get(domain: str, name: str) -> Dataset:
    """Return a dataset, reading its manifest the first time.

    Raises:
        AttributeError: There is no such dataset.
    """
    key = (domain, name)
    if key not in _cache:
        folder = _ROOT / domain / name
        if not (folder / "dataset.toml").exists():
            raise AttributeError(
                f"nominal_samples.{domain} has no dataset {name!r}; it has: {', '.join(names(domain))}"
            )
        _cache[key] = Dataset(domain, folder)
    return _cache[key]
