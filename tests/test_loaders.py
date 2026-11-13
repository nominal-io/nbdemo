import pytest

import nominal_samples as ns


def test_flight_df():
    pytest.importorskip("pandas")
    df = ns.aero.flight_dc.df
    assert df.shape == (600, 15)
    assert df.index.name == "time" and str(df.index.dtype).startswith("datetime64")
    assert df.index[0].isoformat() == "2026-01-01T12:00:00+00:00"


def test_ecg_native_and_df():
    pytest.importorskip("wfdb")
    pytest.importorskip("pandas")
    record = ns.med.ecg_mitbih_119.native
    assert record.fs == 360 and record.sig_name == ["MLII", "V1"]
    df = ns.med.ecg_mitbih_119.df
    assert len(df) == 21600
    assert set(df["beat"].dropna()) >= {"N", "V"}


def test_a_dataset_caches_its_native_object():
    pytest.importorskip("wfdb")
    assert ns.med.ecg_mitbih_119.native is ns.med.ecg_mitbih_119.native
