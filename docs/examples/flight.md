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

# Flight telemetry

{.lead}
Plot the ground track and altitude of `aero/flight_dc`, a simulated one-minute flight over Washington, DC.

The plane starts at the Lincoln Memorial and flies east along the National Mall, climbing to 300 m. After
18 seconds it turns about 180° to fly back west. `gen/aero_flight_dc.py` simulates it at 10 Hz. It needs the
`aero` extra.

```{code-cell} ipython3
import plotly.express as px

from nominal_samples.aero import flight_dc

df = flight_dc.df
df.iloc[::100, :6]
```

## Ground track

```{code-cell} ipython3
fig = px.line_map(df, lat="latitude", lon="longitude", zoom=12, height=420)
fig.update_layout(map_style="open-street-map", margin={"l": 0, "r": 0, "t": 0, "b": 0})
fig
```

## Altitude and speed

```{code-cell} ipython3
px.line(df, y=["altitude", "groundspeed"], labels={"value": "m, m/s"})
```

## How it was made

The telemetry is seeded and starts at a fixed time, so the script reproduces the checked-in file:

```{code-cell} ipython3
flight_dc.manifest["generated"]
```
