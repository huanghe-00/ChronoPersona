"""Unit tests for IntentNode intent classification."""

import pytest

from chronopersona.agent_core.intent_node import Intent, IntentNode


class TestIntentNode:
    """MVA intent classification tests."""

    def test_greeting_intent(self) -> None:
        """T01: Greeting keywords classify as GREETING."""
        node = IntentNode()
        assert node.classify("你好") == Intent.GREETING
        assert node.classify("hello") == Intent.GREETING
        assert node.classify("早上好") == Intent.GREETING

    def test_navigation_intent_variations(self) -> None:
        """T02: Various Chinese navigation phrasing classify as NAVIGATION."""
        node = IntentNode()
        nav_phrases = [
            "到沙发旁边",
            "去厨房那里",
            "导航到床附近",
            "请帮我到桌子旁边",
            "靠近书架",
            "走向冰箱",
        ]
        for phrase in nav_phrases:
            result = node.classify(phrase)
            assert result == Intent.NAVIGATION, f"Expected NAVIGATION for: {phrase}"

    def test_memory_query_intent(self) -> None:
        """T03: Memory-related keywords classify as MEMORY_QUERY."""
        node = IntentNode()
        assert node.classify("记得上次说什么") == Intent.MEMORY_QUERY
        assert node.classify("recall previous context") == Intent.MEMORY_QUERY
        assert node.classify("想起那个方案") == Intent.MEMORY_QUERY

    def test_general_fallback(self) -> None:
        """T04: Unmatched input falls back to GENERAL."""
        node = IntentNode()
        assert node.classify("今天天气不错") == Intent.GENERAL
        assert node.classify("随便聊聊") == Intent.GENERAL
        assert node.classify("12345") == Intent.GENERAL
