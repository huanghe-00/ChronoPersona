"""Interface for unified LLM API clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional


class ModelClientError(Exception):
    """Base exception for model client errors.

    Attributes:
        provider: The provider that encountered the error.
        status_code: HTTP status code if applicable.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: Optional[int] = None,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class RateLimitError(ModelClientError):
    """Raised when API rate limit is exceeded (HTTP 429).

    Attributes:
        retry_after: Suggested retry delay in seconds, if provided by the API.
    """

    def __init__(
        self,
        provider: str,
        retry_after: Optional[float] = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(provider, "Rate limit exceeded", status_code=429)


class ModelUnavailableError(ModelClientError):
    """Raised when the model API is unreachable or returns 5xx."""

    def __init__(self, provider: str, detail: str = "") -> None:
        super().__init__(
            provider,
            f"Model unavailable: {detail}",
            status_code=503,
        )


class IModelClient(ABC):
    """Abstract interface for LLM API clients.

    All implementations must support OpenAI-compatible chat completion API
    format, with provider-specific extensions handled via extra_headers
    and extra_body. Per AIDER.md section 2, branch_id must be explicitly
    passed in all data operations.

    Attributes:
        None
    """

    @abstractmethod
    def complete(
        self,
        prompt: str,
        task_type: str,
        branch_id: str,
        *,
        persona_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a non-streaming chat completion request.

        Args:
            prompt: The user prompt or system-injected context.
            task_type: Task tier identifier (T0-T7 per requirements 7.1).
            branch_id: Explicit branch identifier for request isolation.
            persona_id: Current persona identifier for cache key generation.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature.
            model_name: Override model name (if None, uses default for task_type).
            metadata: Additional request metadata.

        Returns:
            Dictionary containing:
                - content: str - Generated text content.
                - model_name: str - Actual model used.
                - input_tokens: int - Token count of the input.
                - output_tokens: int - Token count of the output.
                - finish_reason: str - Completion reason (e.g., "stop", "length").
                - latency_ms: float - End-to-end latency in milliseconds.

        Raises:
            RateLimitError: When API rate limit is exceeded.
            ModelUnavailableError: When the API is unreachable.
            ModelClientError: For other API errors.
        """
        ...

    @abstractmethod
    def stream_complete(
        self,
        prompt: str,
        task_type: str,
        branch_id: str,
        *,
        persona_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model_name: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Send a streaming chat completion request.

        Args:
            Same as complete(), except stream=True is implied.

        Returns:
            Iterator of dictionaries, each containing:
                - content: str - Text chunk.
                - model_name: str - Model name (in first chunk).
                - finish_reason: Optional[str] - None until last chunk.

        Raises:
            RateLimitError: When API rate limit is exceeded.
            ModelUnavailableError: When the API is unreachable.
            ModelClientError: For other API errors.
        """
        ...

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Retrieve model metadata and configuration.

        Returns:
            Dictionary containing:
                - provider: str - Provider identifier.
                - default_model: str - Default model name.
                - max_context_tokens: int - Maximum context window.
                - supports_streaming: bool - Whether streaming is supported.
                - pricing: Dict - Per-token pricing info.
        """
        ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate the USD cost for a request.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the model API endpoint is reachable.

        Returns:
            True if the API responds to a lightweight request within timeout.
        """
        ...
