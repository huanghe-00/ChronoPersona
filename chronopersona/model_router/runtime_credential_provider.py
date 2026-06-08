"""Runtime credential provider reading from environment variables and config."""

import os
from typing import Any, Dict, Optional

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    CredentialNotFoundError,
    ICredentialProvider,
)

# Default API base URLs for each provider
_DEFAULT_API_BASES: Dict[str, str] = {
    "kimi": "https://api.kimi.com/coding/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "glm": "http://113.46.219.251:8080/v1",
}

# Environment variable mapping for API keys
_ENV_KEY_MAP: Dict[str, str] = {
    "kimi": "KIMI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "glm": "OPENAI_API_KEY",  # GLM uses OpenAI-compatible env var
}

# Provider-specific extra headers
_DEFAULT_EXTRA_HEADERS: Dict[str, Dict[str, str]] = {
    "kimi": {"User-Agent": "KimiCLI/1.3"},
    "deepseek": {},
    "glm": {},
}

# Provider-specific extra body parameters
_DEFAULT_EXTRA_BODY: Dict[str, Dict[str, Any]] = {
    "kimi": {},
    "deepseek": {},
    "glm": {},
}


class RuntimeCredentialProvider(ICredentialProvider):
    """Credential provider that reads API keys from environment variables
    and configuration dictionaries.

    Supports runtime refresh to pick up environment variable changes,
    and per-branch credential isolation via config overrides. Priority
    order: config_override > environment variable > default mapping.

    Attributes:
        _config_overrides: Per-provider config overrides loaded from YAML.
        _cache: In-memory cache of resolved credentials.
    """

    def __init__(
        self,
        config_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Initialize the credential provider.

        Args:
            config_overrides: Optional per-provider config overrides,
                typically loaded from .aider.model.settings.yml.
                Structure: {"kimi": {"api_key": "...", "api_base": "..."}, ...}
        """
        self._config_overrides: Dict[str, Dict[str, Any]] = config_overrides or {}
        self._cache: Dict[str, Optional[str]] = {}
        logger.info(
            "RuntimeCredentialProvider initialized with {} overrides",
            len(self._config_overrides),
        )

    def get_api_key(self, provider: str, branch_id: str) -> str:
        """Retrieve API key from environment variable or config override.

        Priority: config_override > environment variable.

        Args:
            provider: Model provider identifier.
            branch_id: Explicit branch identifier (used for logging,
                not key isolation in this implementation).

        Returns:
            API key string.

        Raises:
            CredentialNotFoundError: If no key is found.
        """
        # Try config override first
        override_key = self._config_overrides.get(provider, {}).get("api_key")
        if override_key:
            logger.debug("Using config override key for provider {}", provider)
            return override_key

        # Fallback to environment variable
        env_var = _ENV_KEY_MAP.get(provider)
        if env_var:
            env_key = os.environ.get(env_var, "")
            if env_key:
                logger.debug("Using env var {} for provider {}", env_var, provider)
                return env_key

        raise CredentialNotFoundError(
            provider,
            f"No API key found in config or env var {_ENV_KEY_MAP.get(provider, 'N/A')}",
        )

    def get_api_base(self, provider: str) -> str:
        """Retrieve API base URL.

        Priority: config_override > default mapping.

        Args:
            provider: Model provider identifier.

        Returns:
            Base URL string.

        Raises:
            CredentialNotFoundError: If provider is unknown.
        """
        override = self._config_overrides.get(provider, {}).get("api_base")
        if override:
            return override

        default = _DEFAULT_API_BASES.get(provider)
        if default:
            return default

        raise CredentialNotFoundError(provider, "No API base URL configured")

    def get_extra_headers(self, provider: str) -> Dict[str, str]:
        """Retrieve extra HTTP headers for a provider.

        Config overrides merge with (and take precedence over) defaults.

        Args:
            provider: Model provider identifier.

        Returns:
            Dictionary of extra headers.
        """
        base_headers = _DEFAULT_EXTRA_HEADERS.get(provider, {})
        override_headers = self._config_overrides.get(provider, {}).get(
            "extra_headers", {}
        )
        return {**base_headers, **override_headers}

    def get_extra_body(self, provider: str) -> Dict[str, Any]:
        """Retrieve extra body parameters for a provider.

        Config overrides merge with (and take precedence over) defaults.

        Args:
            provider: Model provider identifier.

        Returns:
            Dictionary of extra body params.
        """
        base_body = _DEFAULT_EXTRA_BODY.get(provider, {})
        override_body = self._config_overrides.get(provider, {}).get(
            "extra_body", {}
        )
        return {**base_body, **override_body}

    def is_available(self, provider: str) -> bool:
        """Check if a provider has credentials configured.

        Args:
            provider: Model provider identifier.

        Returns:
            True if API key is non-empty.
        """
        try:
            key = self.get_api_key(provider, branch_id="main")
            return bool(key)
        except CredentialNotFoundError:
            return False

    def refresh(self, provider: str) -> None:
        """Refresh cached credentials by clearing the cache entry.

        Re-reading from environment variables happens automatically on
        next get_api_key() call since env vars are always read fresh.

        Args:
            provider: Model provider identifier.

        Raises:
            CredentialNotFoundError: If provider is not in known providers.
        """
        if provider not in _DEFAULT_API_BASES and provider not in self._config_overrides:
            raise CredentialNotFoundError(provider, "Unknown provider")

        self._cache.pop(provider, None)
        logger.info("Credentials refreshed for provider {}", provider)
