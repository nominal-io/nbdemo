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

**Requirements:** a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the Nominal Python Client, and the packages the notebook imports, including instro.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the bench's asset. It archives what earlier executions
created on the asset, so the asset holds one run: this execution's.

+++

## Setup

```{code-cell} ipython3
import time

import matplotlib.pyplot as plt
import numpy as np
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

# Nominal's and instro's cards each have display options: show readable timestamps in both.
set_display_options(time_format="readable")
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

The bench powers a power-conversion board, the device under test (DUT):

| Instrument | instro name | Wiring |
| --- | --- | --- |
| Power supply | `bench_psu` | output 1: 12 V into the DUT. Output 2: the fixture's 5 V rail. |
| DMM | `dut_dmm` | DC voltage across the 5 V rail |
| Electronic load | `dut_load` | sinks 1 A from the DUT's 5 V output |

Each instrument uses an instro virtual driver. The DMM's leads were clipped to the wrong output
of the power supply, so it reads 12 V.

```{code-cell} ipython3
psu_hardware = VirtualPSU(num_channels=2, load_resistance={1: 24.0, 2: 10.0})
dmm_hardware = VirtualDMM({MeasurementFunction.DC_VOLTAGE: 12.0})
eload_hardware = VirtualELoad(source_voltage=5.0, source_resistance=0.05)
```

The bench is a Nominal asset, and every instrument streams to the asset's `bench` dataset. A run
marks the bring-up session. Keep it open in Nominal during bring-up, with **Open in Nominal** on
its card.

```{code-cell} ipython3
bench = client.get_or_create_asset_by_properties(
    {"bench_id": "bench-7", "example": "bench_bringup"}, name="Bench 7"
)
dataset = bench.get_or_create_dataset("bench", name="Bench 7 instruments")
# end=None leaves the run open until the session ends.
run = bench.create_run(
    "Bench 7 bring-up", start=pd.Timestamp.now(tz="UTC").floor("s"), end=None
)
run
```

### The test spec

The test spec names each channel it reads, with the range it expects. It needs every channel at
10 Hz.

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
# Below 10 Hz, because the newest second of data may not have reached Nominal yet.
MIN_RATE_HZ = 5.0
WINDOW_S = 10


def check(window_s: float = WINDOW_S) -> pd.DataFrame:
    """Compare the last ``window_s`` seconds of the bench's data in Nominal with ``SPEC``.

    Args:
        window_s (float): Length of the window that ends now, in seconds.

    Returns:
        pandas.DataFrame: A row for each channel in ``SPEC``, and for each channel of an
        instrument ``SPEC`` doesn't name that sent data in the window. Each row has the
        channel's rate in Hz, its latest value and a status.
    """
    end = pd.Timestamp.now(tz="UTC")
    data = datasource_to_dataframe(
        dataset, start=end - pd.Timedelta(seconds=window_s), end=end
    ).dropna(axis="columns", how="all")
    # Keep the test spec's channels, and every channel of an instrument it doesn't name.
    instruments = {name.split(".")[0] for name in SPEC}
    data = data[[c for c in data if c in SPEC or c.split(".")[0] not in instruments]]
    report = pd.DataFrame(SPEC, index=["low", "high"]).T.join(
        pd.DataFrame(
            {"rate (Hz)": data.count() / window_s, "latest": data.ffill().iloc[-1]}
        ),
        how="outer",
    )
    report["status"] = np.select(
        [
            report["rate (Hz)"].isna(),
            report["low"].isna(),
            report["rate (Hz)"] < MIN_RATE_HZ,
            ~report["latest"].between(report["low"], report["high"]),
        ],
        ["no data", "not in spec", "too slow", "out of range"],
        "ok",
    )
    return report.round(3)
```

## Bring up the bench

Run `check()` after each change on the bench.

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
check()
```

The power supply's channels pass. The DMM and the electronic load aren't connected yet, so their
channels have `no data`.

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
check()
```

`dmm.dc_voltage` is `not in spec`, and `dut_dmm.dc_voltage` has no data. instro names every
channel `<instrument name>.<channel>`, so rename the DMM. As on a real bench, that means editing
the script and connecting the DMM again.

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
check()
```

The DMM's data now arrives as `dut_dmm.dc_voltage`, but it reads 12 V where the test spec expects
the 5 V rail. Move the leads to output 2. The DMM's card shows the new reading within a second,
without waiting for Nominal.

```{code-cell} ipython3
# In the simulation, moving the leads changes the voltage the virtual DMM reads.
dmm_hardware.stimulus[MeasurementFunction.DC_VOLTAGE] = 5.0
time.sleep(1)
dmm
```

```{code-cell} ipython3
# Wait for a full window of data from after the move.
time.sleep(WINDOW_S)
check()
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
check()
```

The electronic load's channels have no data. Its card shows that it works, but its only publisher
is the **in-memory buffer**, so nothing goes to Nominal. **Background** also runs every second,
where the test spec needs 10 Hz.

```{code-cell} ipython3
eload
```

Add a Nominal publisher, and set the daemon to 10 Hz:

```{code-cell} ipython3
eload.add_publisher(NominalCorePublisher(dataset=dataset))
eload.background_interval = 0.1
time.sleep(WINDOW_S)
check()
```

Every channel in the test spec passes the check.

## End the session

```{code-cell} ipython3
# Closing an instrument stops its daemon and flushes its stream to Nominal.
for instrument in [psu, dmm, eload]:
    instrument.close()
run.update(end=pd.Timestamp.now(tz="UTC").ceil("s"))
bench
```

The bench's card shows its run and its dataset. Over the run, the DMM steps from 12 V to 5 V when
its leads move:

```{code-cell} ipython3
session = datasource_to_dataframe(
    dataset,
    channels=[dataset.get_channel("dut_dmm.dc_voltage")],
    start=run.start,
    end=run.end,
)
session.index = pd.to_datetime(session.index)
session.plot(style=".", figsize=(12, 3), ylabel="V", legend=False);
```
