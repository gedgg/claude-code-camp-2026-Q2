class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class UnknownToolError(Exception):
    """Raised when the registry is asked to dispatch an unregistered tool."""


class UnsupportedModelError(Exception):
    """Raised when a backend is configured with a model it doesn't support."""
