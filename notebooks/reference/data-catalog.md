---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Catalog

{.lead}
Every dataset in the package, generated from the dataset manifests.

`nbdemo.data.catalog` returns the datasets. It reads manifests only, so nothing is downloaded.

```{code-cell} ipython3
import pandas as pd

import nbdemo.data as nd

pd.DataFrame(
    {
        "id": d.id,
        "description": d.description,
        "size (MB)": round(d.size / 1e6, 2),
        "forms": ", ".join(d.forms),
        "license": d.license,
    }
    for d in nd.catalog()
).style.hide(axis="index")
```

Look one up by its id when the name is only known at run time:

```{code-cell} ipython3
nd.get("aero/flight_dc")
```

The attribution for datasets whose license asks for one:

```{code-cell} ipython3
for dataset in nd.catalog():
    if dataset.attribution:
        print(f"{dataset.id}: {dataset.attribution}\n")
```
