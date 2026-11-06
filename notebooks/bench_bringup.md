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

% TODO: introduction. Motivation: set up monitoring of a bench.

**Requirements:** a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the Nominal Python Client, and the packages the notebook imports, including
[instro](https://instro.nominal.io). [Running the notebooks](running.md) explains how to set them
up.

+++

## The bench

The bench powers a power-conversion board, the device under test (DUT). Each instrument connects
to the bench PC. On the PC, instro reads each instrument and streams its data to Nominal. Each
instrument box shows the instrument's instro name.

```mermaid
block-beta
  columns 6
  block:shelf:3
    columns 3
    dmm["DMM<br>dut_dmm"] psu["Power supply<br>bench_psu"] load["Electronic load<br>dut_load"]
  end
  space:2
  pc["💻 Bench PC<br>instro"]
  space:6
  block:fixture:3
    columns 3
    rail["Fixture<br>5 V rail"] space dut["DUT"]
  end
  space:2
  nominal[("Nominal")]
  dmm -- "leads" --> rail
  psu -- "5 V" --> rail
  psu -- "12 V" --> dut
  dut -- "5 V, 1 A" --> load
  shelf -- "USB / LAN" --> pc
  pc -- "stream" --> nominal
```

On a real bench, each instrument uses the instro driver for its model, with the instrument's VISA
address. For example, for a Keysight 34461A DMM on the network:

```python
from instro.dmm.drivers import Keysight34461A

dmm_hardware = Keysight34461A("TCPIP::192.168.1.20::INSTR")
```

instro has drivers for power supplies, DMMs, electronic loads, oscilloscopes and other instruments
from many vendors. The [instro documentation](https://instro.nominal.io) lists them. This notebook
uses instro's virtual drivers, which simulate the instruments, so it needs no hardware. Only the
driver changes on a real bench. The rest of the code stays the same.

```{code-cell} ipython3
from instro.dmm import MeasurementFunction
from instro.dmm.drivers import VirtualDMM
from instro.eload.drivers import VirtualELoad
from instro.psu.drivers import VirtualPSU

psu_hardware = VirtualPSU(num_channels=2, load_resistance={1: 24.0, 2: 10.0})
dmm_hardware = VirtualDMM({MeasurementFunction.DC_VOLTAGE: 12.0})
eload_hardware = VirtualELoad(source_voltage=5.0, source_resistance=0.05)
```

## Connect the bench to Nominal

The bench is a Nominal asset. Every instrument streams to the asset's `bench` dataset. A run marks
the bring-up session. Keep the run open in Nominal during bring-up, with **Open in Nominal** on its
card.

```{code-cell} ipython3
import pandas as pd
from nominal.core import NominalClient, set_display_options

# Show readable timestamps on Nominal's cards.
set_display_options(time_format="readable")

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

## Connect the instruments

Each instrument's setup comes from an earlier script. An instro instrument reads its driver in a
background daemon, and sends each reading to its publishers. A `NominalCorePublisher` streams the
readings to a Nominal dataset. instro names each channel `<instrument name>.<channel>`.

### The power supply

```{code-cell} ipython3
import time

from instro.lib import set_display_options as set_instro_display_options
from instro.lib.publishers import NominalCorePublisher
from instro.lib.types import BackgroundDaemonConfig
from instro.psu import InstroPSU

# Show readable timestamps on instro's cards.
set_instro_display_options(time_format="readable")

psu = InstroPSU(
    name="bench_psu",
    driver=psu_hardware,
    num_channels=2,
    # Stream every reading to the bench's dataset.
    publishers=[NominalCorePublisher(dataset=dataset)],
    # Read both outputs every 100 ms.
    background_config=BackgroundDaemonConfig(interval=0.1),
)
psu.open()
psu.apply(current_limit=1.0, voltage=12.0, enable=True, channel=1)
psu.apply(current_limit=1.0, voltage=5.0, enable=True, channel=2)
psu.start()
time.sleep(1)
psu
```

The power supply reads the voltage, the current and the enable state of each output. Each
instrument also records its daemon's timing in `loop_time` and `daemon_work_time`.

### The DMM

```{code-cell} ipython3
from instro.dmm import InstroDMM

dmm = InstroDMM(
    name="dmm",
    driver=dmm_hardware,
    publishers=[NominalCorePublisher(dataset=dataset)],
    background_config=BackgroundDaemonConfig(interval=0.1),
)
dmm.open()
dmm.set_measurement_function(MeasurementFunction.DC_VOLTAGE)
dmm.start()
time.sleep(1)
dmm
```

The DMM reads one value: the DC voltage.

### The electronic load

```{code-cell} ipython3
from instro.eload import InstroELoad, LoadMode

eload = InstroELoad(name="dut_load", driver=eload_hardware)
eload.open()
# Sink a constant 1 A.
eload.set_mode(LoadMode.CC)
eload.set_level(1.0)
eload.output_enable(True)
eload.start()
time.sleep(1)
eload
```

The electronic load reads the voltage and the current at its input.

## Check the bench's data

Each card shows what instro reads from its instrument. A test reads its data from Nominal. Before
the test starts, make sure that each channel the test reads:

- gets to Nominal, under the name that the test uses
- has a value in the expected range
- arrives at the rate that the test needs

The test spec gives this information. It names each channel that the test reads, with the range of
values that the test expects, and the lowest rate that the test accepts.

```{code-cell} ipython3
SPEC = {
    "channels": {
        "bench_psu.ch1.voltage": (11.8, 12.2),
        "bench_psu.ch1.current": (0.45, 0.55),
        "bench_psu.ch2.voltage": (4.9, 5.1),
        "bench_psu.ch2.current": (0.45, 0.55),
        "dut_dmm.dc_voltage": (4.9, 5.1),
        "dut_load.ch1.voltage": (4.85, 5.0),
        "dut_load.ch1.current": (0.95, 1.05),
    },
    "min_rate_hz": 9.5,
}
```

`check()` gets the last few seconds of the bench's data from Nominal, and compares each channel
with the spec. It also reports an instrument that sends data but that the spec doesn't name.

```{code-cell} ipython3
from nominal.thirdparty.pandas import datasource_to_dataframe


def check(spec: dict, window_s: float = 10) -> pd.DataFrame:
    """Compare the last ``window_s`` seconds of the bench's data in Nominal with ``spec``."""
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(seconds=window_s)
    data = datasource_to_dataframe(dataset, start=start, end=end)
    data.index = pd.to_datetime(data.index)

    report = {}
    for channel, (low, high) in spec["channels"].items():
        values = data[channel].dropna() if channel in data else pd.Series()
        if values.empty:
            report[channel] = {"status": "no data"}
            continue
        latest = values.iloc[-1]
        # The rate from the median interval between samples. One sample gives no rate.
        intervals = values.index.diff().dropna()
        rate = 1 / intervals.median().total_seconds() if len(intervals) else 0
        if not low <= latest <= high:
            status = "out of range"
        elif rate < spec["min_rate_hz"]:
            status = "too slow"
        else:
            status = "ok"
        report[channel] = {"latest": latest, "rate (Hz)": rate, "status": status}

    # An instrument that sends data, but that the spec doesn't name.
    named = {channel.split(".")[0] for channel in spec["channels"]}
    sent = data.dropna(axis="columns", how="all")
    sending = {channel.split(".")[0] for channel in sent}
    for instrument in sorted(sending - named):
        report[f"{instrument}.*"] = {"status": "not in spec"}

    report = pd.DataFrame.from_dict(report, orient="index").round(3)
    # Show a value that a row doesn't have as an empty cell.
    return report.astype(object).fillna("")
```

```{code-cell} ipython3
check(SPEC)
```

The power supply's channels pass. The check finds two problems:

- The DMM's data arrives as `dmm.dc_voltage`, so `dut_dmm.dc_voltage` has no data. The script
  named the DMM `dmm`.
- The electronic load's channels have no data. Its card shows that its only publisher is the
  **in-memory buffer**, so nothing goes to Nominal.

To rename the DMM, edit its script and connect it again. Give the electronic load a Nominal
publisher.

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

eload.add_publisher(NominalCorePublisher(dataset=dataset))

# Wait until the window holds only data from after the changes.
time.sleep(15)
check(SPEC)
```

The DMM and the electronic load now send their data to Nominal. The check finds two more problems:

- `dut_dmm.dc_voltage` is 12 V, where the spec expects the 5 V rail. The DMM's leads are on the
  power supply's 12 V output.
- The electronic load's channels are too slow. Its card shows **Background** every second, where
  the spec needs 10 Hz.

Move the DMM's leads to the 5 V rail, and set the electronic load's daemon to 10 Hz:

```{code-cell} ipython3
# In the simulation, moving the leads changes the voltage that the virtual DMM reads.
dmm_hardware.stimulus[MeasurementFunction.DC_VOLTAGE] = 5.0
eload.background_interval = 0.1

time.sleep(15)
check(SPEC)
```

Every channel in the spec passes the check.

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
import matplotlib.pyplot as plt

plt.style.use("dark_background")

session = datasource_to_dataframe(
    dataset,
    channels=[dataset.get_channel("dut_dmm.dc_voltage")],
    start=run.start,
    end=run.end,
)
session.index = pd.to_datetime(session.index)
session.plot(style=".", figsize=(12, 3), ylabel="V", legend=False);
```
