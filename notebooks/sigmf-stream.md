---
icon: pulse
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# SigMF stream

{.lead}
Replay a radio recording in real time

Stream a [SigMF](https://sigmf.org) recording to Nominal in real time, as if a software-defined
radio were capturing it now, at the recorded sample rate or a fraction of it. The recording is IQEngine's `synthetic` example by
Marc ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)): 2 seconds at 480 kS/s.

**Requirements:** a `default` [profile](https://nominal-io.github.io/nominal-client/guides/api-keys-setup/)
for the Nominal Python Client, and the packages the notebook imports, including sigmf.
[Running the notebooks](running.md) explains how to set them up.

Each execution of the notebook reuses the asset. It archives the dataset that earlier executions
streamed to, so the asset holds one dataset: this execution's.

+++

## Load the recording

A SigMF recording is a metadata file (`.sigmf-meta`) and the raw samples (`.sigmf-data`), here in
`sigmf_data/`. The metadata holds the sample rate.

```{code-cell} ipython3
import numpy as np
from sigmf import sigmffile

# This file's checksum doesn't match its data, so skip the check.
recording = sigmffile.fromfile("sigmf_data/synthetic.sigmf-meta", skip_checksum=True)
rate = float(recording.get_global_field("core:sample_rate"))  # samples per second
iq = recording.read_samples()  # complex samples
print(f"{len(iq):,} samples at {rate:,.0f} S/s = {len(iq) / rate:.1f} s")
```

## Connect to Nominal

```{code-cell} ipython3
from nominal.core import NominalClient, set_display_options

# A Nominal object at the end of a cell displays as a card.
set_display_options(time_format="readable")

client = NominalClient.from_profile("default")
```

```{code-cell} ipython3
:tags: [remove-cell]

# Start each execution with only its own data on the asset. The client cannot delete, so
# what earlier executions created is archived: datasets. The `example` property matches
# only the asset this notebook created. The page does not show this cell.
for old_asset in client.search_assets(properties={"example": "sigmf_stream"}):
    old_datasets = old_asset.list_datasets()
    old_asset.remove_data_scopes(names=[name for name, _ in old_datasets])
    for _, old_dataset in old_datasets:
        old_dataset.archive()
```

## Create the dataset

```{code-cell} ipython3
asset = client.get_or_create_asset_by_properties(
    {"example": "sigmf_stream"},
    name="VirtualSDR",
    description="A virtual software-defined radio, replaying a SigMF recording",
)
dataset = asset.get_or_create_dataset(
    "iq",
    name="iq",
    description="The recording's samples, streamed in real time",
)
dataset
```

## Stream

A radio hands over samples a buffer at a time, so the loop sends 4,096 samples (8.5 ms) when that
buffer would have finished filling. Sample *n* is stamped with the start time plus *n* / `stream_rate`,
so the data has the same spacing as a radio sampling at that rate.

`RATE_FACTOR` scales the recording's sample rate. At 1.0 the stream matches the recording's
480 kS/s. At 0.01, the default, it plays at 4.8 kS/s: the same samples, a hundred times slower. The
docs build doesn't run this cell, since it streams in real time.

Set `LOOP_FOREVER = True` to replay the recording until you interrupt the kernel, with timestamps
continuing across replays.

The status line below the cell updates every second. `lag` is how late the latest buffer was sent. It
stays near 0 ms while the loop keeps up with `stream_rate`, and the status changes to
FALLING BEHIND once it passes 100 ms.

```{code-cell} ipython3
:tags: [skip-execution]

import time

from IPython.display import display

LOOP_FOREVER = False  # True: replay until interrupted
BLOCK = 4096  # samples per buffer
RATE_FACTOR = 0.01  # 1.0: the recorded sample rate; 0.01: one hundredth of it
stream_rate = rate * RATE_FACTOR  # samples per second to stream
REPORT = 1.0  # seconds between status updates

start = time.time_ns()
sent = 0  # samples sent so far, across replays
worst_lag = 0.0  # the largest delay behind real time, in seconds
next_report = start
status = display("starting...", display_id=True)  # updated in place while streaming
with dataset.get_write_stream() as stream:
    while True:
        for i in range(0, len(iq), BLOCK):
            block = iq[i : i + BLOCK]
            index = sent + np.arange(len(block))
            times = start + np.round(index * 1e9 / stream_rate).astype("int64")
            sent += len(block)
            # wait until the buffer would have finished filling
            due = start + sent * 1e9 / stream_rate
            time.sleep(max(0.0, (due - time.time_ns()) / 1e9))
            stream.enqueue_batch("i", times, block.real)
            stream.enqueue_batch("q", times, block.imag)
            # lag: how late this buffer was sent, 0 when the loop keeps up
            lag = (time.time_ns() - due) / 1e9
            worst_lag = max(worst_lag, lag)
            if time.time_ns() >= next_report:
                next_report += int(REPORT * 1e9)
                elapsed = (time.time_ns() - start) / 1e9
                state = "OK" if lag < 0.1 else "FALLING BEHIND"
                status.update(
                    f"{state}: streamed {sent:,} samples in {elapsed:.0f} s "
                    f"({sent / elapsed:,.0f} S/s, streaming at {stream_rate:,.0f} S/s), "
                    f"lag {lag * 1e3:.1f} ms, worst {worst_lag * 1e3:.1f} ms"
                )
        if not LOOP_FOREVER:
            break
    elapsed = (time.time_ns() - start) / 1e9
status.update(
    f"done: streamed {sent:,} samples in {elapsed:.2f} s, worst lag {worst_lag * 1e3:.1f} ms"
)
```

```{code-cell} ipython3

```
