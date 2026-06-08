"""Authentication data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuthContext:
    """Authenticated session context with branch-level RBAC."""

    tenant_id: str
    role: str
    allowed_branches: List[str]
    api_key_prefix: str
    metadata: Dict[str, Any] = field(default_factory=dict)
