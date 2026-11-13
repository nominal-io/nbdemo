import pytest


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    """Keep every test's downloads out of the real cache."""
    monkeypatch.setenv("NOMINAL_SAMPLES_CACHE", str(tmp_path / "cache"))
    return tmp_path / "cache"
