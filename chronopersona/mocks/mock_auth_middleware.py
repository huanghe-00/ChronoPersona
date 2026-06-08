"""Mock authentication middleware for testing."""

from chronopersona.contracts.interfaces.abstract_auth_middleware import (
    AuthenticationError,
    IAuthMiddleware,
)
from chronopersona.contracts.schemas.auth import AuthContext


class MockAuthMiddleware(IAuthMiddleware):
    """In-memory mock auth middleware with configurable tenants."""

    def __init__(self) -> None:
        self._contexts: dict[str, AuthContext] = {}

    def add_tenant(
        self,
        token: str,
        tenant_id: str,
        role: str,
        allowed_branches: list[str],
    ) -> None:
        """Register a tenant for testing."""
        self._contexts[token] = AuthContext(
            tenant_id=tenant_id,
            role=role,
            allowed_branches=allowed_branches,
            api_key_prefix=token[:8],
        )

    def authenticate(self, token: str) -> AuthContext:
        if token not in self._contexts:
            raise AuthenticationError("Invalid token")
        return self._contexts[token]

    def check_branch_access(
        self,
        auth_context: AuthContext,
        branch_id: str,
        access_type: str = "read",
    ) -> bool:
        if auth_context.role == "admin":
            return True
        if branch_id not in auth_context.allowed_branches:
            return False
        if access_type == "write" and auth_context.role == "reader":
            return False
        return True

    def check_persona_anchor_access(
        self,
        auth_context: AuthContext,
        persona_id: str,
        branch_id: str,
    ) -> bool:
        if auth_context.role == "admin":
            return True
        return (
            branch_id in auth_context.allowed_branches
            and auth_context.role == "writer"
        )
