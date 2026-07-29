class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class UnknownToolError(Exception):
    """Raised when the registry is asked to dispatch an unregistered tool."""


class UnsupportedModelError(Exception):
    """Raised when a backend is configured with a model it doesn't support."""


class ApiError(Exception):
    """Raised when an API request fails after exhausting retries, or fails
    with a non-retryable status."""


class LoopError(Exception):
    """Reserved for runaway agents. Not yet raised anywhere in this step —
    ported for structural parity with the Ruby source, which defines but
    never raises it either."""
