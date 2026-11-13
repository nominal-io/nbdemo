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

Simulate a one-minute flight over Washington, DC, by a plane that carries a software-defined
radio (SDR). The plane is one Nominal asset with two datasets: `telemetry`, the flight data, and
`sdr`, the radio's IQ samples. The telemetry is simulated. The SDR data is a
[SigMF](https://sigmf.org) recording, IQEngine's `synthetic` example by Marc
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)), repeated to last as long as the
flight.

**Requirements:** a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the Nominal Python Client, and the packages the notebook imports, including sigmf.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the asset. It archives what earlier executions created on
it, so the asset holds one flight: this execution's.

+++

## Setup

```{code-cell} ipython3
import numpy as np
import pandas as pd
from nominal.core import NominalClient, set_display_options
from sigmf import sigmffile

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

## Simulate the flight

The flight is 60 seconds, and the flight ends when the notebook runs. The plane starts at the
Lincoln Memorial and flies east along the National Mall at 50 m/s, climbing to 300 m. After 18
seconds it banks right by 25° and turns about 180° to fly back west. A light wind from the west
pushes it east, so its ground track differs from its heading.

The simulation steps the plane's motion at 10 Hz and records one row of telemetry per step. The
code is folded. Select **Show code cell source** to read it.

```{code-cell} ipython3
:tags: [hide-input]

DURATION = 60  # seconds
RATE_HZ = 10  # telemetry samples per second
DT = 1 / RATE_HZ
G = 9.81  # m/s^2
LINCOLN_MEMORIAL = (38.8893, -77.0502)  # latitude, longitude
WIND = (4.0, 1.0)  # m/s, toward the east and the north
M_PER_DEG = 111_320.0  # meters per degree of latitude

rng = np.random.default_rng(42)
steps = int(DURATION * RATE_HZ)
rows = []
east = north = 0.0  # meters from the start
altitude, heading, roll, fuel = 200.0, np.radians(90), 0.0, 80.0  # heading: east
turned = 0.0
for step in range(steps):
    t = step * DT
    airspeed = 50 + 0.6 * np.sin(0.4 * t) + rng.normal(0, 0.15)
    # Bank right to turn about 180 degrees, starting at 18 s, then roll out.
    roll_target = np.radians(25) if t >= 18 and turned < np.radians(165) else 0.0
    roll += np.clip(roll_target - roll, -np.radians(10) * DT, np.radians(10) * DT)
    turn_rate = G * np.tan(roll) / airspeed
    heading += turn_rate * DT
    turned += turn_rate * DT
    # Climb to 300 m.
    vertical_speed = np.clip(0.4 * (300 - altitude), -4, 4) + rng.normal(0, 0.1)
    altitude += vertical_speed * DT
    # Air velocity plus wind gives the ground velocity.
    v_east = airspeed * np.sin(heading) + WIND[0]
    v_north = airspeed * np.cos(heading) + WIND[1]
    east += v_east * DT
    north += v_north * DT
    throttle = 62 + 3 * vertical_speed + rng.normal(0, 0.5)
    fuel -= 0.007 * throttle / 65 * DT  # kg
    rows.append(
        {
            "latitude": LINCOLN_MEMORIAL[0] + north / M_PER_DEG,
            "longitude": LINCOLN_MEMORIAL[1]
            + east / (M_PER_DEG * np.cos(np.radians(LINCOLN_MEMORIAL[0]))),
            "altitude": altitude,
            "heading": np.degrees(heading) % 360,
            "track": np.degrees(np.arctan2(v_east, v_north)) % 360,
            "groundspeed": np.hypot(v_east, v_north),
            "airspeed": airspeed,
            "vertical_speed": vertical_speed,
            "pitch": np.degrees(np.arctan2(vertical_speed, airspeed))
            + 2
            + rng.normal(0, 0.2),
            "roll": np.degrees(roll) + rng.normal(0, 0.3),
            "throttle": throttle,
            "engine_rpm": 1800 + 8 * throttle + rng.normal(0, 15),
            "fuel": fuel,
            "outside_air_temp": 22 - 0.0065 * altitude + rng.normal(0, 0.05),
            "bus_voltage": 13.8 + rng.normal(0, 0.03),
        }
    )

flight_start = pd.Timestamp.now(tz="UTC").floor("s") - pd.Timedelta(seconds=DURATION)
telemetry = pd.DataFrame(
    rows, index=flight_start + pd.to_timedelta(np.arange(steps) * DT, unit="s")
)
telemetry.index.name = "time"
telemetry.round(2).iloc[::100]
```

## Build the SDR data

The recording is 1,000,000 complex samples at 480 kS/s. `RATE_FACTOR` scales the sample rate the
data is stamped with. At 1.0 the SDR runs at the recorded 480 kS/s, and the flight takes 28.8
million samples. At 0.1, the default, it runs at 48 kS/s and takes 2.9 million. The recording
repeats from the start as many times as it takes to cover the flight.

```{code-cell} ipython3
RATE_FACTOR = 0.1  # 1.0: the recorded sample rate; 0.1: one tenth of it

# The checksum in this file's metadata doesn't match its data, so skip the check.
recording = sigmffile.fromfile("sigmf_data/synthetic.sigmf-meta", skip_checksum=True)
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

One asset, the plane, with a dataset for each source. A run marks the flight, so both datasets can
be opened for the same time range.

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

Each channel goes through a write stream: one call per channel with every timestamp and value.
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
