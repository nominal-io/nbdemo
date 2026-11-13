import hashlib
import io
from urllib.error import URLError

import pytest

from nominal_samples import ChecksumError, Dataset, _fetch

DATA = b"0123456789" * 1000
DIGEST = hashlib.sha256(DATA).hexdigest()


@pytest.fixture
def served(monkeypatch):
    """Serve DATA for any URL, recording the requests."""
    requests = []

    def fake_urlopen(request):
        requests.append(request)
        return io.BytesIO(DATA)

    monkeypatch.setattr(_fetch, "urlopen", fake_urlopen)
    return requests


def test_download_writes_the_file(tmp_path, served):
    dest = tmp_path / "a" / "file.bin"
    _fetch.download("https://example.com/file.bin", dest, DIGEST)
    assert dest.read_bytes() == DATA
    assert not list(dest.parent.glob("*.part"))


def test_a_wrong_checksum_leaves_nothing(tmp_path, served):
    dest = tmp_path / "file.bin"
    with pytest.raises(ChecksumError):
        _fetch.download("https://example.com/file.bin", dest, "0" * 64)
    assert list(tmp_path.iterdir()) == []


def test_a_failed_download_leaves_nothing(tmp_path, monkeypatch):
    def fail(request):
        raise URLError("offline")

    monkeypatch.setattr(_fetch, "urlopen", fail)
    with pytest.raises(URLError):
        _fetch.download("https://example.com/file.bin", tmp_path / "file.bin", DIGEST)
    assert list(tmp_path.iterdir()) == []


def test_token_is_sent_only_to_github(monkeypatch):
    monkeypatch.setenv("NOMINAL_SAMPLES_TOKEN", "secret")
    assert _fetch._request("https://api.github.com/x").get_header("Authorization") == "Bearer secret"
    assert _fetch._request("https://example.com/x").get_header("Authorization") is None


def make_dataset(tmp_path):
    folder = tmp_path / "demo"
    folder.mkdir()
    (folder / "small.txt").write_bytes(b"small")
    (folder / "dataset.toml").write_text(
        'description = "d"\nlicense = "Apache-2.0"\nsource = "s"\nversion = 3\n'
        f'[[files]]\nname = "small.txt"\nsha256 = "{hashlib.sha256(b"small").hexdigest()}"\nsize = 5\nprimary = true\n'
        f'[[files]]\nname = "big.bin"\nsha256 = "{DIGEST}"\nsize = {len(DATA)}\nurl = "https://example.com/big.bin"\n'
    )
    return Dataset.from_dir(folder, domain="demo")


def test_dataset_downloads_on_first_use_and_puts_files_together(tmp_path, served, cache):
    dataset = make_dataset(tmp_path)
    assert not dataset.is_local and len(served) == 0  # building the dataset downloads nothing
    path = dataset.path
    assert path.parent == dataset.paths["big.bin"].parent == cache / "demo" / "demo" / "v3"
    assert path.read_bytes() == b"small" and dataset.paths["big.bin"].read_bytes() == DATA
    assert dataset.is_local and len(served) == 1
    assert dataset.verify() == []


def test_a_cached_file_is_not_downloaded_again(tmp_path, served):
    dataset = make_dataset(tmp_path)
    dataset.paths
    Dataset.from_dir(tmp_path / "demo", domain="demo").paths  # a fresh object, as in a new process
    assert len(served) == 1


@pytest.mark.network
def test_real_sigmf_download():
    import nominal_samples as ns

    assert ns.rf.sigmf_synthetic.path.exists()
    assert ns.rf.sigmf_synthetic.verify() == []
