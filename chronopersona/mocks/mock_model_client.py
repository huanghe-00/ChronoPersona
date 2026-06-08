"""Mock model client for testing."""

from typing import Any, Dict, Iterator, Optional

from chronopersona.contracts.interfaces.abstract_model_client import (
    IModelClient,
    ModelClientError,
)
from chronopersona.contracts.schemas.model import ModelRequest


class MockModelClient(IModelClient):
    """Mock implementation of IModelClient for testing.

    Returns deterministic responses based on input prompt,
    without making real API calls. Supports pre-configured
    response mapping for specific prompts.

    Attributes:
        _provider: Provider identifier string.
        _default_model: Default model name.
        _responses: Pre-configured prompt->response mapping.
        _call_count: Number of complete() calls made (test helper).
        _stream_call_count: Number of stream_complete() calls (test helper).
        _latency_ms: Simulated response latency.
    """

    def __init__(
        self,
        provider: str = "mock",
        default_model: str = "mock-model-v1",
        responses: Optional[Dict[str, str]] = None,
        latency_ms: float = 10.0,
    ) -> None:
        """Initialize mock model client.

        Args:
            provider: Provider identifier for logging.
            default_model: Default model name to return in responses.
            responses: Optional prompt->response mapping for deterministic
                testing. Unmapped prompts return generic mock response.
            latency_ms: Simulated response latency in milliseconds.
        """
        self._provider = provider
        self._default_model = default_model
        self._responses = responses or {}
        self._call_count = 0
        self._stream_call_count = 0
        self._latency_ms = latency_ms

    def complete(
        self,
        request: ModelRequest,
    ) -> Dict[str, Any]:
        """Return a mock completion response.

        Looks up deterministic response from _responses mapping.
        Unmapped prompts return "Mock response for: {prompt[:50]}".

        Args:
            request: ModelRequest object containing prompt, task_type,
                context, max_tokens, temperature, and metadata.

        Returns:
            Mock response dictionary.
        """
        self._call_count += 1
        prompt = request.prompt
        max_tokens = getattr(request, "max_tokens", 4096)

        # Look up deterministic response
        content = self._responses.get(
            prompt, f"Mock response for: {prompt[:50]}"
        )

        resolved_model = getattr(request, "model_name", None) or self._default_model
        # Rough token estimate (2 tokens per word, per English avg)
        input_tokens = max(1, len(prompt.split()) * 2)
        output_tokens = max(1, len(content.split()) * 2)

        return {
            "content": content,
            "model_name": resolved_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "finish_reason": "stop",
            "latency_ms": self._latency_ms,
        }

    def stream_complete(
        self,
        request: ModelRequest,
    ) -> Iterator[Dict[str, Any]]:
        """Return mock streaming response chunks.

        Splits the deterministic response into 3 chunks:
        prefix, body, and final (with finish_reason="stop").

        Args:
            request: ModelRequest object containing prompt, task_type,
                context, max_tokens, temperature, and metadata.

        Returns:
            Iterator yielding 3 chunks.
        """
        self._stream_call_count += 1
        prompt = request.prompt
        content = self._responses.get(
            prompt, f"Mock stream response for: {prompt[:50]}"
        )
        resolved_model = getattr(request, "model_name", None) or self._default_model

        # Yield 3 chunks
        words = content.split()
        chunk_size = max(1, len(words) // 3)

        for i in range(3):
            start = i * chunk_size
            end = start + chunk_size if i < 2 else len(words)
            chunk_content = " ".join(words[start:end])
            finish_reason = "stop" if i == 2 else None

            yield {
                "content": chunk_content,
                "model_name": resolved_model,
                "finish_reason": finish_reason,
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Return mock model metadata.

        Returns:
            Mock model info dictionary.
        """
        return {
            "provider": self._provider,
            "default_model": self._default_model,
            "max_context_tokens": 128000,
            "supports_streaming": True,
            "pricing": {
                "input_per_1m": 0.0,
                "output_per_1m": 0.0,
            },
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Return zero cost for mock client.

        Args:
            input_tokens: Input token count.
            output_tokens: Output token count.

        Returns:
            0.0 (mock has no real cost).
        """
        return 0.0

    def health_check(self) -> bool:
        """Return True (mock client is always healthy).

        Returns:
            True.
        """
        return True

    def get_call_count(self) -> int:
        """Get the number of complete() calls (test helper).

        Returns:
            Number of complete() calls.
        """
        return self._call_count

    def get_stream_call_count(self) -> int:
        """Get the number of stream_complete() calls (test helper).

        Returns:
            Number of stream_complete() calls.
        """
        return self._stream_call_count
