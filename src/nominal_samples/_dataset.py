from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from nominal_samples import _loaders
from nominal_samples._errors import FormUnavailable, ManifestError
from nominal_samples._fetch import cache_dir, download, sha256_of

_REQUIRED = ("description", "license", "source", "version", "files")
_ATTRIBUTION_LICENSES = ("CC-BY", "ODC-By")  # licenses that require crediting the author


@dataclass(frozen=True)
class FileSpec:
    """One file of a dataset, as the manifest lists it."""

    name: str
    sha256: str
    size: int
    url: str | None = None
    """Where to download the file from. ``None`` for a file that ships in the package."""


class Dataset:
    """A sample dataset: its files, and the forms they can be read in.

    Get one by importing it from its domain, which reads only its manifest::

        from nominal_samples.med import ecg_mitbih_119

        ecg_mitbih_119.path    # a Path, to pass to your own loader
        ecg_mitbih_119.native  # a wfdb.Record
        ecg_mitbih_119.df      # a pandas.DataFrame

    Nothing is downloaded or parsed until you use ``path``, ``paths``, ``native`` or ``df``. Files that do
    not ship in the package are downloaded on first use and kept in `~nominal_samples.cache_dir`.

    Args:
        domain: The domain the dataset is in, such as ``"med"``.
        root: The folder holding ``dataset.toml`` and the files that ship in the package.
    """

    def __init__(self, domain: str, root: Path) -> None:
        self.domain = domain
        self.root = root
        self.name = root.name
        manifest_path = root / "dataset.toml"
        try:
            self.manifest: dict[str, Any] = tomllib.loads(manifest_path.read_text())
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ManifestError(f"{manifest_path}: {error}") from error
        self._validate()
        self.description: str = self.manifest["description"]
        self.license: str = self.manifest["license"]
        self.source: str = self.manifest["source"]
        self.attribution: str = self.manifest.get("attribution", "")
        self.version: int = self.manifest["version"]
        self.files = tuple(FileSpec(f["name"], f["sha256"], f["size"], f.get("url")) for f in self.manifest["files"])
        primary = [f["name"] for f in self.manifest["files"] if f.get("primary")]
        self._primary = primary[0]

    @classmethod
    def from_dir(cls, root: str | Path, domain: str = "local") -> Dataset:
        """Read a dataset from any folder that holds a ``dataset.toml``.

        Use it to try a manifest before adding the dataset to the package.

        Args:
            root: The dataset's folder; its name is the dataset's name.
            domain: A label for the dataset's domain.

        Raises:
            ManifestError: The manifest is missing a field or has an invalid one.
        """
        return cls(domain, Path(root))

    def _validate(self) -> None:
        where = f"{self.root / 'dataset.toml'}"
        missing = [key for key in _REQUIRED if key not in self.manifest]
        if missing:
            raise ManifestError(f"{where}: missing {', '.join(missing)}")
        if self.manifest["license"].startswith(_ATTRIBUTION_LICENSES) and not self.manifest.get("attribution"):
            raise ManifestError(f"{where}: license {self.manifest['license']} requires an attribution")
        files = self.manifest["files"]
        if not files or sum(bool(f.get("primary")) for f in files) != 1:
            raise ManifestError(f"{where}: exactly one file must have primary = true")
        for f in files:
            if not {"name", "sha256", "size"} <= f.keys():
                raise ManifestError(f"{where}: each file needs name, sha256 and size ({f.get('name')})")
            if not (self.root / f["name"]).exists() and "url" not in f:
                raise ManifestError(f"{where}: {f['name']} is not in the dataset folder, so it needs a url")
        forms = self.manifest.get("forms", {})
        for kind in ("native", "dataframe"):
            if kind in forms and forms[kind] not in _loaders.FORMATS:
                raise ManifestError(f"{where}: unknown {kind} loader {forms[kind]!r}")

    @property
    def id(self) -> str:
        """The dataset's ``<domain>/<name>``."""
        return f"{self.domain}/{self.name}"

    @property
    def size(self) -> int:
        """The total size of the dataset's files, in bytes."""
        return sum(f.size for f in self.files)

    @property
    def is_local(self) -> bool:
        """Whether every file is present, so using the dataset downloads nothing."""
        return all(self._local(f) is not None for f in self.files)

    @property
    def forms(self) -> tuple[str, ...]:
        """The forms this dataset has. ``path`` is always one; ``native`` and ``df`` are where they apply."""
        found = ["path"]
        if "native" in self.manifest.get("forms", {}):
            found.append("native")
        if "dataframe" in self.manifest.get("forms", {}):
            found.append("df")
        return tuple(found)

    def _local(self, spec: FileSpec) -> Path | None:
        for folder in (self.root, self._cache):
            candidate = folder / spec.name
            if candidate.exists():
                return candidate
        return None

    @property
    def _cache(self) -> Path:
        return cache_dir() / self.domain / self.name / f"v{self.version}"

    @cached_property
    def paths(self) -> dict[str, Path]:
        """Every file of the dataset, by name, downloading any that are missing.

        The files are in one folder, so a loader can find companions such as a ``.hea`` beside its ``.dat``.
        """
        if all((self.root / f.name).exists() for f in self.files):
            return {f.name: self.root / f.name for f in self.files}
        # Some files are downloaded, so put them all in the cache folder, beside each other.
        for spec in self.files:
            dest = self._cache / spec.name
            if dest.exists():
                continue
            if (self.root / spec.name).exists():
                self._cache.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.root / spec.name, dest)
            else:
                assert spec.url is not None
                download(spec.url, dest, spec.sha256)
        return {f.name: self._cache / f.name for f in self.files}

    @cached_property
    def path(self) -> Path:
        """The path of the dataset's main file, downloading the dataset's files if needed.

        The other files are beside it; see `paths`.
        """
        return self.paths[self._primary]

    def _form(self, kind: str, attribute: str) -> Any:
        loader = self.manifest.get("forms", {}).get(kind)
        if loader is None:
            reason = self.manifest.get("unavailable", {}).get(kind, "it has no such form")
            raise FormUnavailable(f"{self.id} has no {attribute}: {reason}. Its forms: {', '.join(self.forms)}")
        return _loaders.get(kind, loader)(self)

    @cached_property
    def native(self) -> Any:
        """The dataset as its format's own Python object, such as a ``wfdb.Record``.

        Raises:
            FormUnavailable: The format has no such object here.
            MissingExtraError: The library that reads the format is not installed.
        """
        return self._form("native", "native")

    @cached_property
    def df(self) -> Any:
        """The dataset as a ``pandas.DataFrame``.

        Raises:
            FormUnavailable: The data is not tabular, such as binary samples.
            MissingExtraError: pandas, or the library that reads the format, is not installed.
        """
        return self._form("dataframe", "df")

    def verify(self) -> list[str]:
        """Check the files that are present against the manifest.

        Returns:
            A description of each problem found; empty if every present file matches.
        """
        problems = []
        for spec in self.files:
            local = self._local(spec)
            if local is None:
                continue
            if local.stat().st_size != spec.size:
                problems.append(f"{spec.name}: size {local.stat().st_size}, manifest says {spec.size}")
            elif sha256_of(local) != spec.sha256:
                problems.append(f"{spec.name}: sha256 differs from the manifest")
        return problems

    def __repr__(self) -> str:
        state = "local" if self.is_local else "not downloaded"
        return f"Dataset({self.id!r}, {self.size / 1e6:.2f} MB, {state}, forms={self.forms})"
