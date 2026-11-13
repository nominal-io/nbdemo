from __future__ import annotations

from typing import Any

from nbdemo.data._loaders import require


def native(dataset: Any) -> Any:
    """Read the recording as a ``sigmf.SigMFFile``; call its ``read_samples()`` for the IQ samples.

    The checksum is not checked, because the metadata of IQEngine's ``synthetic`` recording does not match
    its data.
    """
    sigmffile = require("sigmf.sigmffile", "sigmf")
    return sigmffile.fromfile(str(dataset.path), skip_checksum=True)
