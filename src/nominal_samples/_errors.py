class SamplesError(Exception):
    """Base class for errors raised by nominal-samples."""


class ManifestError(SamplesError):
    """A ``dataset.toml`` is missing a field or has an invalid one."""


class ChecksumError(SamplesError):
    """A downloaded file does not match the sha256 in its manifest."""


class FormUnavailable(AttributeError):
    """A dataset has no ``native`` or ``df`` form.

    Subclasses :py:class:`AttributeError`, so ``hasattr(dataset, "df")`` is ``False`` for such a dataset.
    """


class MissingExtraError(ImportError):
    """A library that a loader needs is not installed."""
