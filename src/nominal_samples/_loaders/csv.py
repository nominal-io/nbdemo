from __future__ import annotations

from typing import Any

from nominal_samples._loaders import require


def dataframe(dataset: Any) -> Any:
    """Read the CSV, indexed by the column named in the manifest's ``[tabular] index``, as timestamps."""
    pd = require("pandas", "pandas")
    index = dataset.manifest.get("tabular", {}).get("index")
    if index is None:
        return pd.read_csv(dataset.path)
    return pd.read_csv(dataset.path, index_col=index, parse_dates=[index])
