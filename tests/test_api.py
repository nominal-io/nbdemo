import subprocess
import sys

import pytest

import nbdemo.data as nd
from nbdemo.data import FormUnavailable


def test_importing_reads_no_loader_libraries():
    code = (
        "import sys, nbdemo.data as nd\n"
        "from nbdemo.data.med import ecg_mitbih_119\n"
        "nd.catalog()\n"
        "print(sorted({'pandas', 'wfdb', 'sigmf', 'numpy'} & set(sys.modules)))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"


def test_namespace_and_get_return_the_same_dataset():
    from nbdemo.data.med import ecg_mitbih_119

    assert nd.get("med/ecg_mitbih_119") is ecg_mitbih_119
    assert nd.med.ecg_mitbih_119 is ecg_mitbih_119


def test_dir_lists_datasets():
    assert "flight_dc" in dir(nd.aero)


def test_unknown_dataset_lists_the_known_ones():
    with pytest.raises(AttributeError, match="ecg_mitbih_119"):
        nd.med.nope


def test_bundled_dataset_path_is_in_the_package():
    path = nd.med.ecg_mitbih_119.path
    assert path.name == "119.hea" and path.exists()
    assert set(nd.med.ecg_mitbih_119.paths) == {"119.hea", "119.dat", "119.atr"}


def test_unavailable_form_is_an_attribute_error_with_a_reason():
    assert not hasattr(nd.rf.sigmf_synthetic, "df")
    with pytest.raises(FormUnavailable, match="binary IQ"):
        nd.rf.sigmf_synthetic.df
    assert not hasattr(nd.aero.flight_dc, "native")


def test_forms():
    assert nd.med.ecg_mitbih_119.forms == ("path", "native", "df")
    assert nd.rf.sigmf_synthetic.forms == ("path", "native")
