"""API mode switch managing local vs cloud model routing."""

import time
from enum import Enum
from typing import Dict

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)


class APIMode(Enum):
    """API operation mode."""

    LOCAL = "local"  # Use local models (LM Studio / Qwen3.5)
    CLOUD = "cloud"  # Use cloud API providers
    HYBRID = "hybrid"  # Local for T0/T1, cloud for T2-T7


class ModeSwitchEvent:
    """Record of a mode switch event for audit logging.

    Attributes:
        from_mode: Previous API mode.
        to_mode: New API mode.
        reason: Reason for the switch.
        timestamp: Time of the switch (monotonic seconds).
    """

    def __init__(
        self,
        from_mode: APIMode,
        to_mode: APIMode,
        reason: str,
        timestamp: float,
    ) -> None:
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.reason = reason
        self.timestamp = timestamp


class APIModeSwitch:
    """Manages switching between local, cloud, and hybrid API modes.

    Tracks local model health and automatically switches to cloud fallback
    when local models are unavailable. Logs all mode transitions for audit.
    Per requirements 7.1, T0/T1 tasks prefer local Qwen3.5-9B, all others
    use cloud providers.

    Attributes:
        _current_mode: Current active API mode.
        _credential_provider: Credential provider for cloud API access.
        _local_health_status: Health status of local model endpoints.
        _switch_history: Log of mode switch events.
        _last_health_check: Timestamp of last health check.
    """

    # Task tiers that can use local models (per requirements 7.1)
    LOCAL_TASK_TIERS = {"T0", "T1"}

    # Health check interval in seconds
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        initial_mode: APIMode = APIMode.HYBRID,
        local_base_url: str = "http://localhost:1234/v1",
    ) -> None:
        """Initialize the API mode switch.

        Args:
            credential_provider: Provider for cloud API credentials.
            initial_mode: Starting API mode (default: HYBRID).
            local_base_url: Base URL for local LM Studio endpoint.
        """
        self._current_mode = initial_mode
        self._credential_provider = credential_provider
        self._local_base_url = local_base_url
        self._local_health_status: Dict[str, bool] = {"lm_studio": True}
        self._switch_history: list[ModeSwitchEvent] = []
        self._last_health_check: float = 0.0
        logger.info("APIModeSwitch initialized in {} mode", initial_mode.value)

    @property
    def current_mode(self) -> APIMode:
        """Get the current API mode."""
        return self._current_mode

    @property
    def switch_history(self) -> list[ModeSwitchEvent]:
        """Get the history of mode switch events (copy)."""
        return self._switch_history.copy()

    def get_mode_for_task(self, task_type: str) -> APIMode:
        """Determine the appropriate API mode for a task tier.

        In HYBRID mode, T0/T1 tasks use local models if healthy,
        all other tasks use cloud. In LOCAL mode, all tasks use
        local unless unhealthy. In CLOUD mode, all tasks use cloud.

        Args:
            task_type: Task tier identifier (T0-T7).

        Returns:
            The API mode to use for this task.
        """
        if self._current_mode == APIMode.LOCAL:
            if not self._local_health_status.get("lm_studio", False):
                logger.warning(
                    "Local mode active but local model unhealthy, "
                    "forcing cloud for task {}",
                    task_type,
                )
                return APIMode.CLOUD
            return APIMode.LOCAL

        if self._current_mode == APIMode.CLOUD:
            return APIMode.CLOUD

        # HYBRID mode: local for T0/T1, cloud for rest
        if (
            task_type in self.LOCAL_TASK_TIERS
            and self._local_health_status.get("lm_studio", False)
        ):
            return APIMode.LOCAL

        return APIMode.CLOUD

    def switch_mode(self, new_mode: APIMode, reason: str = "manual") -> None:
        """Switch to a new API mode.

        Args:
            new_mode: Target API mode.
            reason: Reason for the switch (logged for audit).
        """
        if new_mode == self._current_mode:
            logger.debug(
                "Mode switch requested but already in {} mode", new_mode.value
            )
            return

        old_mode = self._current_mode
        self._current_mode = new_mode
        event = ModeSwitchEvent(old_mode, new_mode, reason, time.time())
        self._switch_history.append(event)
        logger.info(
            "API mode switched: {} → {} (reason: {})",
            old_mode.value,
            new_mode.value,
            reason,
        )

    def update_local_health(self, endpoint: str, is_healthy: bool) -> None:
        """Update the health status of a local model endpoint.

        If local health drops in HYBRID mode, T0/T1 tasks automatically
        fall back to cloud. If local recovers, tasks resume local execution.

        Args:
            endpoint: Local endpoint identifier (e.g., "lm_studio").
            is_healthy: Whether the endpoint is currently healthy.
        """
        was_healthy = self._local_health_status.get(endpoint, False)
        self._local_health_status[endpoint] = is_healthy
        self._last_health_check = time.time()

        if was_healthy and not is_healthy and self._current_mode == APIMode.HYBRID:
            logger.warning(
                "Local endpoint {} became unhealthy, T0/T1 will fall back to cloud",
                endpoint,
            )

        if not was_healthy and is_healthy and self._current_mode == APIMode.HYBRID:
            logger.info(
                "Local endpoint {} recovered, T0/T1 will resume local execution",
                endpoint,
            )

    def check_local_health(self) -> bool:
        """Check if local model endpoints are healthy.

        Returns:
            True if at least one local endpoint is healthy.
        """
        return any(self._local_health_status.values())

    def should_run_health_check(self) -> bool:
        """Check if a periodic health check should be run.

        Returns:
            True if the health check interval has elapsed.
        """
        elapsed = time.time() - self._last_health_check
        return elapsed >= self.HEALTH_CHECK_INTERVAL

    def get_cloud_provider_for_task(self, task_type: str) -> str:
        """Determine which cloud provider to use for a task tier.

        Per requirements 7.1 routing table:
        - T0/T1: DeepSeek (fallback from local Qwen3.5)
        - T2/T3: DeepSeek
        - T4: Kimi
        - T5: DeepSeek-pro
        - T6: Kimi
        - T7: DeepSeek-pro

        Args:
            task_type: Task tier identifier (T0-T7).

        Returns:
            Provider identifier string.
        """
        task_provider_map: Dict[str, str] = {
            "T0": "deepseek",
            "T1": "deepseek",
            "T2": "deepseek",
            "T3": "deepseek",
            "T4": "kimi",
            "T5": "deepseek",
            "T6": "kimi",
            "T7": "deepseek",
        }
        return task_provider_map.get(task_type, "deepseek")
