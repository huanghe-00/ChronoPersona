"""Authentication middleware for v1.1.0 production baseline.

MVA: API Key + Branch-level RBAC skeleton.
"""

import os
from typing import Dict, List, Optional

from loguru import logger


class AuthMiddleware:
    """Simple API Key and Branch RBAC middleware."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.environ.get("MVA_API_KEY", "")
        # MVA: hardcoded role map for single-tenant demo
        self._roles: Dict[str, Dict[str, List[str]]] = {
            "default": {
                "readable_branches": ["main", "therapist", "rpg-hero"],
                "writable_branches": ["main", "therapist", "rpg-hero"],
            },
        }

    def authenticate(self, auth_header: str) -> bool:
        """Validate Bearer token."""
        if not self._api_key:
            logger.warning("MVA_API_KEY not set; allowing all requests")
            return True
        expected = f"Bearer {self._api_key}"
        return auth_header == expected

    def authorize_branch(self, token_scope: str, branch_id: str, operation: str) -> bool:
        """Check if scope has permission for branch operation.

        Args:
            token_scope: Identifies the tenant/role (MVA: single "default").
            branch_id: Target branch.
            operation: "read" or "write".

        Returns:
            True if authorized.
        """
        role = self._roles.get(token_scope, self._roles["default"])
        if operation == "read":
            allowed = role.get("readable_branches", [])
        elif operation == "write":
            allowed = role.get("writable_branches", [])
        else:
            return False

        # MVA: "main" is universal; other branches require explicit permission
        if branch_id == "main":
            return True
        return branch_id in allowed
"""Lightweight auth middleware for MVA single-tenant mode."""

import os
from typing import Dict, Optional

from loguru import logger

from chronopersona.contracts.interfaces.abstract_auth_middleware import (
    AuthenticationError,
    IAuthMiddleware,
)
from chronopersona.contracts.schemas.auth import AuthContext


class AuthMiddleware(IAuthMiddleware):
    """MVA auth middleware backed by environment variable master key.

    API Key is loaded from CHRONOPERSONA_API_KEY env var at startup.
    Multi-tenant registry is reserved at interface level; MVA uses a
    single default tenant with admin role.
    """

    def __init__(self, master_key: Optional[str] = None) -> None:
        self._master_key = master_key or os.getenv("CHRONOPERSONA_API_KEY", "")
        self._tenant_registry: Dict[str, AuthContext] = {}

        if self._master_key:
            self._tenant_registry[self._master_key] = AuthContext(
                tenant_id="default",
                role="admin",
                allowed_branches=["main", "therapist", "rpg-hero"],
                api_key_prefix=self._master_key[:8],
            )
            logger.info("AuthMiddleware initialized with default tenant")
        else:
            logger.warning(
                "CHRONOPERSONA_API_KEY not set; all requests will be rejected"
            )

    def authenticate(self, token: str) -> AuthContext:
        """Validate bearer token against in-memory registry."""
        if not token:
            raise AuthenticationError("Missing bearer token")
        ctx = self._tenant_registry.get(token)
        if not ctx:
            raise AuthenticationError("Invalid API key")
        logger.debug("Authenticated tenant: {}", ctx.tenant_id)
        return ctx

    def check_branch_access(
        self,
        auth_context: AuthContext,
        branch_id: str,
        access_type: str = "read",
    ) -> bool:
        """Branch-level RBAC check."""
        if auth_context.role == "admin":
            return True
        if branch_id not in auth_context.allowed_branches:
            logger.warning(
                "Tenant {} denied access to branch {}",
                auth_context.tenant_id,
                branch_id,
            )
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
        """Restrict Persona Anchor reads to admin or branch writers."""
        if auth_context.role == "admin":
            return True
        return (
            branch_id in auth_context.allowed_branches
            and auth_context.role == "writer"
        )
