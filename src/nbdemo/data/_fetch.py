"""Download files into the cache, checking their sha256."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from nbdemo.data._errors import ChecksumError

_CHUNK = 1 << 20
_TOKEN_VARS = ("NBDEMO_TOKEN", "GITHUB_TOKEN")
_GITHUB_HOSTS = {"github.com", "api.github.com"}


def cache_dir() -> Path:
    """Return the directory that fetched files are saved in.

    It is ``$NBDEMO_CACHE`` if set, otherwise ``nbdemo`` in ``$XDG_CACHE_HOME``
    (``~/.cache`` by default).

    Returns:
        The cache directory. It may not exist yet.
    """
    override = os.environ.get("NBDEMO_CACHE")
    if override:
        return Path(override)
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "nbdemo"


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _request(url: str) -> Request:
    headers = {"User-Agent": "nbdemo"}
    token = next((os.environ[var] for var in _TOKEN_VARS if os.environ.get(var)), None)
    if token and urlparse(url).hostname in _GITHUB_HOSTS:  # a private repo's release assets
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/octet-stream"
    return Request(url, headers=headers)


def download(url: str, dest: Path, sha256: str) -> None:
    """Download ``url`` to ``dest``, keeping nothing if the sha256 does not match.

    The file is written beside ``dest`` and moved into place once it is complete and checked, so a failed
    or interrupted download never leaves a partial file.

    Args:
        url: The HTTPS address to download.
        dest: Where to save the file. Its folder is created if needed.
        sha256: The expected hex digest of the file.

    Raises:
        ChecksumError: The downloaded bytes do not have the expected digest.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    try:
        with urlopen(_request(url)) as response, tmp.open("wb") as file:
            while chunk := response.read(_CHUNK):
                digest.update(chunk)
                file.write(chunk)
        if digest.hexdigest() != sha256:
            raise ChecksumError(f"{url}: expected sha256 {sha256}, got {digest.hexdigest()}")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
