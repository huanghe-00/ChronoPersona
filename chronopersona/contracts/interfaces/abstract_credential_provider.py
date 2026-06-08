"""Interface for credential providers managing LLM API keys and configuration."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class CredentialNotFoundError(Exception):
    """Raised when credentials are not found for a provider.

    Attributes:
        provider: The provider identifier that was not found.
        detail: Additional detail about the failure.
    """

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"Credential not found for provider '{provider}': {detail}")


class ICredentialProvider(ABC):
    """Abstract interface for providing API credentials for LLM providers.

    Implementations must support credential isolation by branch_id,
    ensuring different branches do not share or leak credentials.
    Per AIDER.md section 2, all data operations must explicitly pass
    branch_id; default global branches are prohibited.

    Attributes:
        None
    """

    @abstractmethod
    def get_api_key(self, provider: str, branch_id: str) -> str:
        """Retrieve the API key for a specific provider and branch.

        Args:
            provider: Model provider identifier (e.g., "kimi", "deepseek", "glm").
            branch_id: Explicit branch identifier for credential isolation.
                Must not be empty or use a global default.

        Returns:
            The API key string for the specified provider.

        Raises:
            CredentialNotFoundError: If no credential is configured for the
                given provider and branch.
        """
        ...

    @abstractmethod
    def get_api_base(self, provider: str) -> str:
        """Retrieve the API base URL for a specific provider.

        Args:
            provider: Model provider identifier.

        Returns:
            The base URL string for API calls.

        Raises:
            CredentialNotFoundError: If no base URL is configured.
        """
        ...

    @abstractmethod
    def get_extra_headers(self, provider: str) -> Dict[str, str]:
        """Retrieve extra HTTP headers required by a provider.

        Some providers require custom headers (e.g., Kimi requires
        User-Agent: KimiCLI/1.3).

        Args:
            provider: Model provider identifier.

        Returns:
            Dictionary of extra headers to include in API requests.
        """
        ...

    @abstractmethod
    def get_extra_body(self, provider: str) -> Dict[str, Any]:
        """Retrieve extra body parameters for a provider's API requests.

        Some providers require additional JSON body fields (e.g., DeepSeek's
        thinking mode configuration).

        Args:
            provider: Model provider identifier.

        Returns:
            Dictionary of extra body parameters.
        """
        ...

    @abstractmethod
    def is_available(self, provider: str) -> bool:
        """Check if credentials are available and valid for a provider.

        Args:
            provider: Model provider identifier.

        Returns:
            True if the provider has a non-empty API key configured.
        """
        ...

    @abstractmethod
    def refresh(self, provider: str) -> None:
        """Refresh or rotate credentials for a provider.

        Useful for key rotation or re-reading from environment variables
        after external updates.

        Args:
            provider: Model provider identifier.

        Raises:
            CredentialNotFoundError: If the provider is not configured.
        """
        ...
