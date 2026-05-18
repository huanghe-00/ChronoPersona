"""Intent classification node."""

from enum import Enum


class Intent(str, Enum):
    """Intent categories for lightweight keyword classification."""

    GREETING = "greeting"
    MEMORY_QUERY = "memory_query"
    GENERAL = "general"


class IntentNode:
    """Lightweight intent classifier based on keyword matching.

    TODO (W5): Replace with T0/T1 model router (Qwen3.5-9B / DS-V4-flash)
    for production-grade 8-class intent classification.
    """

    GREETING_KEYWORDS: set[str] = {"hello", "hi", "你好", "hey", "morning"}
    MEMORY_KEYWORDS: set[str] = {"remember", "recall", "memory", "记得", "回忆", "想起"}

    def classify(self, user_input: str) -> Intent:
        """Classify user input into an intent."""
        lowered = user_input.lower()
        if any(kw in lowered for kw in self.GREETING_KEYWORDS):
            return Intent.GREETING
        if any(kw in lowered for kw in self.MEMORY_KEYWORDS):
            return Intent.MEMORY_QUERY
        return Intent.GENERAL
