"""VLNAgent: Vision-Language Navigation agent for Chinese commands.

Parses Chinese natural language navigation commands into
SemanticNavigationGoal objects and delegates execution to an
AbstractEmbodiedAdapter.
"""

from __future__ import annotations

import re
from typing import Optional, Set

from loguru import logger

from chronopersona.contracts.interfaces import AbstractEmbodiedAdapter
from chronopersona.contracts.schemas import (
    NavigationResult,
    SemanticNavigationGoal,
)

# Known navigation targets (Chinese object names)
_NAV_TARGETS: Set[str] = {
    "沙发",
    "床",
    "桌子",
    "椅子",
    "冰箱",
    "茶几",
}

# Navigation command patterns (Chinese)
_NAV_PATTERNS = [
    # Commands with location suffix (e.g., "请到沙发旁边", "去床那边")
    re.compile(
        r"(?:请到|去|走到|导航到)\s*(.+?)\s*"
        r"(?:旁边|那边|这里|那里|附近|边上)"
    ),
    # Direct find/seek commands (e.g., "找到桌子")
    re.compile(r"(?:找到|寻找)\s*(.+)$"),
    # Direct go-to commands without suffix (e.g., "去飞船", "请到沙发")
    re.compile(r"(?:请到|去|走到|导航到)\s*(.+)$"),
]


class VLNAgent:
    """Vision-Language Navigation agent for Chinese commands.

    Bridges natural language input with the
    AbstractEmbodiedAdapter.navigate_to_object() contract.

    Attributes:
        adapter: Optional embodied adapter for navigation execution.
    """

    def __init__(self, adapter: Optional[AbstractEmbodiedAdapter] = None) -> None:
        self._adapter = adapter

    def parse_command(self, text: str) -> Optional[SemanticNavigationGoal]:
        """Parse a Chinese navigation command into a SemanticNavigationGoal.

        Args:
            text: Natural language command in Chinese.

        Returns:
            SemanticNavigationGoal if the command is a valid navigation
            request with a known target object; None otherwise.
        """
        if not text or not text.strip():
            return None

        for pattern in _NAV_PATTERNS:
            match = pattern.search(text)
            if match:
                raw_target = match.group(1).strip()
                if raw_target in _NAV_TARGETS:
                    return SemanticNavigationGoal(target_object=raw_target)
                # Navigation pattern matched but target is unknown
                return None

        # No navigation pattern matched
        return None

    def execute_navigation(
        self, command: str, branch_id: str
    ) -> NavigationResult:
        """Execute a navigation command via the embodied adapter.

        Args:
            command: Natural language navigation command.
            branch_id: Branch identifier for memory isolation. Must not be empty.

        Returns:
            NavigationResult from the adapter.

        Raises:
            ValueError: If branch_id is empty.
            RuntimeError: If no adapter is configured.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        if self._adapter is None:
            raise RuntimeError("No embodied adapter configured")

        goal = self.parse_command(command)
        if goal is None:
            return NavigationResult(success=False, steps_taken=0)

        result = self._adapter.navigate_to_object(goal)
        logger.info(
            "VLNAgent: nav command='{}' target='{}' success={} steps={}",
            command,
            goal.target_object,
            result.success,
            result.steps_taken,
        )
        return result

    def generate_follow_up(self, result: NavigationResult) -> str:
        """Generate a follow-up question based on navigation result.

        Args:
            result: NavigationResult from a completed navigation episode.

        Returns:
            Chinese follow-up text prompting further interaction.
        """
        if result.success:
            return "还需要我做什么吗？"
        if result.steps_taken > 30:
            return "未能到达目标，是否要重新尝试？"
        return "导航未能完成，请重新指定目标。"
