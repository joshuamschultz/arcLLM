"""ArcLLM exception hierarchy."""


class ArcLLMError(Exception):
    """Base exception for all ArcLLM errors."""


class ArcLLMParseError(ArcLLMError):
    """Raised when tool call arguments cannot be parsed.

    Stores the raw string and original error so agents can log,
    retry, or surface the failure.
    """

    def __init__(self, raw_string: str, original_error: Exception) -> None:
        self.raw_string = raw_string
        self.original_error = original_error
        super().__init__(
            f"Failed to parse tool call arguments: {original_error}"
        )


class ArcLLMConfigError(ArcLLMError):
    """Raised on configuration validation failure."""
