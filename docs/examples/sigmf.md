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

# SDR recording

{.lead}
Read IQ samples from `rf/sigmf_synthetic` and plot their spectrum.

The dataset is IQEngine's `synthetic` SigMF recording by Marc ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
It needs the `rf` extra. The 8 MB recording downloads the first time you use it.

A SigMF recording has no DataFrame form, because its samples are binary. Use `native`, a `sigmf.SigMFFile`:

```{code-cell} ipython3
import numpy as np
import plotly.express as px

from nominal_samples.rf import sigmf_synthetic

recording = sigmf_synthetic.native
rate = float(recording.get_global_field("core:sample_rate"))
centre = recording.get_captures()[0]["core:frequency"]
iq = recording.read_samples()
print(f"{len(iq):,} samples at {rate / 1e3:.0f} kS/s, centred on {centre / 1e9:.3f} GHz")
```

## Spectrum

Average the power spectrum over blocks of 4096 samples:

```{code-cell} ipython3
block = 4096
blocks = iq[: len(iq) // block * block].reshape(-1, block)
power = (np.abs(np.fft.fftshift(np.fft.fft(blocks * np.hanning(block), axis=1), axes=1)) ** 2).mean(axis=0)
freq = centre + np.fft.fftshift(np.fft.fftfreq(block, 1 / rate))

fig = px.line(x=freq / 1e6, y=10 * np.log10(power), labels={"x": "frequency (MHz)", "y": "power (dB)"})
fig
```

## The files

`path` is the `.sigmf-meta` file, and the `.sigmf-data` file is beside it. Pass either to a loader of your own:

```{code-cell} ipython3
sigmf_sizes = {name: path.stat().st_size for name, path in sigmf_synthetic.paths.items()}
sigmf_sizes
```
