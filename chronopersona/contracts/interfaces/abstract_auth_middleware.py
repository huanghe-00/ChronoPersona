"""Abstract authentication middleware with branch-level RBAC."""

from abc import ABC, abstractmethod

from chronopersona.contracts.schemas.auth import AuthContext


class AuthenticationError(Exception):
    """Raised when bearer token is invalid or missing."""


class AuthorizationError(Exception):
    """Raised when branch or persona access is denied."""


class IAuthMiddleware(ABC):
    """Abstract middleware for API authentication and RBAC.

    MVA stage operates in single-tenant single-key mode, but interface
    preserves multi-tenant extension points for production.
    """

    @abstractmethod
    def authenticate(self, token: str) -> AuthContext:
        """Validate bearer token and return auth context.

        Args:
            token: Bearer token from Authorization header or WebSocket
                query parameter.

        Returns:
            AuthContext with tenant_id, role, allowed_branches.

        Raises:
            AuthenticationError: If token is missing or invalid.
        """
        ...

    @abstractmethod
    def check_branch_access(
        self,
        auth_context: AuthContext,
        branch_id: str,
        access_type: str = "read",
    ) -> bool:
        """Check if auth context has access to branch.

        Args:
            auth_context: Authenticated context.
            branch_id: Target branch identifier.
            access_type: "read" or "write".

        Returns:
            True if access is permitted.
        """
        ...

    @abstractmethod
    def check_persona_anchor_access(
        self,
        auth_context: AuthContext,
        persona_id: str,
        branch_id: str,
    ) -> bool:
        """Check if auth context can read Persona Anchor.

        Per requirements 6.2.1, Persona Anchor is sensitive identity
        asset. Only admin or the branch's writer may read.

        Args:
            auth_context: Authenticated context.
            persona_id: Persona identifier.
            branch_id: Branch the persona belongs to.

        Returns:
            True if permitted.
        """
        ...
