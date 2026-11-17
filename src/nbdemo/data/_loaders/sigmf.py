"""A minimal SigMF reader: JSON metadata plus numpy samples.

This stands in for the ``sigmf`` package (LGPL-3.0) until we decide whether to depend on it. It handles
complex recordings whose ``core:datatype`` is one of ``_DTYPES``; it does not check the data's checksum, because
the metadata of IQEngine's ``synthetic`` recording does not match its data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nbdemo.data._loaders import require

# core:datatype -> (numpy dtype of one component, True if the integers are signed, scale to +-1.0 or None)
_DTYPES: dict[str, tuple[str, float | None]] = {
    "cf32_le": ("<f4", None),
    "cf32_be": (">f4", None),
    "ci16_le": ("<i2", 32768.0),
    "ci16_be": (">i2", 32768.0),
    "ci8": ("i1", 128.0),
    "cu8": ("u1", None),
}


@dataclass(frozen=True)
class SigMFRecording:
    """A SigMF recording: its metadata and a path to its samples. ``read_samples()`` loads them."""

    meta_path: Path
    global_info: dict[str, Any]
    captures: list[dict[str, Any]]
    annotations: list[dict[str, Any]]

    @property
    def data_path(self) -> Path:
        return self.meta_path.with_suffix(".sigmf-data")

    @property
    def sample_rate(self) -> float:
        return float(self.global_info["core:sample_rate"])

    def get_global_field(self, name: str, default: Any = None) -> Any:
        return self.global_info.get(name, default)

    def read_samples(self) -> Any:
        """Return the recording's samples as a one-dimensional ``complex64`` numpy array."""
        np = require("numpy", "rf")
        datatype = self.global_info["core:datatype"]
        if datatype not in _DTYPES:
            raise ValueError(f"unsupported core:datatype {datatype!r}; supported: {', '.join(_DTYPES)}")
        component, scale = _DTYPES[datatype]
        raw = np.fromfile(self.data_path, dtype=component).astype("float32")
        if datatype == "cu8":
            raw = (raw - 127.5) / 127.5
        elif scale:
            raw = raw / scale
        return (raw[0::2] + 1j * raw[1::2]).astype("complex64")


def native(dataset: Any) -> SigMFRecording:
    """Read the recording as a :py:class:`SigMFRecording`; call its ``read_samples()`` for the IQ samples."""
    path = Path(dataset.path)
    meta = json.loads(path.read_text())
    return SigMFRecording(
        meta_path=path,
        global_info=meta["global"],
        captures=meta.get("captures", []),
        annotations=meta.get("annotations", []),
    )
