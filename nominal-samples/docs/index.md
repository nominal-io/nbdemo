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
Sample datasets for Nominal's open-source projects.

Each dataset is a {py:class}`~nominal_samples.Dataset` with up to three ways to be accessed:

* as a file path, with {py:attr}`~nominal_samples.Dataset.path`
* as its format's own Python object, with {py:attr}`~nominal_samples.Dataset.native`
* as a pandas {py:class}`~pandas.DataFrame`, with {py:attr}`~nominal_samples.Dataset.df`

## Usage 
Import a dataset from its domain: {py:mod}`~nominal_samples.aero`, {py:mod}`~nominal_samples.med` or
{py:mod}`~nominal_samples.rf`. Importing reads only a small manifest; nothing is downloaded or parsed
until you use the dataset.

+++

### As Path 

```{code-cell} ipython3
from nominal_samples.med import ecg_mitbih_119

ecg_mitbih_119.path  # a Path, to pass to your own loader
```

The same dataset as the Python object that its format's library returns, and as a DataFrame. A dataset
has each only where it makes sense; see {py:attr}`~nominal_samples.Dataset.forms`.

+++

### As Native 

```{code-cell} ipython3
ecg_mitbih_119.native  # a wfdb.Record
```

### As Dataframe

```{code-cell} ipython3
ecg_mitbih_119.df.head()
```

To work with the domains as a group, import the package under a short name.
{py:func}`~nominal_samples.catalog` lists the datasets, and {py:func}`~nominal_samples.get` looks one up by id:

```{code-cell} ipython3
import nominal_samples as ns

ns.catalog("rf")
```

[Install](guides/install.md) the package with the extras for the formats you read.
[Using the paths](guides/paths.md) covers testing a file loader, and
[Using the loaded data](guides/loaded.md) covers `native` and `df`, including
{py:class}`~nominal_samples.FormUnavailable`, which a dataset raises for a form it does not have.
The [catalog](guides/catalog.md) lists every dataset, and [Adding a dataset](guides/adding-datasets.md)
explains how to contribute one.

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
:caption: Reference
:hidden:

nominal_samples <reference/index>
reference/dataset
reference/errors
```
