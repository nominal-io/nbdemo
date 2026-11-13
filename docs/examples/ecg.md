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

# ECG from a heart monitor

{.lead}
Count beats and plot an ECG from `med/ecg_mitbih_119`, using `df` and `native`.

The dataset is the first minute of record 119 from the
[MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/): two leads at 360 Hz, with beat
and rhythm annotations. It needs the `med` extra.

```{code-cell} ipython3
import plotly.express as px

from nominal_samples.med import ecg_mitbih_119

df = ecg_mitbih_119.df
df.head()
```

## Count beats

`N` is a normal beat and `V` a premature ventricular contraction (PVC).

```{code-cell} ipython3
df["beat"].value_counts()
```

The heart rate is the number of beats over the length of the record:

```{code-cell} ipython3
beats = df["beat"].dropna()
print(f"{len(beats) / df.index[-1] * 60:.0f} beats per minute")
```

## Plot

The first ten seconds of both leads, with each PVC marked:

```{code-cell} ipython3
first = df.loc[:10]
fig = px.line(first, y=["MLII", "V1"], labels={"time": "time (s)", "value": "mV"})
pvc = first[first["beat"] == "V"]
fig.add_scatter(x=pvc.index, y=pvc["MLII"], mode="markers", name="PVC", marker={"size": 9})
fig
```

## Annotations from the native record

`df` holds the beat symbols. `native` is the `wfdb.Record`, for what a frame leaves out, such as units and
the sampling frequency:

```{code-cell} ipython3
record = ecg_mitbih_119.native
dict(zip(record.sig_name, record.units)), record.fs
```
