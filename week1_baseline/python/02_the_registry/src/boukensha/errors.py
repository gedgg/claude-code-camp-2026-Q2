class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class UnknownToolError(Exception):
    """Raised when the registry is asked to dispatch an unregistered tool."""
