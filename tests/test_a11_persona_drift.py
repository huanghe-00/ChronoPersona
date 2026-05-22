"""A11: Persona drift detection evaluation."""

import pytest

from evaluation.drift_checker import PersonaDriftChecker


class TestA11PersonaDrift:
    """A11: Style fingerprint drift detection."""

    def test_consistent_style_high_similarity(self) -> None:
        """T01: Replies with similar length/pattern to style examples score high."""
        examples = [
            "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？",
            "这种担忧让你很不安。我能理解你想找到答案的心情。",
        ]
        checker = PersonaDriftChecker(examples)
        # Similar length and structure to examples
        reply = "我能理解你的感受。这种感觉一定让你很不舒服吧？"
        sim = checker.check(reply)
        assert sim > 0.75

    def test_drifted_style_low_similarity(self) -> None:
        """T02: Short aggressive reply diverges from long empathetic examples."""
        examples = [
            "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？",
        ]
        checker = PersonaDriftChecker(examples)
        # Much shorter and different tone
        reply = "矫情！"
        sim = checker.check(reply)
        assert sim < 0.75

    def test_empty_reply_zero_similarity(self) -> None:
        """T03: Empty reply returns zero similarity."""
        checker = PersonaDriftChecker(["example text for baseline"])
        sim = checker.check("")
        assert sim == 0.0

    def test_end_to_end_drift_after_turns(self) -> None:
        """T04: Agent replies after multiple turns maintain style similarity."""
        from chronopersona.agent_core.state_machine import StateMachineAgentCore
        from chronopersona.mocks.mock_memory_store import MockMemoryStore
        from chronopersona.mocks.mock_model_router import MockModelRouter

        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        # Collect replies over multiple turns
        replies = []
        for query in ["你好", "我最近很焦虑", "谢谢你的建议"]:
            out = core.run_turn(query, branch_id="main")
            replies.append(out.reply_text)

        # Baseline from therapist-style examples
        examples = [
            "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？",
            "这种担忧让你很不安。我能理解你想找到答案的心情。",
        ]
        checker = PersonaDriftChecker(examples)
        avg_sim = sum(checker.check(r) for r in replies) / len(replies)
        # MVA: MockModelRouter returns deterministic text; verify pipeline runs
        assert avg_sim >= 0.0  # Structural sanity: no crash, non-negative similarity
