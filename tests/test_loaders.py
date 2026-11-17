import pytest

import nbdemo.data as nd


def test_flight_df():
    pytest.importorskip("pandas")
    df = nd.aero.flight_dc.df
    assert df.shape == (1200, 15)
    assert df.index.name == "time" and str(df.index.dtype).startswith("datetime64")
    assert df.index[0].isoformat() == "2026-01-01T12:00:00+00:00"


def test_ecg_native_and_df():
    pytest.importorskip("wfdb")
    pytest.importorskip("pandas")
    record = nd.med.ecg_mitbih_119.native
    assert record.fs == 360 and record.sig_name == ["MLII", "V1"]
    df = nd.med.ecg_mitbih_119.df
    assert len(df) == 21600
    assert set(df["beat"].dropna()) >= {"N", "V"}


def test_a_dataset_caches_its_native_object():
    pytest.importorskip("wfdb")
    assert nd.med.ecg_mitbih_119.native is nd.med.ecg_mitbih_119.native


def test_sigmf_native_reads_metadata_and_samples():
    pytest.importorskip("numpy")
    recording = nd.rf.sigmf_synthetic.native
    assert recording.sample_rate == 480000
    assert recording.get_global_field("core:datatype") == "cf32_le"
    assert len(recording.captures) == 3
    iq = recording.read_samples()
    assert iq.dtype.name == "complex64" and len(iq) == 1_000_000
