"""DeepSeek API client with thinking mode support."""

from typing import Any, Dict, Optional, Tuple

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)
from chronopersona.model_router.base_http_client import BaseHttpClient


class DeepSeekClient(BaseHttpClient):
    """Client for DeepSeek API.

    DeepSeek uses OpenAI-compatible API format with optional
    thinking mode (reasoning_effort parameter) for complex tasks.
    Two instances are typically created: one with thinking disabled
    (for T0-T3/T5/T7 flash tasks) and one with thinking enabled
    (for T4/T5/T6/T7 pro tasks).

    Attributes:
        Inherits from BaseHttpClient.
        _thinking_mode: Whether thinking mode is enabled.
        _reasoning_effort: Reasoning effort level when thinking is enabled.
    """

    # DeepSeek pricing (approximate, per 1M tokens)
    PRICING_INPUT_CACHE = 0.1  # Cached input tokens
    PRICING_INPUT = 1.0  # Non-cached input tokens
    PRICING_OUTPUT = 2.0  # Output tokens (V4-pro)
    PRICING_OUTPUT_FLASH = 0.3  # Output tokens (V4-flash)

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        timeout: float = 30.0,
        max_retries: int = 3,
        thinking_mode: bool = False,
        reasoning_effort: Optional[str] = None,
    ) -> None:
        """Initialize DeepSeek client.

        Args:
            credential_provider: Provider for DeepSeek API credentials.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            thinking_mode: Whether to enable thinking/reasoning mode.
            reasoning_effort: Effort level ("low", "medium", "max")
                when thinking is enabled.
        """
        super().__init__(credential_provider, timeout, max_retries)
        self._thinking_mode = thinking_mode
        self._reasoning_effort = reasoning_effort
        logger.info(
            "DeepSeekClient initialized, thinking_mode={}, reasoning_effort={}",
            thinking_mode,
            reasoning_effort,
        )

    def _get_provider_name(self) -> str:
        """Return DeepSeek provider identifier."""
        return "deepseek"

    def _get_default_model(self) -> str:
        """Return default DeepSeek model name."""
        return "deepseek-v4-pro"

    def _apply_provider_specific_params(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Apply DeepSeek-specific parameters.

        Adds thinking mode configuration to the request body.
        When thinking is enabled, adds reasoning_effort if specified.
        When disabled, explicitly sets thinking type to "disabled"
        to prevent default reasoning overhead.

        Args:
            payload: Request payload.
            headers: Request headers.

        Returns:
            Modified (payload, headers) tuple.
        """
        if self._thinking_mode:
            thinking_config: Dict[str, Any] = {"thinking": {"type": "enabled"}}
            if self._reasoning_effort:
                payload["reasoning_effort"] = self._reasoning_effort
            payload.update(thinking_config)
        else:
            payload.update({"thinking": {"type": "disabled"}})

        return payload, headers

    def get_model_info(self) -> Dict[str, Any]:
        """Return DeepSeek model metadata.

        Returns:
            Dictionary with DeepSeek-specific model info including
            thinking mode support and tiered pricing.
        """
        return {
            "provider": "deepseek",
            "default_model": "deepseek-v4-pro",
            "max_context_tokens": 128000,
            "supports_streaming": True,
            "supports_thinking": True,
            "pricing": {
                "input_cache_per_1m": self.PRICING_INPUT_CACHE,
                "input_per_1m": self.PRICING_INPUT,
                "output_pro_per_1m": self.PRICING_OUTPUT,
                "output_flash_per_1m": self.PRICING_OUTPUT_FLASH,
            },
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for DeepSeek API call.

        Uses pro-tier pricing. Flash-tier pricing is available in
        model_info for cost comparison.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD (using pro pricing).
        """
        input_cost = (input_tokens / 1_000_000) * self.PRICING_INPUT
        output_cost = (output_tokens / 1_000_000) * self.PRICING_OUTPUT
        return input_cost + output_cost
