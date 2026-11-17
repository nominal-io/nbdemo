---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Adding a dataset

{.lead}
A dataset is a folder with a `dataset.toml` and its small files, in the folder of its domain. This page
builds one in a temporary folder and loads it.

Put a dataset in the package at `src/nbdemo/data/<domain>/<name>/`. The domain is `aero`, `med` or `rf`.
The name is the Python name that users import.

## Write the files and the manifest

Files up to about 1 MB ship in the package. A larger file is not in the repository: its manifest entry has
a `url` and the file downloads on first use.

```{code-cell} ipython3
import hashlib
import tempfile
from pathlib import Path

folder = Path(tempfile.mkdtemp()) / "bench_voltage"
folder.mkdir()
(folder / "voltage.csv").write_text(
    "time,volts\n2026-01-01T12:00:00Z,3.30\n2026-01-01T12:00:01Z,3.31\n"
)
```

`just hash-files <folder>` prints the `[[files]]` entries. This cell computes the same values:

```{code-cell} ipython3
data = (folder / "voltage.csv").read_bytes()
digest = hashlib.sha256(data).hexdigest()

(folder / "dataset.toml").write_text(f"""\
description = "Two readings of a 3.3 V rail"
license = "Apache-2.0"
source = "Written by hand for this page"
version = 1

[forms]
dataframe = "csv"

[unavailable]
native = "a CSV file has no object of its own; use .df"

[tabular]
index = "time"

[[files]]
name = "voltage.csv"
primary = true
sha256 = "{digest}"
size = {len(data)}
""")
```

The fields:

- `description`, `license` and `source` are required. A license that asks for credit, such as `CC-BY-4.0`,
  also needs an `attribution`.
- `version` goes up when a file's content changes. Downloads are cached by version.
- `[[files]]` lists every file, with exactly one `primary`. `path` is that file.
- `[forms]` names a loader for `native` and `dataframe`. The loaders are `wfdb`, `sigmf` and `csv`. Leave a
  form out if the format has none, and say why under `[unavailable]`.

## Load it

`Dataset.from_dir` reads any folder with a manifest and checks it, so you can try it before adding it to
the package.

```{code-cell} ipython3
from nbdemo.data import Dataset

dataset = Dataset.from_dir(folder, domain="aero")
dataset.df
```

`verify` compares the files with their manifest entries, as the tests do for every dataset:

```{code-cell} ipython3
dataset.verify()  # an empty list: every file matches
```

## Generated data

Data that a script makes goes with the script. Put the script in `gen/`, add a `[generated]` table to the
manifest with its `script`, `seed` and `command`, and check in the output. `gen/aero_flight_dc.py` makes
`aero/flight_dc`, and a test reruns it to confirm that it reproduces the checked-in file:

```{code-cell} ipython3
import nbdemo.data as nd

nd.aero.flight_dc.manifest["generated"]
```
