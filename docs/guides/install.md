---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.6
kernelspec:
  name: python3
  display_name: Python 3 (ipykernel)
  language: python
---

# Install

{.lead}
The package has no dependencies of its own. Each format's library is an extra that you install when you
read that format.

```bash
pip install nominal-samples                 # paths only
pip install 'nominal-samples[med]'          # + wfdb and pandas
pip install 'nominal-samples[rf]'           # + sigmf
pip install 'nominal-samples[aero]'         # + pandas
pip install 'nominal-samples[all]'
```

With `uv`, use `uv add 'nominal-samples[med]'`.

The extras set minimum versions only, such as `pandas>=2.0`, so they do not conflict with the versions your
project pins.

## What needs an extra

Paths work with no extras. `native` and `df` import their library the first time you use them. Without it
installed, they raise an error that names the extra to install:

```{code-cell} ipython3
import sys

import nominal_samples as ns
from nominal_samples import MissingExtraError

sys.modules["wfdb"] = None  # stands in for a project that did not install the extra

try:
    ns.med.ecg_mitbih_119.native
except MissingExtraError as error:
    print(error)
```

## Where downloads go

Most files ship in the package. A larger file downloads the first time you use its dataset, and is checked
against the sha256 in the dataset's manifest. Downloads go in `NOMINAL_SAMPLES_CACHE`, or in
`$XDG_CACHE_HOME/nominal-samples` (`~/.cache/nominal-samples` by default). `nominal_samples.cache_dir()`
returns the folder in use.

When a dataset is hosted in a private GitHub repository, set `NOMINAL_SAMPLES_TOKEN` or `GITHUB_TOKEN` to a
token that can read it. The token is sent only to GitHub.
