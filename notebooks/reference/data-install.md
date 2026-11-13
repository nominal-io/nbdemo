---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Install

{.lead}
`nbdemo.data` has no dependencies of its own. Each format's library is an extra that you install when you
read that format. `nbdemo` is not published to PyPI, so install it from its repository:

```bash
pip install 'nbdemo @ git+ssh://git@github.com/nominal-io/nbdemo.git'                # paths only
pip install 'nbdemo[med] @ git+ssh://git@github.com/nominal-io/nbdemo.git'           # + wfdb and pandas
pip install 'nbdemo[rf] @ git+ssh://git@github.com/nominal-io/nbdemo.git'            # + sigmf
pip install 'nbdemo[aero] @ git+ssh://git@github.com/nominal-io/nbdemo.git'          # + pandas
pip install 'nbdemo[all] @ git+ssh://git@github.com/nominal-io/nbdemo.git'
```

With `uv`, use `uv add 'nbdemo[med]' --git ssh://git@github.com/nominal-io/nbdemo.git`.
Inside this repository, `uv sync` installs it with every extra.

The extras set minimum versions only, such as `pandas>=2.0`, so they do not conflict with the versions your
project pins.

## What needs an extra

Paths work with no extras. `native` and `df` import their library the first time you use them. Without it
installed, they raise an error that names the extra to install:

```{code-cell} ipython3
import sys

import nbdemo.data as nd
from nbdemo.data import MissingExtraError

sys.modules["wfdb"] = None  # stands in for a project that did not install the extra

try:
    nd.med.ecg_mitbih_119.native
except MissingExtraError as error:
    print(error)
```

## Where downloads go

Most files ship in the package. A larger file downloads the first time you use its dataset, and is checked
against the sha256 in the dataset's manifest. Downloads go in `NBDEMO_CACHE`, or in
`$XDG_CACHE_HOME/nbdemo` (`~/.cache/nbdemo` by default). `nbdemo.data.cache_dir()`
returns the folder in use.

When a dataset is hosted in a private GitHub repository, set `NBDEMO_TOKEN` or `GITHUB_TOKEN` to a
token that can read it. The token is sent only to GitHub.
