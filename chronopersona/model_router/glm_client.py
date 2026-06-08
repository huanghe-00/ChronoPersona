"""GLM (Zhipu AI) API client."""

from typing import Any, Dict, Tuple

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)
from chronopersona.model_router.base_http_client import BaseHttpClient


class GLMClient(BaseHttpClient):
    """Client for GLM (Zhipu AI) API.

    GLM uses OpenAI-compatible API format via a proxy endpoint.
    Supports GLM-5.1 model for editing and weak model tasks.
    Per .aider.model.settings.yml, GLM serves as the weak_model
    and editor_model in the Kimi+GLM architecture.

    Attributes:
        Inherits from BaseHttpClient.
    """

    # GLM pricing (approximate, per 1M tokens)
    PRICING_INPUT = 5.0  # USD per 1M input tokens
    PRICING_OUTPUT = 10.0  # USD per 1M output tokens

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize GLM client.

        Args:
            credential_provider: Provider for GLM API credentials.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
        """
        super().__init__(credential_provider, timeout, max_retries)
        logger.info("GLMClient initialized with timeout={}s", timeout)

    def _get_provider_name(self) -> str:
        """Return GLM provider identifier."""
        return "glm"

    def _get_default_model(self) -> str:
        """Return default GLM model name."""
        return "GLM-5.1"

    def _apply_provider_specific_params(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Apply GLM-specific parameters.

        GLM uses standard OpenAI format with no extra params needed.
        Per .aider.model.settings.yml, GLM-5.1 has native Agentic
        engineering capability without additional configuration.

        Args:
            payload: Request payload.
            headers: Request headers.

        Returns:
            Unmodified (payload, headers) tuple.
        """
        return payload, headers

    def get_model_info(self) -> Dict[str, Any]:
        """Return GLM model metadata.

        Returns:
            Dictionary with GLM-specific model info.
        """
        return {
            "provider": "glm",
            "default_model": "GLM-5.1",
            "max_context_tokens": 128000,
            "supports_streaming": True,
            "pricing": {
                "input_per_1m": self.PRICING_INPUT,
                "output_per_1m": self.PRICING_OUTPUT,
            },
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for GLM API call.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        input_cost = (input_tokens / 1_000_000) * self.PRICING_INPUT
        output_cost = (output_tokens / 1_000_000) * self.PRICING_OUTPUT
        return input_cost + output_cost
