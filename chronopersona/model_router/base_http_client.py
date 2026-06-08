"""Base HTTP client for OpenAI-compatible LLM API calls."""

import json
import time
from typing import Any, Dict, Iterator, Optional, Tuple

import httpx
from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)
from chronopersona.contracts.interfaces.abstract_model_client import (
    IModelClient,
    ModelClientError,
    ModelUnavailableError,
    RateLimitError,
)


class BaseHttpClient(IModelClient):
    """Base HTTP client implementing OpenAI-compatible chat completion API.

    Provides retry with exponential backoff, rate limit handling,
    and latency tracking. Provider-specific subclasses override
    _get_provider_name(), _get_default_model(), and
    _apply_provider_specific_params().

    Attributes:
        _credential_provider: Credential provider for API keys.
        _timeout: Request timeout in seconds.
        _max_retries: Maximum retry attempts for transient errors.
        _client: httpx synchronous client instance.
    """

    RETRY_BACKOFF_BASE = 1.0  # Initial backoff in seconds
    RETRY_BACKOFF_MAX = 8.0  # Maximum backoff
    RETRY_MAX_ATTEMPTS = 4  # Maximum retry attempts per requirements 11

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the base HTTP client.

        Args:
            credential_provider: Provider for API credentials.
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
        """
        self._credential_provider = credential_provider
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=timeout)

    def _get_provider_name(self) -> str:
        """Return the provider identifier string.

        Subclasses must override this.

        Returns:
            Provider name (e.g., "kimi", "deepseek", "glm").
        """
        raise NotImplementedError("Subclasses must implement _get_provider_name()")

    def _get_default_model(self) -> str:
        """Return the default model name for this provider.

        Subclasses must override this.

        Returns:
            Default model identifier.
        """
        raise NotImplementedError("Subclasses must implement _get_default_model()")

    def _apply_provider_specific_params(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Apply provider-specific modifications to request payload and headers.

        Subclasses override this to add extra headers or body params
        required by their specific API (e.g., Kimi's User-Agent,
        DeepSeek's thinking mode).

        Args:
            payload: The request payload dict.
            headers: The request headers dict.

        Returns:
            Modified (payload, headers) tuple.
        """
        return payload, headers

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
        """Send a non-streaming chat completion request with retry.

        Args:
            prompt: The user prompt.
            task_type: Task tier identifier.
            branch_id: Explicit branch identifier.
            persona_id: Current persona identifier.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.
            model_name: Override model name.
            metadata: Additional metadata.

        Returns:
            Response dict with content, model_name, input_tokens,
            output_tokens, finish_reason, latency_ms.

        Raises:
            RateLimitError: When rate limit exceeded after all retries.
            ModelUnavailableError: When API unreachable after all retries.
            ModelClientError: For other non-retryable errors.
        """
        provider = self._get_provider_name()
        resolved_model = model_name or self._get_default_model()

        payload = self._build_payload(
            prompt, resolved_model, max_tokens, temperature, stream=False
        )
        headers = self._build_headers(provider, branch_id)
        payload, headers = self._apply_provider_specific_params(payload, headers)

        api_base = self._credential_provider.get_api_base(provider)
        url = f"{api_base}/chat/completions"

        start_time = time.monotonic()

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.post(url, json=payload, headers=headers)
                latency_ms = (time.monotonic() - start_time) * 1000

                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response)
                    logger.warning(
                        "[{}] Rate limited, retry_after={}s, attempt={}/{}",
                        provider,
                        retry_after,
                        attempt,
                        self._max_retries,
                    )
                    if attempt < self._max_retries:
                        backoff = min(
                            self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
                            self.RETRY_BACKOFF_MAX,
                        )
                        time.sleep(backoff)
                        continue
                    raise RateLimitError(provider, retry_after=retry_after)

                if response.status_code >= 500:
                    logger.error(
                        "[{}] Server error {}, attempt={}/{}",
                        provider,
                        response.status_code,
                        attempt,
                        self._max_retries,
                    )
                    if attempt < self._max_retries:
                        backoff = min(
                            self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
                            self.RETRY_BACKOFF_MAX,
                        )
                        time.sleep(backoff)
                        continue
                    raise ModelUnavailableError(
                        provider, f"HTTP {response.status_code}"
                    )

                if response.status_code >= 400:
                    error_body = response.text[:500]
                    raise ModelClientError(
                        provider,
                        f"HTTP {response.status_code}: {error_body}",
                        status_code=response.status_code,
                    )

                return self._parse_response(response, resolved_model, latency_ms)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.error(
                    "[{}] Connection error: {}, attempt={}/{}",
                    provider,
                    exc,
                    attempt,
                    self._max_retries,
                )
                if attempt < self._max_retries:
                    backoff = min(
                        self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
                        self.RETRY_BACKOFF_MAX,
                    )
                    time.sleep(backoff)
                    continue
                raise ModelUnavailableError(provider, str(exc)) from exc

        raise ModelClientError(provider, "Max retries exceeded without specific error")

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

        Streaming does not use retry logic (single attempt).

        Args:
            Same as complete(), with stream=True implied.

        Returns:
            Iterator of response chunk dicts.

        Raises:
            RateLimitError: When rate limit exceeded.
            ModelUnavailableError: When API unreachable.
            ModelClientError: For other errors.
        """
        provider = self._get_provider_name()
        resolved_model = model_name or self._get_default_model()

        payload = self._build_payload(
            prompt, resolved_model, max_tokens, temperature, stream=True
        )
        headers = self._build_headers(provider, branch_id)
        payload, headers = self._apply_provider_specific_params(payload, headers)

        api_base = self._credential_provider.get_api_base(provider)
        url = f"{api_base}/chat/completions"

        try:
            with self._client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                if response.status_code == 429:
                    raise RateLimitError(provider)
                if response.status_code >= 500:
                    raise ModelUnavailableError(
                        provider, f"HTTP {response.status_code}"
                    )
                if response.status_code >= 400:
                    error_body = response.text[:500]
                    raise ModelClientError(
                        provider,
                        f"HTTP {response.status_code}: {error_body}",
                        status_code=response.status_code,
                    )

                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = chunk.get("choices", [{}])[0].get(
                            "finish_reason"
                        )
                        if content or finish_reason:
                            yield {
                                "content": content,
                                "model_name": chunk.get("model", resolved_model),
                                "finish_reason": finish_reason,
                            }
                    except json.JSONDecodeError:
                        logger.warning(
                            "[{}] Failed to parse streaming chunk: {}",
                            provider,
                            data[:200],
                        )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ModelUnavailableError(provider, str(exc)) from exc

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata for this provider.

        Returns:
            Dictionary with provider, default_model, and capabilities.
        """
        return {
            "provider": self._get_provider_name(),
            "default_model": self._get_default_model(),
            "max_context_tokens": 128000,
            "supports_streaming": True,
            "pricing": {},
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD. Subclasses should override with actual pricing.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost (0.0 for base class, subclasses override).
        """
        return 0.0

    def health_check(self) -> bool:
        """Check if the API endpoint is reachable.

        Returns:
            True if a lightweight request succeeds within timeout.
        """
        provider = self._get_provider_name()
        try:
            api_base = self._credential_provider.get_api_base(provider)
            headers = self._build_headers(provider, branch_id="main")
            response = self._client.get(
                f"{api_base}/models", headers=headers, timeout=5.0
            )
            return response.status_code < 500
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("[{}] Health check failed: {}", provider, exc)
            return False

    def _build_payload(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> Dict[str, Any]:
        """Build the OpenAI-compatible request payload.

        Args:
            prompt: User prompt text.
            model: Model identifier.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.
            stream: Whether to stream the response.

        Returns:
            Request payload dictionary.
        """
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

    def _build_headers(self, provider: str, branch_id: str) -> Dict[str, str]:
        """Build request headers with authentication.

        Args:
            provider: Provider identifier.
            branch_id: Branch identifier for credential lookup.

        Returns:
            Headers dictionary with Authorization and provider-specific extras.
        """
        api_key = self._credential_provider.get_api_key(provider, branch_id)
        base_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        extra_headers = self._credential_provider.get_extra_headers(provider)
        return {**base_headers, **extra_headers}

    def _parse_response(
        self,
        response: httpx.Response,
        model_name: str,
        latency_ms: float,
    ) -> Dict[str, Any]:
        """Parse a non-streaming API response.

        Args:
            response: HTTP response object.
            model_name: Expected model name.
            latency_ms: Measured latency.

        Returns:
            Parsed response dictionary.
        """
        body = response.json()
        choice = body.get("choices", [{}])[0]
        usage = body.get("usage", {})

        return {
            "content": choice.get("message", {}).get("content", ""),
            "model_name": body.get("model", model_name),
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "finish_reason": choice.get("finish_reason", "stop"),
            "latency_ms": latency_ms,
        }

    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        """Parse Retry-After header from a 429 response.

        Args:
            response: HTTP response with 429 status.

        Returns:
            Retry-after seconds, or None if not specified.
        """
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                return None
        return None
