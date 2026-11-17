---
icon: broadcast
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# W-band radios

{.lead}
Component data and a field test

Keep two W-band (75–110 GHz) point-to-point radios' component data and field-test telemetry in
Nominal, along with the telemetry of the drones that carry them, then analyze it all in the Nominal platform. Each radio is a Nominal {py:class}`asset <nominal.core.Asset>`,
with its parts' Touchstone files as {py:class}`attachments <nominal.core.Attachment>` and its field test as a
{py:class}`run <nominal.core.Run>`. All data is
simulated, with [scikit-rf](https://scikit-rf.org) standing in for vector network analyzer
measurements.

**Requirements:** a `default` [profile](inv:nominal:std:doc#guides/api-keys-setup)
for the Nominal Python Client, and the packages the notebook imports, including scikit-rf.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the two assets. It archives what earlier executions
created on them, so they hold one set of data: this execution's.

+++

## Setup

### Connect to Nominal

```{code-cell} ipython3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import skrf as rf
from nominal.core import EventType, NominalClient, set_display_options
from nbdemo.style import set_plotly_style
from nominal.thirdparty.pandas import upload_dataframe_to_dataset
from plotly.subplots import make_subplots

# A Nominal object at the end of a cell displays as a card. Show its timestamps in a readable
# format.
set_display_options(time_format="readable")
# Plotly figures use nbdemo's style, on plotly's dark template.
set_plotly_style()
pio.templates.default = "plotly_dark+nbdemo"

client = NominalClient.from_profile("default")
```

```{code-cell} ipython3
:tags: [remove-cell]

# Start each execution with only its own data on the two radios. The client cannot delete, so
# what earlier executions created is archived: runs, events, attachments and datasets. The
# `example` property matches only the radios this notebook created. The page does not show
# this cell.
for old_asset in client.search_assets(properties={"example": "rf_radio_field_test"}):
    for old_run in old_asset.list_runs():
        if not old_run.is_archived:
            old_run.archive()
    for old_event in old_asset.search_events():
        old_event.archive()
    old_attachments = old_asset.list_attachments()
    old_asset.remove_attachments(old_attachments)
    for old_attachment in old_attachments:
        old_attachment.archive()
    old_datasets = old_asset.list_datasets()
    old_asset.remove_data_scopes(names=[name for name, _ in old_datasets])
    for _, old_dataset in old_datasets:
        old_dataset.archive()
```

### Synthesize the component Touchstone files

Every part is characterized from 75 to 110 GHz. The radios use frequency-division duplexing: they
transmit in 81–86 GHz and receive in 91–96 GHz, so each has a bandpass filter for each direction.

| Part | File | Model |
| --- | --- | --- |
| Tx filter | `.s2p` | 5th-order Chebyshev bandpass, 81–86 GHz |
| Rx filter | `.s2p` | 5th-order Chebyshev bandpass, 91–96 GHz |
| Amplifier | `.s2p` | about 21 dB gain, rolling off toward the band edges |
| Antenna | `.s1p` | horn antenna, return loss only |
| Coupler | `.s4p` | 10 dB directional coupler: port 1 in, 2 through, 3 coupled, 4 isolated |

Each radio's parts vary slightly, from a fixed random seed. RadioTwo was built with a marginal
amplifier, about 2.5 dB below RadioOne's.

The code that synthesizes data is folded. Select **Show code cell source** to read it.

```{code-cell} ipython3
:tags: [hide-input]

FREQUENCY = rf.Frequency(75, 110, 701, unit="GHz")
F_GHZ = FREQUENCY.f_scaled
F_HZ = FREQUENCY.f


def delay(seconds: float) -> np.ndarray:
    """Phase of a pure time delay across the band."""
    return np.exp(-2j * np.pi * F_HZ * seconds)


def bandpass_filter(
    name: str, f_lo: float, f_hi: float, loss_db: float
) -> rf.Network:
    """A 5th-order Chebyshev bandpass with 0.5 dB ripple and `loss_db` of dissipation loss."""
    x = (F_GHZ - (f_lo + f_hi) / 2) / ((f_hi - f_lo) / 2)
    chebyshev = np.cosh(5 * np.arccosh(np.abs(x).astype(complex))).real
    lossless_s21 = 1 / np.sqrt(1 + 0.35**2 * chebyshev**2)
    s21 = lossless_s21 * 10 ** (-loss_db / 20) * delay(0.4e-9)
    s11 = np.maximum(np.sqrt(1 - lossless_s21**2), 0.03) * delay(0.2e-9)
    s = np.empty((F_GHZ.size, 2, 2), complex)
    s[:, 0, 0], s[:, 1, 1] = s11, s11 * np.exp(0.6j)
    s[:, 0, 1] = s[:, 1, 0] = s21
    return rf.Network(frequency=FREQUENCY, s=s, name=name)


def amplifier(name: str, gain_db: float, rng: np.random.Generator) -> rf.Network:
    """An amplifier with `gain_db` of gain at 92.5 GHz, about 4 dB less at the band edges."""
    ripple = 0.3 * np.sin(2 * np.pi * F_GHZ / 6.5 + rng.uniform(0, np.pi))
    gain = gain_db - 4 * ((F_GHZ - 92.5) / 17.5) ** 2 + ripple
    s = np.empty((F_GHZ.size, 2, 2), complex)
    s[:, 0, 0] = 10 ** ((-12 + 2 * np.sin(2 * np.pi * F_GHZ / 9)) / 20) * delay(
        0.05e-9
    )
    s[:, 1, 1] = 10 ** ((-10 + 2 * np.cos(2 * np.pi * F_GHZ / 11)) / 20) * delay(
        0.07e-9
    )
    s[:, 1, 0] = 10 ** (gain / 20) * delay(0.15e-9)
    s[:, 0, 1] = 10 ** (-45 / 20) * delay(0.15e-9)
    return rf.Network(frequency=FREQUENCY, s=s, name=name)


def horn_antenna(name: str, rng: np.random.Generator) -> rf.Network:
    """A horn antenna's input match: about 22 dB return loss, with ripple from the feed."""
    return_loss = 22 + 4 * np.sin(2 * np.pi * F_GHZ / 3.1 + rng.uniform(0, np.pi))
    s = (10 ** (-return_loss / 20) * delay(0.3e-9)).reshape(-1, 1, 1)
    return rf.Network(frequency=FREQUENCY, s=s, name=name)


def directional_coupler(name: str, coupling_db: float) -> rf.Network:
    """A reciprocal 10 dB coupler. Ports: 1 input, 2 through, 3 coupled, 4 isolated."""
    coupled = 10 ** (-(coupling_db + 0.6 * ((F_GHZ - 92.5) / 17.5) ** 2) / 20)
    through = np.sqrt(1 - coupled**2) * 10 ** (-0.4 / 20)
    isolated = 10 ** ((-30 + 3 * np.sin(2 * np.pi * F_GHZ / 7)) / 20)
    match = 10 ** (-25 / 20) * delay(0.1e-9)
    s = np.empty((F_GHZ.size, 4, 4), complex)
    for i in range(4):
        s[:, i, i] = match
    for a, b, value in [
        (0, 1, through * delay(0.25e-9)),
        (2, 3, through * delay(0.25e-9)),
        (0, 2, coupled * delay(0.25e-9) * -1j),
        (1, 3, coupled * delay(0.25e-9) * -1j),
        (0, 3, isolated * delay(0.3e-9)),
        (1, 2, isolated * delay(0.3e-9)),
    ]:
        s[:, a, b] = s[:, b, a] = value
    return rf.Network(frequency=FREQUENCY, s=s, name=name)


def radio_components(
    radio: str, seed: int, amplifier_gain_db: float
) -> dict[str, rf.Network]:
    rng = np.random.default_rng(seed)
    shift = rng.normal(0, 0.15, 2)
    return {
        "tx_filter": bandpass_filter(
            f"{radio}_tx_filter",
            81 + shift[0],
            86 + shift[0],
            loss_db=1.2 + rng.normal(0, 0.15),
        ),
        "rx_filter": bandpass_filter(
            f"{radio}_rx_filter",
            91 + shift[1],
            96 + shift[1],
            loss_db=1.4 + rng.normal(0, 0.15),
        ),
        "amplifier": amplifier(f"{radio}_amplifier", amplifier_gain_db, rng),
        "antenna": horn_antenna(f"{radio}_antenna", rng),
        "coupler": directional_coupler(f"{radio}_coupler", 10 + rng.normal(0, 0.2)),
    }


RADIOS = {
    "RadioOne": radio_components("RadioOne", seed=1, amplifier_gain_db=21.0),
    "RadioTwo": radio_components("RadioTwo", seed=2, amplifier_gain_db=18.5),
}
```

scikit-rf writes each network to a Touchstone file whose extension matches its port count:

```{code-cell} ipython3
:tags: [hide-input]

DATA_DIR = Path("rf_radio_data")

touchstone_files: dict[str, dict[str, Path]] = {}
for radio, parts in RADIOS.items():
    (DATA_DIR / radio).mkdir(parents=True, exist_ok=True)
    touchstone_files[radio] = {}
    for part, network in parts.items():
        network.write_touchstone(network.name, dir=DATA_DIR / radio)
        touchstone_files[radio][part] = (
            DATA_DIR / radio / f"{network.name}.s{network.nports}p"
        )

pd.DataFrame(touchstone_files).map(str)
```

```{code-cell} ipython3
# Overlay the two radios' parts: RadioOne solid, RadioTwo dashed.
panels = ["Filters", "Amplifier", "Antenna", "Coupler"]
fig = make_subplots(
    rows=2, cols=2, subplot_titles=panels, shared_xaxes=True, vertical_spacing=0.12
)


def add_s_db(
    network: rf.Network, m: int, n: int, name: str, row: int, col: int, dash: str
) -> None:
    fig.add_scatter(
        x=network.f / 1e9,
        y=network.s_db[:, m, n],
        name=name,
        line={"dash": dash, "width": 1.5},
        row=row,
        col=col,
    )


for radio, parts in RADIOS.items():
    dash = "solid" if radio == "RadioOne" else "dash"
    for part in ["tx_filter", "rx_filter"]:
        add_s_db(parts[part], 1, 0, f"{radio} {part} S21", 1, 1, dash)
    add_s_db(parts["amplifier"], 1, 0, f"{radio} amplifier S21", 1, 2, dash)
    add_s_db(parts["amplifier"], 0, 0, f"{radio} amplifier S11", 1, 2, dash)
    add_s_db(parts["antenna"], 0, 0, f"{radio} antenna S11", 2, 1, dash)
    for m, port in [(1, "through"), (2, "coupled"), (3, "isolated")]:
        add_s_db(parts["coupler"], m, 0, f"{radio} coupler {port}", 2, 2, dash)
fig.update_yaxes(range=[-60, 5], row=1, col=1)
fig.update_yaxes(title_text="dB", col=1)
fig.update_xaxes(title_text="frequency (GHz)", row=2)
fig.update_layout(
    height=640, hovermode="closest", legend={"y": -0.2, "yanchor": "top"}
)
fig
```

### Register the radios as assets

A few key figures become asset properties, so they show on each asset's page in Nominal and can be
searched. Filter loss is read at the center of each filter's band, and the rest at the center of
the receive band, 93.5 GHz.

```{code-cell} ipython3
def db_at(network: rf.Network, m: int, n: int, ghz: float) -> float:
    return round(float(network.s_db[np.argmin(np.abs(F_GHZ - ghz)), m, n]), 2)


def key_figures(parts: dict[str, rf.Network]) -> dict[str, float]:
    return {
        "tx_filter_insertion_loss_db": -db_at(parts["tx_filter"], 1, 0, 83.5),
        "rx_filter_insertion_loss_db": -db_at(parts["rx_filter"], 1, 0, 93.5),
        "amplifier_gain_db": db_at(parts["amplifier"], 1, 0, 93.5),
        "antenna_return_loss_db": -db_at(parts["antenna"], 0, 0, 93.5),
        "coupler_coupling_db": -db_at(parts["coupler"], 2, 0, 93.5),
    }


pd.DataFrame({radio: key_figures(parts) for radio, parts in RADIOS.items()})
```

{py:meth}`~nominal.core.NominalClient.get_or_create_asset_by_properties` finds each radio by its
properties, or registers it the first time. The `example` property keeps these assets apart from
real radios with the same `radio_id`.

Each Touchstone file is uploaded with `create_attachment` and added to its radio with
`add_attachments`.

```{code-cell} ipython3
EXAMPLE = "rf_radio_field_test"
PART_DESCRIPTIONS = {
    "tx_filter": "Tx channel filter, 81–86 GHz",
    "rx_filter": "Rx channel filter, 91–96 GHz",
    "amplifier": "W-band amplifier",
    "antenna": "Horn antenna",
    "coupler": "10 dB directional coupler (1 in, 2 through, 3 coupled, 4 isolated)",
}

assets = {}
for radio, parts in RADIOS.items():
    asset = client.get_or_create_asset_by_properties(
        {"radio_id": radio, "example": EXAMPLE},
        name=radio,
        description="W-band (75–110 GHz) point-to-point radio",
        labels=["w-band", "radio"],
    )
    asset.update(properties={**asset.properties, **key_figures(parts)})

    attachments = [
        client.create_attachment(
            path,
            description=f"{radio} {PART_DESCRIPTIONS[part]}, 75–110 GHz",
            properties={
                "part": part,
                "ports": str(parts[part].nports),
                "radio_id": radio,
            },
            labels=["touchstone", path.suffix.lstrip(".")],
        )
        for part, path in touchstone_files[radio].items()
    ]
    asset.add_attachments(attachments)
    assets[radio] = asset
```

## Field test

### Simulate the field test

Both radios carry traffic over the same link for 10 minutes, recorded at 10 Hz. Each records:

| Dataset | Channel | Unit | What it measures |
| --- | --- | --- | --- |
| `power` | `bias_voltage` | V | amplifier drain bias, regulated at 4.0 V |
| `power` | `dc_supply_voltage` | V | 12 V supply bus, which sags under load |
| `power` | `thermistor_voltage` | V | heat: an NTC thermistor divider, which rises as the radio warms |
| `comms` | `rx_packets_mpps` | million packets/s | packets received intact |
| `comms` | `dropped_packets_pps` | packets/s | packets lost to bit errors or a full queue |
| `comms` | `throughput_gbps` | Gb/s | delivered throughput |
| `flight` | `latitude`, `longitude` | ° | the drone's position |
| `flight` | `altitude` | m | height above mean sea level |
| `flight` | `groundspeed` | m/s | speed over the ground |
| `flight` | `battery_voltage` | V | 6S flight battery, which sags as it drains |
| `flight` | `battery_remaining` | % | battery charge left |

Traffic is 1500-byte packets, so 1 Mpps is 12 Gb/s. The modem runs at 20 Gb/s, about 1.67 Mpps,
while it has at least 2 dB of link margin. Below that, it steps down to a more robust modulation at
14 Gb/s, and back up above 3 dB.

The amplifier loses about 0.05 dB of gain per °C, which eats into the link margin. Five minutes
in, RadioTwo's cooling fan fails. Its marginal amplifier then runs out of margin.

Each radio hangs under a drone. The drones take off 1.2 km apart, climb to about 160 m in 30 s,
then fly over their sites for the rest of the test: RadioOne's a figure eight 500 m wide and
RadioTwo's circles 350 m across, with wind pushing them east. The radios' power draw adds to the
batteries' load.

```{code-cell} ipython3
:tags: [hide-input]

SAMPLE_RATE_HZ = 10
DURATION_S = 600
PACKET_BITS = 1500 * 8
t = np.arange(DURATION_S * SAMPLE_RATE_HZ) / SAMPLE_RATE_HZ
test_start = pd.Timestamp.now(tz="UTC").floor("s") - pd.Timedelta(
    seconds=DURATION_S + 60
)
times = test_start + pd.to_timedelta(t, unit="s")


def thermistor_voltage(temp_c: np.ndarray) -> np.ndarray:
    """10 kΩ NTC thermistor (B = 3950) on the high side of a 10 kΩ divider, from 3.3 V."""
    r_ntc = 10e3 * np.exp(3950 * (1 / (temp_c + 273.15) - 1 / 298.15))
    return 3.3 * 10e3 / (10e3 + r_ntc)


def field_test(
    amplifier_gain_db: float, fan_fails_at_s: float | None, seed: int
) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    noise = lambda scale: rng.normal(0, scale, t.size)  # noqa: E731

    # Offered traffic ramps up over the first minute and then fluctuates around 17 Gb/s.
    load = np.clip(t / 60, 0, 1)
    offered_gbps = (
        load * (17 + 1.5 * np.sin(2 * np.pi * t / 90)) + np.abs(noise(0.4)) * load
    )

    # The radio warms toward 45 °C. Without its fan, it climbs another 25 °C.
    temp_c = 25 + 20 * (1 - np.exp(-t / 180))
    if fan_fails_at_s is not None:
        after = np.clip(t - fan_fails_at_s, 0, None)
        temp_c += 25 * (1 - np.exp(-after / 120))
    temp_c += noise(0.2)

    # Link margin: 6 dB with a 21 dB amplifier at 25 °C, less with less gain and more heat.
    margin_db = 6 + (amplifier_gain_db - 21) - 0.05 * (temp_c - 25) + noise(0.3)
    capacity_gbps = np.empty_like(t)
    stepped_down = False
    for i, margin in enumerate(
        pd.Series(margin_db).rolling(20, min_periods=1).mean()
    ):
        stepped_down = margin < 3 if stepped_down else margin < 2
        capacity_gbps[i] = 14 if stepped_down else 20

    # Bit errors drop a fraction of packets that grows as margin shrinks.
    # Traffic beyond the modem's capacity overflows the queue and is dropped too.
    offered_pps = offered_gbps * 1e9 / PACKET_BITS
    carried_pps = np.minimum(offered_gbps, capacity_gbps) * 1e9 / PACKET_BITS
    error_rate = np.clip(1e-5 * 10 ** (0.6 * (6 - margin_db)), 0, 0.05)
    received_pps = carried_pps * (1 - error_rate)
    dropped_pps = offered_pps - received_pps

    return {
        "power": pd.DataFrame(
            {
                "bias_voltage": 4.0 - 0.002 * (temp_c - 25) + noise(0.004),
                "dc_supply_voltage": 12.05 - 0.012 * offered_gbps + noise(0.01),
                "thermistor_voltage": thermistor_voltage(temp_c) + noise(0.003),
            },
            index=pd.Index(times, name="time"),
        ).round(4),
        "comms": pd.DataFrame(
            {
                "rx_packets_mpps": received_pps / 1e6,
                "dropped_packets_pps": np.round(np.maximum(dropped_pps, 0)),
                "throughput_gbps": received_pps * PACKET_BITS / 1e9,
            },
            index=pd.Index(times, name="time"),
        ).round(4),
    }


def drone_flight(
    lat0: float, lon0: float, width_m: float, laps: float, circle: bool, seed: int
) -> pd.DataFrame:
    """A drone that climbs for 30 s while flying a figure eight or a circle."""
    rng = np.random.default_rng(seed)
    climb = np.clip(t / 30, 0, 1)
    # Altitude rises to 160 m, then swells and falls by 25 m every 200 s.
    altitude = (
        40
        + 120 * climb
        + 25 * np.sin(2 * np.pi * t / 200) * climb
        + np.cumsum(rng.normal(0, 0.02, t.size)) * climb
    )

    # Position as meters east and north of the takeoff point. The path is `width_m` wide
    # and flies `laps` times in the test: a circle, or a figure eight half as tall. Wind
    # drifts the drone east and adds a random walk.
    phase = 2 * np.pi * laps * t / DURATION_S
    if circle:
        path_east = width_m / 2 * np.sin(phase)
        path_north = width_m / 2 * (1 - np.cos(phase))
    else:
        path_east = width_m / 2 * np.sin(phase)
        path_north = width_m / 4 * np.sin(2 * phase)
    east = path_east * climb + np.cumsum(rng.normal(0.02, 0.08, t.size)) * climb
    north = path_north * climb + np.cumsum(rng.normal(0, 0.08, t.size)) * climb
    groundspeed = np.hypot(np.gradient(east, t), np.gradient(north, t))

    # A 6S pack at 25.2 V full sags with load and as it drains. The 10-minute test uses 12%.
    remaining = 100 - 12 * t / DURATION_S
    voltage = (
        21.5 + 3.7 * remaining / 100 - 0.4 * climb + rng.normal(0, 0.02, t.size)
    )

    return pd.DataFrame(
        {
            "latitude": lat0 + north / 111_320,
            "longitude": lon0 + east / (111_320 * np.cos(np.radians(lat0))),
            "altitude": altitude,
            "groundspeed": groundspeed + np.abs(rng.normal(0, 0.05, t.size)),
            "battery_voltage": voltage,
            "battery_remaining": remaining,
        },
        index=pd.Index(times, name="time"),
    ).round(6)


tests = {
    "RadioOne": field_test(amplifier_gain_db=21.0, fan_fails_at_s=None, seed=11),
    "RadioTwo": field_test(amplifier_gain_db=18.5, fan_fails_at_s=300, seed=12),
}
# The drones start 1.2 km apart, near Washington, DC.
tests["RadioOne"]["flight"] = drone_flight(
    38.8895, -77.0353, width_m=500, laps=2, circle=False, seed=21
)
tests["RadioTwo"]["flight"] = drone_flight(
    38.8895, -77.0353 + 0.01729, width_m=350, laps=3, circle=True, seed=22
)
```

```{code-cell} ipython3
# Plot the simulated test for both radios.
CHANNEL_PLOTS = [
    ("power", "thermistor_voltage", "thermistor (V)"),
    ("comms", "throughput_gbps", "throughput (Gb/s)"),
    ("comms", "dropped_packets_pps", "dropped (packets/s)"),
    ("flight", "battery_voltage", "drone battery (V)"),
]
radio_colors = {"RadioOne": "#2ca02c", "RadioTwo": "#ff7f0e"}
fig = make_subplots(
    rows=len(CHANNEL_PLOTS), cols=1, shared_xaxes=True, vertical_spacing=0.04
)
for row, (scope, channel, label) in enumerate(CHANNEL_PLOTS, start=1):
    for radio, tables in tests.items():
        fig.add_scatter(
            x=tables[scope].index,
            y=tables[scope][channel],
            name=radio,
            legendgroup=radio,
            showlegend=row == 1,
            line={"color": radio_colors[radio], "width": 1},
            row=row,
            col=1,
        )
    fig.update_yaxes(title_text=label, row=row, col=1)
fig.update_yaxes(type="log", row=3, col=1)
fig.update_layout(height=760)
fig
```

The map shows where each drone flew. It opens on the centroid of both drones' tracks, with each
radio's track as a line and its takeoff point marked:

```{code-cell} ipython3
flights = pd.concat(
    [tables["flight"].assign(radio=radio) for radio, tables in tests.items()]
)
# Open the map on the centroid of all the positions, zoomed to fit both tracks.
center = {"lat": flights["latitude"].mean(), "lon": flights["longitude"].mean()}
radio_map = px.line_map(
    flights,
    lat="latitude",
    lon="longitude",
    color="radio",
    center=center,
    zoom=14,
    height=420,
)
starts = flights.groupby("radio").first().reset_index()
radio_map.add_scattermap(
    lat=starts["latitude"],
    lon=starts["longitude"],
    mode="markers+text",
    text=starts["radio"],
    textposition="top right",
    textfont={"color": "white"},
    marker={"size": 10},
    showlegend=False,
)
radio_map.update_layout(
    map_style="carto-darkmatter", margin={"l": 0, "r": 0, "t": 0, "b": 0}
)
radio_map
```

### Upload the field test

Both radios store their data under the same data scope names, `power`, `comms` and `flight`, so one workbook
template or checklist works for either radio. {py:meth}`~nominal.core.Asset.get_or_create_dataset`
creates each radio's dataset under its data scope, and `upload_dataframe_to_dataset` uploads the
test, waiting until Nominal has ingested it.

Then set each channel's unit and description. The packet-rate channels carry their unit in their
names and descriptions.

Each radio's run also gets its Touchstone files, as a record of the parts the radio had during
the test.

```{code-cell} ipython3
CHANNELS = {
    "bias_voltage": ("V", "Amplifier drain bias, regulated at 4.0 V"),
    "dc_supply_voltage": ("V", "12 V supply bus"),
    "thermistor_voltage": (
        "V",
        "NTC thermistor divider from 3.3 V. Rises as the radio warms.",
    ),
    "rx_packets_mpps": (
        None,
        "Packets received intact, in millions of packets per second (1500-byte packets)",
    ),
    "dropped_packets_pps": (
        None,
        "Packets dropped to bit errors or a full queue, in packets per second",
    ),
    "throughput_gbps": ("Gb/s", "Delivered throughput"),
    "latitude": ("°", "Drone latitude, WGS 84"),
    "longitude": ("°", "Drone longitude, WGS 84"),
    "altitude": ("m", "Drone altitude above mean sea level"),
    "groundspeed": ("m/s", "Drone speed over the ground"),
    "battery_voltage": ("V", "6S flight battery voltage"),
    "battery_remaining": ("%", "Flight battery charge remaining"),
}

runs = {}
for radio, tables in tests.items():
    asset = assets[radio]
    for scope, table in tables.items():
        dataset = asset.get_or_create_dataset(
            scope,
            name=f"{radio} {scope}",
            description=f"{radio} {scope} telemetry from field tests",
            labels=["field-test", scope],
            properties={"sample_rate_hz": SAMPLE_RATE_HZ},
        )
        upload_dataframe_to_dataset(
            dataset,
            table,
            "time",
            "iso_8601",
            file_name=f"{radio}_{scope}_{test_start:%Y%m%dT%H%M%S}.csv.gz",
        )
        for channel in dataset.get_channels():
            unit, description = CHANNELS[channel.name]
            channel.update(unit=unit, description=description)

    runs[radio] = asset.create_run(
        f"{radio} field test {test_start:%Y-%m-%d %H:%M}",
        start=times[0],
        end=times[-1],
        description="10-minute W-band link test at 20 Gb/s line rate, with the radio on a drone",
        properties={
            "site": "Range 4",
            "link_distance_km": 1.2,
            "packet_bytes": 1500,
        },
        labels=["field-test"],
        attachments=asset.list_attachments(),
    )
```

RadioTwo's fan failure and the modem stepping down become {py:class}`events <nominal.core.Event>`, so they show on the timeline
in Nominal:

```{code-cell} ipython3
# Look after the first minute, while traffic ramps up and throughput is low anyway.
throughput = tests["RadioTwo"]["comms"]["throughput_gbps"][
    test_start + pd.Timedelta(seconds=60) :
]
first_step_down = throughput[throughput < 15].index[0]
fan_failure = assets["RadioTwo"].create_event(
    "Cooling fan failure",
    EventType.ERROR,
    start=test_start + pd.Timedelta(seconds=300),
    description="Fan tachometer read zero for the rest of the test.",
    labels=["field-test"],
)
step_down = assets["RadioTwo"].create_event(
    "Modem stepped down to 14 Gb/s",
    EventType.FLAG,
    start=first_step_down,
    duration=times[-1] - first_step_down,
    description="Link margin fell below 2 dB. Excess traffic was dropped.",
    labels=["field-test"],
)
```

## Review with Nominal's Analyst

Analysis happens in the Nominal platform. Open the RadioTwo run in Nominal, then give its
assistant a prompt like the ones below to set up a workbook.

### What's in Nominal

The two radio assets are in Nominal. A card's name links to its page there, and its copy button
copies its RID. Each card lists the asset's datasets by data scope, its runs and its attachments,
and links on to them. Each Touchstone file's name downloads the file from Nominal, after signing
in if needed:

```{code-cell} ipython3
assets["RadioOne"]
```

```{code-cell} ipython3
assets["RadioTwo"]
```

### Overview of a run

A map, the key telemetry and an amplifier gain curve in one workbook.

+++

```text
make a workbook for this run that shows
 * the drone's position on a map, using the "street" base layer
 * thermistor voltage, throughput and dropped packets on separate plots, stacked
 * the distance between the two drones, computed from their latitude and longitude,
   on a new plot under dropped packets
 * the drone's battery voltage and altitude on a plot
 * the amplifier's S21 gain from the attached Touchstone file, full width at the bottom
Compare RadioOne and RadioTwo, and mark the fan failure event.
```

```{image} images/rf-radio-workbook.png
:alt: A Nominal workbook comparing RadioOne and RadioTwo, with plots of thermistor voltage, throughput, dropped packets, the distance between the drones, battery voltage and altitude, a map of the drones' flights and the amplifier's S21 gain
:width: 100%
:target: ../_images/rf-radio-workbook.png
```

### Flight telemetry against dropped packets

Both drones' flight data overlaid on dropped packets, to check whether where and how the drones flew explains RadioTwo's drops.

+++

```text
make a workbook that compares RadioOne and RadioTwo's flight telemetry against dropped packets
 * dropped packets for both radios on one plot, on a log scale, at the top
 * below it, one plot per flight channel with RadioOne and RadioTwo overlaid:
   altitude, groundspeed, battery voltage and battery remaining
 * the distance between the two drones, computed from their latitude and longitude,
   on a plot of its own
 * a scatter plot of dropped packets against the distance between the drones
 * a map of both drones' flights, using the "street" base layer
 * a table of each drone's mean altitude, mean groundspeed and battery remaining at the
   end, next to each radio's total dropped packets
Mark RadioTwo's fan failure event on every time series plot.
```

```{image} images/rf-radio-flight-workbook.png
:alt: A Nominal workbook comparing RadioOne and RadioTwo's flight telemetry against dropped packets, with plots of altitude, groundspeed, battery voltage and remaining, the distance between the drones, dropped packets against that distance, a map of the drones' flights and a summary table
:width: 100%
:target: ../_images/rf-radio-flight-workbook.png
```

### Touchstone files

One radio's component data, on a Smith chart and in log magnitude.

+++

```text
make a workbook for the RadioOne asset that shows its attached Touchstone files
 * the antenna's S11 on a Smith chart
 * the Tx filter's S21, the Rx filter's S21 and the amplifier's S21 in log magnitude (dB)
   on separate plots, stacked, with frequency in GHz
 * the Tx filter's and Rx filter's S11 in log magnitude on one plot
 * the coupler's S31 (coupled) and S41 (isolated) in log magnitude on one plot
Mark the Tx band (81–86 GHz) and the Rx band (91–96 GHz) on the log magnitude plots.
```

The workbook it builds in Nominal. Select the image to open it at full size:

```{image} images/rf-radio-touchstone-workbook.png
:alt: A Nominal workbook of RadioOne's Touchstone files, with the antenna's S11 on a Smith chart, and the Tx filter, Rx filter, amplifier, filter S11 and coupler plots in log magnitude, with the Tx and Rx bands marked
:width: 100%
:target: ../_images/rf-radio-touchstone-workbook.png
```
