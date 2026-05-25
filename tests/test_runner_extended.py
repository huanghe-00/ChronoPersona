"""Verify evaluation runner covers A7-A11 agent behavior metrics."""

import pytest

from evaluation.runner import EvaluationRunner


class TestEvaluationRunnerExtended:
    """A7-A11 scenario coverage validation."""

    def test_runner_includes_a7_emotion(self) -> None:
        """T01: A7 emotion consistency produces transition_accuracy metric."""
        runner = EvaluationRunner()
        result = runner._evaluate_a7_emotion_consistency()
        assert "transition_accuracy" in result
        assert result["transition_accuracy"] == 1.0

    def test_runner_includes_a8_embodied(self) -> None:
        """T02: A8 embodied injection produces injection_rate metric."""
        runner = EvaluationRunner()
        result = runner._evaluate_a8_embodied_injection()
        assert "injection_rate" in result
        assert result["injection_rate"] == 1.0

    def test_runner_includes_a9_cross_body(self) -> None:
        """T03: A9 cross-body produces consistency_rate metric."""
        runner = EvaluationRunner()
        result = runner._evaluate_a9_cross_body_consistency()
        assert "consistency_rate" in result
        assert result["consistency_rate"] == 1.0

    def test_runner_includes_a10_auditability(self) -> None:
        """T04: A10 action auditability produces reasoning_coverage metric."""
        runner = EvaluationRunner()
        result = runner._evaluate_a10_action_auditability()
        assert "reasoning_coverage" in result
        assert result["reasoning_coverage"] == 1.0

    def test_runner_includes_a11_drift(self) -> None:
        """T05: A11 persona drift produces drift_detection_rate metric."""
        runner = EvaluationRunner()
        result = runner._evaluate_a11_persona_drift()
        assert "drift_detection_rate" in result
        assert result["drift_detection_rate"] == 1.0
