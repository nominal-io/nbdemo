import pytest

import nbdemo.data as nd
from nbdemo.data import Dataset, ManifestError

DATASETS = nd.catalog()


def test_domains():
    assert nd.domains() == ["aero", "med", "rf"]


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda d: d.id)
def test_present_files_match_manifest(dataset):
    assert dataset.verify() == []


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda d: d.id)
def test_has_license_and_source(dataset):
    assert dataset.license and dataset.source


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda d: d.id)
def test_generated_data_names_its_script(dataset):
    generated = dataset.manifest.get("generated")
    assert generated is None or generated["script"]


def write(tmp_path, text, files=()):
    folder = tmp_path / "demo"
    folder.mkdir()
    for name in files:
        (folder / name).write_text("x")
    (folder / "dataset.toml").write_text(text)
    return folder


BASE = 'description = "d"\nlicense = "Apache-2.0"\nsource = "s"\nversion = 1\n'
FILE = '[[files]]\nname = "a.csv"\nsha256 = "0"\nsize = 1\nprimary = true\n'


def test_from_dir(tmp_path):
    assert Dataset.from_dir(write(tmp_path, BASE + FILE, ["a.csv"])).name == "demo"


def test_missing_field(tmp_path):
    with pytest.raises(ManifestError, match="missing source"):
        Dataset.from_dir(write(tmp_path, BASE.replace('source = "s"\n', "") + FILE, ["a.csv"]))


def test_attribution_required_for_attribution_licenses(tmp_path):
    text = BASE.replace("Apache-2.0", "CC-BY-4.0") + FILE
    with pytest.raises(ManifestError, match="attribution"):
        Dataset.from_dir(write(tmp_path, text, ["a.csv"]))


def test_missing_file_needs_url(tmp_path):
    with pytest.raises(ManifestError, match="needs a url"):
        Dataset.from_dir(write(tmp_path, BASE + FILE))


def test_exactly_one_primary(tmp_path):
    with pytest.raises(ManifestError, match="primary"):
        Dataset.from_dir(write(tmp_path, BASE + FILE.replace("primary = true", ""), ["a.csv"]))


def test_unknown_loader(tmp_path):
    with pytest.raises(ManifestError, match="loader"):
        Dataset.from_dir(write(tmp_path, BASE + '[forms]\nnative = "nope"\n' + FILE, ["a.csv"]))
