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
