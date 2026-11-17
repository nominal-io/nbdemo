---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Using the paths

{.lead}
`path` is the main file of a dataset, as a `pathlib.Path`. Use it to test a file loader against a real file.

```{code-cell} ipython3
from nbdemo.data.aero import flight_dc

flight_dc.path
```

Pass it to the loader you are testing. This one is `pandas.read_csv`:

```{code-cell} ipython3
import pandas as pd

pd.read_csv(flight_dc.path).head(3)
```

## Datasets with several files

Some formats keep their data in more than one file. For `ecg_mitbih_119`, `path` is the header, and the
signals and annotations are beside it. `paths` lists all of them by name:

```{code-cell} ipython3
from nbdemo.data.med import ecg_mitbih_119

ecg_mitbih_119.paths
```

The files are in one folder, so a loader that finds the other files from the main file works unchanged:

```{code-cell} ipython3
import wfdb

wfdb.rdrecord(str(ecg_mitbih_119.path.with_suffix(""))).sig_name
```

## Large files

Using `path` or `paths` downloads whatever is missing. The `.sigmf-data` file of `sigmf_synthetic` is 8 MB,
so it downloads the first time, to the cache. `is_local` says whether a dataset's files are all present:

```{code-cell} ipython3
:tags: [remove-cell]

import os
import tempfile

# Start from an empty cache, so the download below happens on every build of this page.
os.environ["NBDEMO_CACHE"] = tempfile.mkdtemp()
```

```{code-cell} ipython3
from nbdemo.data.rf import sigmf_synthetic

print(sigmf_synthetic.is_local)  # False until a path is used
meta = sigmf_synthetic.path  # downloads the recording
print(sigmf_synthetic.is_local)
sorted(p.name for p in meta.parent.iterdir())
```
