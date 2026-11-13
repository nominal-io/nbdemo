---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Sample data

{.lead}
`nbdemo.data` holds sample datasets for Nominal's open-source projects, grouped by domain: `aero`, `med` and `rf`.

Each dataset is a {py:class}`~nbdemo.data.Dataset` with up to three ways to be accessed:

* as a file path, with {py:attr}`~nbdemo.data.Dataset.path`
* as its format's own Python object, with {py:attr}`~nbdemo.data.Dataset.native`
* as a pandas {py:class}`~pandas.DataFrame`, with {py:attr}`~nbdemo.data.Dataset.df`

## Usage 
Import a dataset from its domain: {py:mod}`~nbdemo.data.aero`, {py:mod}`~nbdemo.data.med` or
{py:mod}`~nbdemo.data.rf`. Importing reads only a small manifest; nothing is downloaded or parsed
until you use the dataset.

+++

### As Path

```{code-cell} ipython3
from nbdemo.data.med import ecg_mitbih_119

ecg_mitbih_119.path  # a Path, to pass to your own loader
```

The same dataset as the Python object that its format's library returns, and as a DataFrame. A dataset
has each only where it makes sense; see {py:attr}`~nbdemo.data.Dataset.forms`.

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
{py:func}`~nbdemo.data.catalog` lists the datasets, and {py:func}`~nbdemo.data.get` looks one up by id:

```{code-cell} ipython3
import nbdemo.data as nd

nd.catalog("rf")
```

[Install](data-install.md) the package with the extras for the formats you read.
[Using the paths](data-paths.md) covers testing a file loader, and
[Using the loaded data](data-loaded.md) covers `native` and `df`, including
{py:class}`~nbdemo.data.FormUnavailable`, which a dataset raises for a form it does not have.
The [catalog](data-catalog.md) lists every dataset, and [Adding a dataset](data-adding.md)
explains how to contribute one. The [API](data-api.md) is the full reference.

```{toctree}
:hidden:

Install <data-install>
Using the paths <data-paths>
Using the loaded data <data-loaded>
Catalog <data-catalog>
Adding a dataset <data-adding>
nbdemo.data API <data-api>
```
