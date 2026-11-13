---
icon: paper-airplane
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Plane with an SDR

{.lead}
Telemetry and radio data from one flight

Upload a one-minute flight over Washington, DC, by a plane that carries a software-defined
radio (SDR). The plane is one Nominal {py:class}`asset <nominal.core.Asset>` with two
{py:class}`datasets <nominal.core.Dataset>`: `telemetry`, the flight data, and `sdr`, the radio's IQ samples. Both come from [`nbdemo.data`](reference/data.md): `aero.flight_dc`
is simulated telemetry, and `rf.sigmf_synthetic` is a [SigMF](https://sigmf.org) recording,
IQEngine's `synthetic` example by Marc
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)), repeated to last as long as the
flight.

**Requirements:** a `default` [profile](inv:nominal:std:doc#guides/api-keys-setup)
for the Nominal Python Client, and the packages the notebook imports, including `nbdemo[all]`.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the asset. It archives what earlier executions created on
it, so the asset holds one flight: this execution's.

+++

## Setup

A {py:class}`~nominal.core.NominalClient` connects to Nominal with the profile.

```{code-cell} ipython3
import numpy as np
import pandas as pd
from nominal.core import NominalClient, set_display_options
from nbdemo.data.aero import flight_dc
from nbdemo.data.rf import sigmf_synthetic

# A Nominal object at the end of a cell displays as a card.
set_display_options(time_format="readable")

client = NominalClient.from_profile("default")
```

```{code-cell} ipython3
:tags: [remove-cell]

# Start each execution with only its own data on the plane. The client cannot delete, so what
# earlier executions created is archived: runs and datasets. The `example` property matches
# only the plane this notebook created. The page does not show this cell.
for old_asset in client.search_assets(properties={"example": "flight_sdr"}):
    for old_run in old_asset.list_runs():
        if not old_run.is_archived:
            old_run.archive()
    old_datasets = old_asset.list_datasets()
    old_asset.remove_data_scopes(names=[name for name, _ in old_datasets])
    for _, old_dataset in old_datasets:
        old_dataset.archive()
```

## Load the flight

`flight_dc.df` has 60 seconds of telemetry at 10 Hz. Its timestamps are fixed, so shift them to end
now.

```{code-cell} ipython3
DURATION = 60  # seconds
RATE_HZ = 10  # telemetry samples per second

flight_start = pd.Timestamp.now(tz="UTC").floor("s") - pd.Timedelta(seconds=DURATION)
telemetry = flight_dc.df.copy()
# pandas reads the timestamps at microsecond resolution; Nominal takes nanoseconds.
telemetry.index = (flight_start + (telemetry.index - telemetry.index[0])).as_unit(
    "ns"
)
telemetry.round(2).iloc[::100]
```

## Build the SDR data

The recording is 1,000,000 complex samples at 480 kS/s. `RATE_FACTOR` scales the sample rate the
data is stamped with. At 1.0 the SDR runs at the recorded 480 kS/s, and the flight takes 28.8
million samples. At 0.1, the default, it runs at 48 kS/s and takes 2.9 million. The recording
repeats from the start as many times as it takes to cover the flight.

```{code-cell} ipython3
RATE_FACTOR = 0.1  # 1.0: the recorded sample rate; 0.1: one tenth of it

recording = sigmf_synthetic.native  # a sigmf.SigMFFile, downloaded on first use
recorded_rate = float(recording.get_global_field("core:sample_rate"))
iq = recording.read_samples()  # complex samples

sdr_rate = recorded_rate * RATE_FACTOR  # samples per second
count = int(DURATION * sdr_rate)
samples = iq[np.arange(count) % len(iq)]  # repeat the recording to fill the flight
sdr_times = flight_start.value + np.round(np.arange(count) * 1e9 / sdr_rate).astype(
    "int64"
)
print(
    f"{count:,} samples at {sdr_rate:,.0f} S/s: "
    f"{count / len(iq):.1f} repeats of the {len(iq):,}-sample recording"
)
```

## Create the plane

One {py:class}`asset <nominal.core.Asset>`, the plane, with a {py:class}`dataset <nominal.core.Dataset>`
for each source. A {py:class}`run <nominal.core.Run>` marks the flight, so both datasets can be opened for
the same time range.

```{code-cell} ipython3
plane = client.get_or_create_asset_by_properties(
    {"example": "flight_sdr"},
    name="Plane",
    description="A plane carrying a software-defined radio",
)
telemetry_dataset = plane.get_or_create_dataset(
    "telemetry",
    name="telemetry",
    description="Simulated flight data at 10 Hz",
)
sdr_dataset = plane.get_or_create_dataset(
    "sdr",
    name="sdr",
    description="IQ samples from the SDR: a SigMF recording, repeated",
)
run = plane.create_run(
    f"Flight over Washington, DC {flight_start:%Y-%m-%d %H:%M}",
    start=flight_start,
    end=flight_start + pd.Timedelta(seconds=DURATION),
    description="A one-minute flight along the National Mall",
)
plane
```

## Upload

Each channel goes through a {py:meth}`write stream <nominal.core.Dataset.get_write_stream>`: one call per channel with every timestamp and value.
Closing the stream waits for the data to be sent.

```{code-cell} ipython3
telemetry_times = telemetry.index.astype("int64").to_numpy()
with telemetry_dataset.get_write_stream() as stream:
    for channel in telemetry.columns:
        stream.enqueue_batch(channel, telemetry_times, telemetry[channel].to_numpy())

with sdr_dataset.get_write_stream() as stream:
    stream.enqueue_batch("i", sdr_times, samples.real)
    stream.enqueue_batch("q", sdr_times, samples.imag)


UNITS = {
    "latitude": ("°", "Latitude, WGS 84"),
    "longitude": ("°", "Longitude, WGS 84"),
    "altitude": ("m", "Altitude above mean sea level"),
    "heading": ("°", "Direction the nose points, clockwise from north"),
    "track": ("°", "Direction of travel over the ground, clockwise from north"),
    "groundspeed": ("m/s", "Speed over the ground"),
    "airspeed": ("m/s", "Speed through the air"),
    "vertical_speed": ("m/s", "Rate of climb"),
    "pitch": ("°", "Nose up is positive"),
    "roll": ("°", "Right wing down is positive"),
    "throttle": ("%", "Throttle position"),
    "engine_rpm": ("rpm", "Engine speed"),
    "fuel": ("kg", "Fuel remaining"),
    "outside_air_temp": ("°C", "Outside air temperature"),
    "bus_voltage": ("V", "Electrical bus voltage"),
}
for channel in telemetry_dataset.get_channels():
    unit, description = UNITS[channel.name]
    channel.update(unit=unit, description=description)

run
```

```{code-cell} ipython3

```
