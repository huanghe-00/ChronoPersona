"""Tests for authentication middleware."""

import pytest

from chronopersona.auth.middleware import AuthMiddleware
from chronopersona.contracts.interfaces.abstract_auth_middleware import (
    AuthenticationError,
)
from chronopersona.mocks.mock_auth_middleware import MockAuthMiddleware


class TestMockAuthMiddleware:
    """T1-T4: Mock auth middleware tests."""

    def test_authenticate_valid_token(self) -> None:
        """Valid token returns correct AuthContext."""
        auth = MockAuthMiddleware()
        auth.add_tenant("sk-test-123", "t1", "admin", ["main", "therapist"])

        ctx = auth.authenticate("sk-test-123")
        assert ctx.tenant_id == "t1"
        assert ctx.role == "admin"
        assert "main" in ctx.allowed_branches

    def test_authenticate_invalid_token_raises(self) -> None:
        """Invalid token raises AuthenticationError."""
        auth = MockAuthMiddleware()
        with pytest.raises(AuthenticationError):
            auth.authenticate("invalid-token")

    def test_branch_access_denied_for_unauthorized(self) -> None:
        """Reader cannot access branches outside allowed list."""
        auth = MockAuthMiddleware()
        auth.add_tenant("sk-reader", "t2", "reader", ["main"])

        ctx = auth.authenticate("sk-reader")
        assert auth.check_branch_access(ctx, "main", "read") is True
        assert auth.check_branch_access(ctx, "therapist", "read") is False

    def test_persona_anchor_access_control(self) -> None:
        """Persona Anchor read restricted to admin or branch writer."""
        auth = MockAuthMiddleware()
        auth.add_tenant("sk-writer", "t3", "writer", ["therapist"])
        auth.add_tenant("sk-reader", "t4", "reader", ["therapist"])

        writer_ctx = auth.authenticate("sk-writer")
        reader_ctx = auth.authenticate("sk-reader")

        assert (
            auth.check_persona_anchor_access(writer_ctx, "therapist", "therapist")
            is True
        )
        assert (
            auth.check_persona_anchor_access(reader_ctx, "therapist", "therapist")
            is False
        )


class TestAuthMiddlewareReal:
    """T5-T6: Real AuthMiddleware with env key."""

    def test_missing_master_key_rejects_all(self, monkeypatch) -> None:
        """Without CHRONOPERSONA_API_KEY, all authentication fails."""
        monkeypatch.delenv("CHRONOPERSONA_API_KEY", raising=False)
        auth = AuthMiddleware(master_key="")

        with pytest.raises(AuthenticationError):
            auth.authenticate("any-token")

    def test_master_key_allows_admin(self, monkeypatch) -> None:
        """Master key yields admin context with default branches."""
        monkeypatch.setenv("CHRONOPERSONA_API_KEY", "sk-master-abc")
        auth = AuthMiddleware()

        ctx = auth.authenticate("sk-master-abc")
        assert ctx.role == "admin"
        assert auth.check_branch_access(ctx, "main", "write") is True
