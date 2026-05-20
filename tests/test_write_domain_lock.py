"""Tests for WriteDomainLock and MockWriteDomainLock."""

import pytest

from chronopersona.memory_system.write_domain_lock import WriteDomainLock
from chronopersona.mocks.mock_write_domain_lock import MockWriteDomainLock


class TestWriteDomainLock:
    """Tests for the real in-memory WriteDomainLock."""

    @pytest.fixture
    def lock(self) -> WriteDomainLock:
        return WriteDomainLock()

    def test_acquire_succeeds_when_not_locked(self, lock: WriteDomainLock) -> None:
        assert lock.acquire("L3", "entity-1", "main") is True

    def test_acquire_fails_when_already_locked(self, lock: WriteDomainLock) -> None:
        lock.acquire("L3", "entity-1", "main")
        assert lock.acquire("L3", "entity-1", "main") is False

    def test_different_entities_do_not_conflict(self, lock: WriteDomainLock) -> None:
        assert lock.acquire("L3", "entity-1", "main") is True
        assert lock.acquire("L3", "entity-2", "main") is True

    def test_different_branches_do_not_conflict(self, lock: WriteDomainLock) -> None:
        assert lock.acquire("L3", "entity-1", "main") is True
        assert lock.acquire("L3", "entity-1", "therapist") is True

    def test_release_allows_reacquire(self, lock: WriteDomainLock) -> None:
        lock.acquire("L3", "entity-1", "main")
        lock.release("L3", "entity-1", "main")
        assert lock.acquire("L3", "entity-1", "main") is True

    def test_is_locked_reflects_state(self, lock: WriteDomainLock) -> None:
        assert lock.is_locked("L3", "entity-1", "main") is False
        lock.acquire("L3", "entity-1", "main")
        assert lock.is_locked("L3", "entity-1", "main") is True
        lock.release("L3", "entity-1", "main")
        assert lock.is_locked("L3", "entity-1", "main") is False


class TestMockWriteDomainLock:
    """Tests for the MockWriteDomainLock."""

    @pytest.fixture
    def mock_lock(self) -> MockWriteDomainLock:
        return MockWriteDomainLock()

    def test_mock_always_acquires(self, mock_lock: MockWriteDomainLock) -> None:
        assert mock_lock.acquire("L3", "entity-1", "main") is True
        # Even a second acquire succeeds in the mock
        assert mock_lock.acquire("L3", "entity-1", "main") is True

    def test_mock_is_locked_after_acquire(self, mock_lock: MockWriteDomainLock) -> None:
        mock_lock.acquire("L3", "entity-1", "main")
        assert mock_lock.is_locked("L3", "entity-1", "main") is True

    def test_mock_release_clears_lock(self, mock_lock: MockWriteDomainLock) -> None:
        mock_lock.acquire("L3", "entity-1", "main")
        mock_lock.release("L3", "entity-1", "main")
        assert mock_lock.is_locked("L3", "entity-1", "main") is False

    def test_mock_different_layers_independent(self, mock_lock: MockWriteDomainLock) -> None:
        mock_lock.acquire("L0", "key-1", "main")
        assert mock_lock.is_locked("L0", "key-1", "main") is True
        assert mock_lock.is_locked("L3", "key-1", "main") is False
