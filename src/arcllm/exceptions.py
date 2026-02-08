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


class ArcLLMAPIError(ArcLLMError):
    """Raised when a provider API returns an HTTP error.

    Carries status_code, body, and provider so agents and the retry
    module can make smart decisions (e.g., 429 → retry, 401 → don't).
    """

    def __init__(self, status_code: int, body: str, provider: str) -> None:
        self.status_code = status_code
        self.body = body
        self.provider = provider
        super().__init__(f"{provider} API error (HTTP {status_code}): {body}")
