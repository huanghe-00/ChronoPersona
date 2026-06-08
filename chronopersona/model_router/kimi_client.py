"""Kimi (Moonshot AI) API client."""

from typing import Any, Dict, Tuple

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)
from chronopersona.model_router.base_http_client import BaseHttpClient


class KimiClient(BaseHttpClient):
    """Client for Kimi (Moonshot AI) API.

    Kimi uses OpenAI-compatible API format with custom headers
    (User-Agent: KimiCLI/1.3) and supports up to 262K context.
    Used for T4 (memory reflection), T6 (conflict resolution),
    and as fallback for T2/T3/T5/T7 per requirements 7.1.

    Attributes:
        Inherits from BaseHttpClient.
    """

    # Kimi pricing (approximate, per 1M tokens)
    PRICING_INPUT = 12.0  # USD per 1M input tokens
    PRICING_OUTPUT = 48.0  # USD per 1M output tokens

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        timeout: float = 60.0,  # Kimi may need longer for 262K context
        max_retries: int = 3,
    ) -> None:
        """Initialize Kimi client.

        Args:
            credential_provider: Provider for Kimi API credentials.
            timeout: Request timeout (longer default for 262K context).
            max_retries: Maximum retry attempts.
        """
        super().__init__(credential_provider, timeout, max_retries)
        logger.info("KimiClient initialized with timeout={}s", timeout)

    def _get_provider_name(self) -> str:
        """Return Kimi provider identifier."""
        return "kimi"

    def _get_default_model(self) -> str:
        """Return default Kimi model name."""
        return "kimi-for-coding"

    def _apply_provider_specific_params(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Apply Kimi-specific parameters.

        Adds User-Agent header required by Kimi API.

        Args:
            payload: Request payload.
            headers: Request headers.

        Returns:
            Modified (payload, headers) tuple.
        """
        headers["User-Agent"] = "KimiCLI/1.3"
        return payload, headers

    def get_model_info(self) -> Dict[str, Any]:
        """Return Kimi model metadata.

        Returns:
            Dictionary with Kimi-specific model info including
            262K context window and pricing.
        """
        return {
            "provider": "kimi",
            "default_model": "kimi-for-coding",
            "max_context_tokens": 262144,
            "supports_streaming": True,
            "pricing": {
                "input_per_1m": self.PRICING_INPUT,
                "output_per_1m": self.PRICING_OUTPUT,
            },
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Kimi API call.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        input_cost = (input_tokens / 1_000_000) * self.PRICING_INPUT
        output_cost = (output_tokens / 1_000_000) * self.PRICING_OUTPUT
        return input_cost + output_cost
