---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Using the loaded data

{.lead}
`native` is the object that a dataset's format library returns, and `df` is a pandas DataFrame. A dataset
has each only where it makes sense.

Each form is read the first time you use it, and kept, so using it again returns the same object.

## Native objects

```{code-cell} ipython3
from nbdemo.data.med import ecg_mitbih_119

record = ecg_mitbih_119.native  # wfdb.Record
record.sig_name, record.fs
```

For a SigMF recording, `native` is a `sigmf.SigMFFile`. It reads the samples from the file beside its
metadata:

```{code-cell} ipython3
from nbdemo.data.rf import sigmf_synthetic

recording = sigmf_synthetic.native
iq = recording.read_samples()
iq.dtype, len(iq)
```

## DataFrames

```{code-cell} ipython3
ecg_mitbih_119.df.head()
```

The ECG frame has a column for each lead, in physical units, indexed by seconds. The `beat` column holds
the annotation symbol at the sample of each beat. Flight telemetry is indexed by timestamp:

```{code-cell} ipython3
from nbdemo.data.aero import flight_dc

flight_dc.df.iloc[:3, :5]
```

## When a form is not available

A dataset with no such form raises `FormUnavailable`, which says why and lists the forms it has. The error
is an `AttributeError`, so `hasattr` also tells you:

```{code-cell} ipython3
print(hasattr(sigmf_synthetic, "df"))
print(sigmf_synthetic.forms)

try:
    sigmf_synthetic.df
except AttributeError as error:
    print(error)
```
