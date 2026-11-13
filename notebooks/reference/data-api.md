# nbdemo.data API

```{eval-rst}
.. automodule:: nbdemo.data
   :no-members:

.. autofunction:: nbdemo.data.catalog
.. autofunction:: nbdemo.data.get
.. autofunction:: nbdemo.data.domains
.. autofunction:: nbdemo.data.cache_dir
```

## Domains

Each domain module resolves dataset names when you import them, so there is no fixed list of attributes.
`dir()` of a domain lists its datasets; the {doc}`catalog <data-catalog>` shows them all.

```{eval-rst}
.. automodule:: nbdemo.data.aero
.. automodule:: nbdemo.data.med
.. automodule:: nbdemo.data.rf
```

## Dataset

```{eval-rst}
.. autoclass:: nbdemo.data.Dataset
   :members: from_dir, id, size, is_local, forms, paths, path, native, df, verify

.. autoclass:: nbdemo.data.FileSpec
   :members:
```

## Errors

```{eval-rst}
.. autoexception:: nbdemo.data.SamplesError
.. autoexception:: nbdemo.data.ManifestError
.. autoexception:: nbdemo.data.ChecksumError
.. autoexception:: nbdemo.data.FormUnavailable
.. autoexception:: nbdemo.data.MissingExtraError
```
