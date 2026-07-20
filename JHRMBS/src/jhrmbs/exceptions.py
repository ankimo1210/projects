class JHRMBSError(Exception):
    """Base exception for expected JHRMBS failures."""


class ConfigurationError(JHRMBSError):
    """Configuration is missing or invalid."""


class DownloadError(JHRMBSError):
    """A public source could not be downloaded safely."""


class SourceFormatError(JHRMBSError):
    """A source file no longer matches its expected structural contract."""


class DataQualityError(JHRMBSError):
    """Critical data-quality checks failed."""


class ModelError(JHRMBSError):
    """A model could not be fit, loaded, or used."""
