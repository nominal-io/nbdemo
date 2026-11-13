from __future__ import annotations

from typing import Any

from nominal_samples._loaders import require


def native(dataset: Any) -> Any:
    """Read the record as a ``wfdb.Record``."""
    wfdb = require("wfdb", "wfdb")
    return wfdb.rdrecord(str(dataset.path.with_suffix("")))


def dataframe(dataset: Any) -> Any:
    """Read the signals in physical units, indexed by seconds, with the beat annotations in ``beat``."""
    wfdb = require("wfdb", "wfdb")
    pd = require("pandas", "pandas")
    base = str(dataset.path.with_suffix(""))
    record = wfdb.rdrecord(base)
    frame = pd.DataFrame(record.p_signal, columns=record.sig_name)
    frame.index = pd.Index(frame.index / record.fs, name="time")
    annotation = wfdb.rdann(base, "atr")
    beats = pd.Series(annotation.symbol, index=annotation.sample)
    frame["beat"] = beats.reindex(range(len(frame))).to_numpy()  # a symbol at the beat's sample, else missing
    return frame
