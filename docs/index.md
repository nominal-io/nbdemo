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

# nominal-samples

{.lead}
Sample datasets for Nominal's open-source projects, grouped by domain: `aero`, `med` and `rf`.
Each dataset is a file path, and where it makes sense its format's own Python object and a pandas DataFrame.

Import a dataset from its domain. Importing reads only a small manifest; nothing is downloaded or parsed
until you use the dataset.

```{code-cell} ipython3
from nominal_samples.med import ecg_mitbih_119

ecg_mitbih_119.path  # a Path, to pass to your own loader
```

The same dataset as the Python object that its format's library returns, and as a DataFrame:

```{code-cell} ipython3
ecg_mitbih_119.native  # a wfdb.Record
```

```{code-cell} ipython3
ecg_mitbih_119.df.head()
```

To work with the domains as a group, import the package under a short name:

```{code-cell} ipython3
import nominal_samples as ns

ns.catalog("rf")
```

[Install](guides/install.md) the package with the extras for the formats you read. [Using the paths](guides/paths.md)
covers testing a file loader, and [Using the loaded data](guides/loaded.md) covers `native` and `df`.

```{toctree}
:caption: Guides
:hidden:

Intro <self>
guides/install
guides/paths
guides/loaded
guides/catalog
guides/adding-datasets
```

```{toctree}
:caption: Examples
:hidden:

Overview <examples/index>
examples/ecg
examples/sigmf
examples/flight
```

```{toctree}
:caption: Reference
:hidden:

nominal_samples <reference/index>
reference/dataset
reference/errors
```
