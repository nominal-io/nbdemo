# nominal-samples

Sample datasets for Nominal's open-source projects, grouped by domain (`aero`, `med`, `rf`). Each dataset
is available as a file path, as its format's native Python object and, where it is tabular, as a
pandas DataFrame. Large files download on first use.

```python
from nominal_samples.med import ecg_mitbih_119

ecg_mitbih_119.path    # a Path, to pass to your own loader
ecg_mitbih_119.native  # a wfdb.Record
ecg_mitbih_119.df      # a pandas.DataFrame
```

Install the extras for the formats you read: `pip install 'nominal-samples[med]'`. The docs are in
`notebooks/samples/` of the repository, and are published with the other demos.
