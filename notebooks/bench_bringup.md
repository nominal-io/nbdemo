---
icon: plug
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Bench bring-up with instro

{.lead}
Check each instrument's data as you connect a bench

When you connect a new bench one instrument at a time, check after each one that its channels
reach Nominal under the names your test spec uses, at plausible values and at the rate the test
spec needs. This notebook does that with three virtual [instro](https://instro.nominal.io)
instruments streaming to a Nominal run, so it needs no hardware.

You check each instrument from two sides. Its instro card shows what the instrument publishes,
within seconds and without Nominal. `check_run`, defined below, shows what reached the Nominal run.

**Requirements:** a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the Nominal Python Client, and the packages the notebook imports, including instro.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the bench's asset. It archives what earlier executions
created on the asset, so the asset holds one run: this execution's.

+++

## Setup

### Connect to Nominal

```{code-cell} ipython3
import time

import matplotlib.pyplot as plt
import pandas as pd
from instro.dmm import InstroDMM, MeasurementFunction
from instro.dmm.drivers import VirtualDMM
from instro.eload import InstroELoad, LoadMode
from instro.eload.drivers import VirtualELoad
from instro.lib import set_display_options as set_instro_display_options
from instro.lib.publishers import NominalCorePublisher
from instro.lib.types import BackgroundDaemonConfig
from instro.psu import InstroPSU
from instro.psu.drivers import VirtualPSU
from nominal.core import NominalClient, set_display_options
from nominal.thirdparty.pandas import datasource_to_dataframe

# Nominal objects and instro instruments both display as cards. Each library has its own
# display options: show timestamps in a readable format in both. In Nominal's cards, also open
# the sections and relationship diagrams with up to 10 items, which are folded by default.
set_display_options(time_format="readable", collapse_threshold=10)
set_instro_display_options(time_format="readable")
plt.style.use("dark_background")

client = NominalClient.from_profile("default")
```

```{code-cell} ipython3
:tags: [remove-cell]

import warnings

# instro's Nominal publisher asks this nominal-client for its stream with a deprecated argument.
# The warnings don't affect the demo. The page does not show this cell.
warnings.filterwarnings(
    "ignore",
    message=r"(The `data_format` argument|implementation='rust_experimental') is deprecated",
    category=UserWarning,
)

# Start each execution with only its own data on the bench. The client cannot delete, so what
# earlier executions created is archived: runs and datasets. The `example` property matches
# only the bench this notebook created.
for old_asset in client.search_assets(properties={"example": "bench_bringup"}):
    for old_run in old_asset.list_runs():
        if not old_run.is_archived:
            old_run.archive()
    old_datasets = old_asset.list_datasets()
    old_asset.remove_data_scopes(names=[name for name, _ in old_datasets])
    for _, old_dataset in old_datasets:
        old_dataset.archive()
```

### Simulate the bench

The bench powers a power-conversion board, the device under test (DUT):

| Instrument | instro name | Wiring |
| --- | --- | --- |
| Power supply | `bench_psu` | output 1: 12 V into the DUT, drawing 0.5 A. Output 2: the fixture's 5 V rail, also 0.5 A. |
| DMM | `dut_dmm` | DC voltage across the 5 V rail, at the DUT |
| Electronic load | `dut_load` | sinks 1 A from the DUT's 5 V output |

Each instrument uses an instro virtual driver. The DMM's leads were clipped to the wrong output
of the power supply.

```{code-cell} ipython3
:tags: [hide-input]

class LeadsOnPSU(VirtualDMM):
    """A virtual DMM whose leads sit across one output of a virtual power supply."""

    def __init__(self, psu: VirtualPSU, channel: int):
        """Clip the DMM's leads across an output of ``psu``.

        Args:
            psu (VirtualPSU): The power supply the leads sit on.
            channel (int): The power supply output the leads sit across, from 1. Change it to
                move the leads.

        Example::

            psu = VirtualPSU(num_channels=2)
            dmm = InstroDMM(name="dmm", driver=LeadsOnPSU(psu, channel=2))
        """
        super().__init__()
        self.psu = psu
        self.channel = channel

    def measure_dc_voltage(self) -> float:
        """Return the voltage of the output the leads sit across, in volts."""
        return self.psu.get_voltage(self.channel)


psu_hardware = VirtualPSU(num_channels=2, load_resistance={1: 24.0, 2: 10.0})
# The leads belong on output 2, the 5 V rail.
dmm_hardware = LeadsOnPSU(psu_hardware, channel=1)
eload_hardware = VirtualELoad(source_voltage=5.0, source_resistance=0.05)
```

### Register the bench and start a run

The bench is a Nominal asset, and every instrument streams to the asset's `bench` dataset. A run
marks the bring-up session.

```{code-cell} ipython3
EXAMPLE = "bench_bringup"

bench = client.get_or_create_asset_by_properties(
    {"bench_id": "bench-7", "example": EXAMPLE},
    name="Bench 7",
    description="Power-conversion test bench",
    labels=["bench"],
)
dataset = bench.get_or_create_dataset(
    "bench",
    name="Bench 7 instruments",
    description="Every instrument on Bench 7, streamed by instro",
)
session_start = pd.Timestamp.now(tz="UTC").floor("s")
# end=None leaves the run open until the session ends.
run = bench.create_run(
    f"Bench 7 bring-up {session_start:%Y-%m-%d %H:%M}",
    start=session_start,
    end=None,
    description="Connecting Bench 7's instruments one at a time",
    labels=["bring-up"],
)
RUN_RID = run.rid
```

Keep the run open in Nominal during bring-up. Its card links to it with **Open in Nominal**.

The card's **Relationships** diagram shows where the instruments' data goes. The run sits above
the Bench 7 asset, and the `bench` dataset feeds the asset under its data scope's ref name. Each
node links to its page in Nominal.

```{code-cell} ipython3
run
```

### The test spec, and `check_run`

The test spec names each channel it reads and the range it expects while the bench idles. It
needs every channel at 10 Hz.

```{code-cell} ipython3
SPEC = {
    "bench_psu.ch1.voltage": (11.8, 12.2),
    "bench_psu.ch1.current": (0.45, 0.55),
    "bench_psu.ch2.voltage": (4.9, 5.1),
    "bench_psu.ch2.current": (0.45, 0.55),
    "dut_dmm.dc_voltage": (4.9, 5.1),
    "dut_load.ch1.voltage": (4.85, 5.0),
    "dut_load.ch1.current": (0.95, 1.05),
}
MIN_RATE_HZ = 8.0
WINDOW_S = 10
```

Re-run `check_run` after each change on the bench. It reads the last `WINDOW_S` seconds of the
run's datasets from Nominal and gives each channel a status:

- **ok**: the channel passes the check.
- **no data**: nothing arrived in the window. The channel isn't collecting, or isn't named as the
  test spec expects.
- **too slow**: samples arrive less often than `MIN_RATE_HZ`.
- **out of range**: the latest value is outside the test spec's range, as when signals are
  cross-wired.
- **not in spec**: an instrument the test spec doesn't name sent data in the window, as when an
  instrument is misnamed.

```{code-cell} ipython3
STATUS_COLORS = {
    "ok": "#2e7d32",
    "too slow": "#8a5200",
    "out of range": "#c62828",
    "no data": "#c62828",
    "not in spec": "#8a5200",
}


def check_run(run_rid: str, window_s: float = WINDOW_S):
    """Check the last ``window_s`` seconds of a run's data in Nominal against ``SPEC``.

    Args:
        run_rid (str): RID of the run to check.
        window_s (float): Length of the window that ends now, in seconds.

    Returns:
        pandas.io.formats.style.Styler: A row for each channel in ``SPEC``, and for each
        channel of an instrument ``SPEC`` doesn't name that sent data in the window.
    """
    run = client.get_run(run_rid)
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(seconds=window_s)
    spec_instruments = {name.split(".")[0] for name in SPEC}

    received: dict[str, pd.Series] = {}
    for _, dataset in run.list_datasets():
        # The test spec's channels, and every channel of an instrument it doesn't name.
        channels = [
            channel
            for channel in dataset.search_channels()
            if channel.name in SPEC
            or channel.name.split(".")[0] not in spec_instruments
        ]
        if channels:
            data = datasource_to_dataframe(
                dataset, channels=channels, start=start, end=end
            )
            received.update({name: data[name].dropna() for name in data.columns})

    rows = {}
    for name, (low, high) in SPEC.items():
        values = received.get(name, pd.Series(dtype=float))
        rows[name] = _summary(values, end, f"{low:g} to {high:g}")
        if values.empty:
            rows[name]["status"] = "no data"
        elif rows[name]["rate (Hz)"] < MIN_RATE_HZ:
            rows[name]["status"] = "too slow"
        elif not low <= values.iloc[-1] <= high:
            rows[name]["status"] = "out of range"
        else:
            rows[name]["status"] = "ok"
    for name, values in received.items():
        if name not in SPEC and not values.empty:
            rows[name] = {**_summary(values, end, ""), "status": "not in spec"}

    return (
        pd.DataFrame.from_dict(rows, orient="index")
        .style.format(
            {
                "rate (Hz)": "{:.1f}",
                "latest": "{:.3f}",
                "last sample (s ago)": "{:.1f}",
            },
            na_rep="",
        )
        .map(
            lambda status: (
                f"background-color: {STATUS_COLORS[status]}; color: white"
            ),
            subset=["status"],
        )
    )


def _summary(values: pd.Series, now: pd.Timestamp, expected: str) -> dict:
    """Summarize one channel's data in the window.

    Args:
        values (pandas.Series): The channel's values, indexed by timestamp.
        now (pandas.Timestamp): The end of the window.
        expected (str): The test spec's range, as shown in the table.

    Returns:
        dict: The sample count, the rate in Hz from the median spacing, the latest value, the
        expected range, and the latest sample's age in seconds.
    """
    if values.empty:
        return {"samples": 0, "expected": expected}
    times = pd.to_datetime(values.index, utc=True).to_series()
    spacing = times.diff().median().total_seconds()
    return {
        "samples": len(values),
        "rate (Hz)": 1 / spacing if spacing > 0 else float("nan"),
        "latest": values.iloc[-1],
        "expected": expected,
        "last sample (s ago)": (now - times.iloc[-1]).total_seconds(),
    }
```

## Bring up the bench

### Step 1: the power supply

```{code-cell} ipython3
psu = InstroPSU(
    name="bench_psu",
    driver=psu_hardware,
    num_channels=2,
    # Stream every value to the bench's dataset.
    publishers=[NominalCorePublisher(dataset=dataset)],
    # Read both outputs every 100 ms.
    background_config=BackgroundDaemonConfig(interval=0.1),
)
psu.open()
psu.apply(current_limit=1.0, voltage=12.0, enable=True, channel=1)
psu.apply(current_limit=1.0, voltage=5.0, enable=True, channel=2)
psu.start()
time.sleep(WINDOW_S)
```

An instro instrument at the end of a cell displays as a card. instro builds the card from what it
holds in memory, so displaying it never talks to the hardware. The power supply's card shows:

- **Background**: the daemon runs every 100 ms.
- **Publishers**: the Nominal publisher, with a link to the dataset, its sent count and no
  errors. The **in-memory buffer** is instro's buffer of recent values.
- **Channels**: every channel the power supply has published, with its latest value and rate.
  Settings sent to the power supply are `.cmd` channels.

```{code-cell} ipython3
psu
```

In Nominal, the power supply's channels are `ok`. The DMM and the electronic load aren't
connected yet, so their channels have `no data`.

```{code-cell} ipython3
check_run(RUN_RID)
```

### Step 2: the DMM

The DMM's setup comes from another bench's script, which named the DMM `dmm`.

```{code-cell} ipython3
dmm = InstroDMM(
    name="dmm",
    driver=dmm_hardware,
    publishers=[NominalCorePublisher(dataset=dataset)],
    background_config=BackgroundDaemonConfig(interval=0.1),
)
dmm.open()
dmm.set_measurement_function(MeasurementFunction.DC_VOLTAGE)
dmm.start()
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

`dut_dmm.dc_voltage` has no data, and `dmm.dc_voltage` isn't in the test spec, so the DMM's data
arrives under the wrong name. instro names every channel `<instrument name>.<channel>`. The DMM's
card shows the instrument name in its title:

```{code-cell} ipython3
dmm
```

Rename the DMM. As on a real bench, that means editing the script and connecting the DMM again.

```{code-cell} ipython3
dmm.close()
dmm = InstroDMM(
    name="dut_dmm",
    driver=dmm_hardware,
    publishers=[NominalCorePublisher(dataset=dataset)],
    background_config=BackgroundDaemonConfig(interval=0.1),
)
dmm.open()
dmm.set_measurement_function(MeasurementFunction.DC_VOLTAGE)
dmm.start()
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

The DMM's data now arrives as `dut_dmm.dc_voltage`. `dmm` is no longer listed, because it sent
nothing in the window. But the DMM reads 12 V, where the test spec expects the 5 V rail. The power
supply's `ch2.voltage` reads 5 V and its `ch1.voltage` reads 12 V, so the DMM's leads are across
output 1.

Move the leads to output 2. The DMM's card shows the new reading within a second, without waiting
for Nominal.

```{code-cell} ipython3
# In the simulation, moving the leads is one attribute.
dmm_hardware.channel = 2
time.sleep(1)
dmm
```

```{code-cell} ipython3
# Wait for a full window of data from after the move.
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

### Step 3: the electronic load

The electronic load's setup comes from a script that only polled it, so it has no publishers and
its daemon runs at instro's default interval.

```{code-cell} ipython3
eload = InstroELoad(name="dut_load", driver=eload_hardware)
eload.open()
# Sink a constant 1 A.
eload.set_mode(LoadMode.CC)
eload.set_level(1.0)
eload.output_enable(True)
eload.start()
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

The electronic load's channels have no data, and no channel is `not in spec`, so the electronic
load isn't misnamed. Its card shows that it works, with plausible values arriving in memory. But
its only publisher is the **in-memory buffer**, so nothing goes to Nominal. The card also shows the
next problem: **Background** runs every second, so each channel's rate is 1/s.

```{code-cell} ipython3
eload
```

Add a Nominal publisher. A publisher gets only the values published after you add it.

```{code-cell} ipython3
eload.add_publisher(NominalCorePublisher(dataset=dataset))
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

The electronic load's data now reaches Nominal, at 1 Hz, which is `too slow` for the test spec.
Set its daemon to 10 Hz:

```{code-cell} ipython3
eload.background_interval = 0.1
time.sleep(WINDOW_S)
check_run(RUN_RID)
```

Every channel in the test spec passes the check.

## End the session

```{code-cell} ipython3
# Closing an instrument stops its daemon and closes its publishers, which flushes the stream
# to Nominal.
for instrument in [psu, dmm, eload]:
    instrument.close()
# Close the run at the end of the session.
run.update(end=pd.Timestamp.now(tz="UTC").ceil("s"));
```

The run's card now shows the session's end and duration:

```{code-cell} ipython3
run
```

The Nominal publisher's card links to the dataset that holds the session, and marks the stream
closed:

```{code-cell} ipython3
psu.publishers[0]
```

The bench's asset card draws the same relationships from the asset's side: its run above it, and
its dataset below it. A bench that runs many sessions collects a run for each. The diagram then
draws the newest runs and a node counting the rest.

```{code-cell} ipython3
bench
```

### The session, from Nominal

The DMM and electronic load channels over the run show both fixes. The DMM steps from 12 V to 5 V
when its leads move, and the electronic load's samples arrive ten times as often after its
interval changes.

```{code-cell} ipython3
channels = ["dut_dmm.dc_voltage", "dut_load.ch1.current"]
# Download the run's span of the two channels.
session = datasource_to_dataframe(
    dataset,
    channels=[dataset.get_channel(name) for name in channels],
    start=run.start,
    end=run.end,
)
session.index = pd.to_datetime(session.index, utc=True)

fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
for ax, name, unit in zip(axes, channels, ["V", "A"], strict=True):
    # Markers show each sample, so the change in rate is visible.
    session[name].dropna().plot(ax=ax, marker=".", markersize=3, linewidth=0.8)
    ax.set_ylabel(f"{name} ({unit})")
axes[-1].set_xlabel("time (UTC)")
fig.tight_layout()
```
