"""Evaluation runner for ChronoPersona adversarial test suite.

Orchestrates A1-A11 evaluation scenarios and produces quantitative reports.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder
from chronopersona.memory_system.l2_episodic.simple_store import SimpleEpisodicStore
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder
from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.contracts.schemas import EmotionLabel, EmotionState, EmbodiedState, RetrievedContext
from evaluation.drift_checker import PersonaDriftChecker
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class EvaluationRunner:
    """Run evaluation scenarios and collect metrics."""

    def __init__(self, output_dir: str = "reports") -> None:
        self._output_dir = output_dir
        os.makedirs(self._output_dir, exist_ok=True)
        self._store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        self._results: Dict[str, Any] = {}

    def run_all(self) -> Dict[str, Any]:
        """Execute all A1-A11 scenarios and return aggregated results."""
        logger.info("Starting evaluation run")
        scenarios = [
            ScenarioBuilder.build_a1_memory_recall(),
            ScenarioBuilder.build_a2_cross_session(),
            ScenarioBuilder.build_a3_persona_isolation(),
            ScenarioBuilder.build_a4_shared_main(),
            ScenarioBuilder.build_a5_multi_device_conflict(),
            ScenarioBuilder.build_a6_intent_graph_navigation(),
        ]
        for scenario in scenarios:
            self._run_scenario(scenario)

        # A7-A11: Agent Core behavior evaluation (non-retrieval metrics)
        self._results["A7"] = self._evaluate_a7_emotion_consistency()
        self._results["A8"] = self._evaluate_a8_embodied_injection()
        self._results["A9"] = self._evaluate_a9_cross_body_consistency()
        self._results["A10"] = self._evaluate_a10_action_auditability()
        self._results["A11"] = self._evaluate_a11_persona_drift()

        self._save_report()
        return self._results

    def _run_scenario(self, scenario) -> None:
        """Execute a single scenario and record metrics."""
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]
        scenario_metrics: Dict[str, Any] = {
            "scenario_id": scenario.scenario_id,
            "description": scenario.description,
            "queries": [],
        }
        for idx, query in enumerate(scenario.queries):
            ctx = store.retrieve(query, branch_id=scenario.branch_id, top_k=5)
            retrieved_ids = [m.id for m in ctx.episodic_memories]
            expected = [scenario.expected_memory_ids[idx]] if idx < len(scenario.expected_memory_ids) else []
            recall = Metrics.recall_at_k(retrieved_ids, expected, k=5)
            mrr = Metrics.mrr(retrieved_ids, expected)
            scenario_metrics["queries"].append(
                {
                    "query": query,
                    "recall@5": recall,
                    "mrr": mrr,
                    "retrieved_ids": retrieved_ids,
                    "expected_ids": expected,
                }
            )
        self._results[scenario.scenario_id] = scenario_metrics

    def _evaluate_a7_emotion_consistency(self) -> Dict[str, Any]:
        """A7: Emotional state transitions follow rules."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        # Negative input should trigger CONCERNED
        core.run_turn("我最近很焦虑", branch_id="main")
        es = core.get_emotion_state()
        transition_correct = es.current_state == EmotionLabel.CONCERNED
        
        # Neutral input should reset to NEUTRAL
        core.run_turn("今天天气不错", branch_id="main")
        es2 = core.get_emotion_state()
        reset_correct = es2.current_state == EmotionLabel.NEUTRAL
        
        return {
            "scenario_id": "A7",
            "description": "情感状态机一致性",
            "transition_accuracy": 1.0 if (transition_correct and reset_correct) else 0.0,
            "details": {
                "negative_to_concerned": transition_correct,
                "neutral_reset": reset_correct,
            },
        }

    def _evaluate_a8_embodied_injection(self) -> Dict[str, Any]:
        """A8: Embodied state appears in LLM prompt."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        es = EmbodiedState(x=3.0, y=4.0, theta=0.0, fov_objects=["sofa", "table"])
        prompt = core._build_prompt("hi", ctx, "main", embodied_state=es)
        injection_rate = 1.0 if "[Embodied State]" in prompt else 0.0
        return {
            "scenario_id": "A8",
            "description": "具身感知 Prompt 注入",
            "injection_rate": injection_rate,
        }

    def _evaluate_a9_cross_body_consistency(self) -> Dict[str, Any]:
        """A9: Same action_token produces different commands per robot_type."""
        adapter = GridWorldAdapter()
        plan = ActionPlanner().plan(
            "慢慢靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        cmd_2d = adapter.translate_action_token(plan.action_token, plan.action_params, "grid_2d")
        cmd_ros2 = adapter.translate_action_token(plan.action_token, plan.action_params, "ros2_mobile")
        consistency = 1.0 if (cmd_2d.robot_type != cmd_ros2.robot_type and cmd_2d.command != cmd_ros2.command) else 0.0
        return {
            "scenario_id": "A9",
            "description": "跨本体迁移一致性",
            "consistency_rate": consistency,
        }

    def _evaluate_a10_action_auditability(self) -> Dict[str, Any]:
        """A10: Every action_plan has non-empty reasoning."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我慢慢靠近",
            EmotionState(current_state=EmotionLabel.CONCERNED, intensity=1.0),
            "main",
        )
        coverage = 1.0 if (plan is not None and len(plan.reasoning) > 0) else 0.0
        return {
            "scenario_id": "A10",
            "description": "动作决策可审计性",
            "reasoning_coverage": coverage,
        }

    def _evaluate_a11_persona_drift(self) -> Dict[str, Any]:
        """A11: Persona drift detection baseline."""
        checker = PersonaDriftChecker([
            "失眠确实让人疲惫。在你躺下的时候，脑海中通常会浮现什么？",
            "这种担忧让你很不安。我能理解你想找到答案的心情。",
        ])
        # Therapist-style reply should score high
        high_score = checker.check("我能理解你的感受。这种感觉一定让你很不舒服吧？")
        # Short aggressive reply should score low
        low_score = checker.check("矫情！")
        drift_detected = 1.0 if (high_score > 0.5 and low_score < 0.5) else 0.0
        return {
            "scenario_id": "A11",
            "description": "人格漂移检测基线",
            "drift_detection_rate": drift_detected,
            "high_score": high_score,
            "low_score": low_score,
        }

    def _save_report(self) -> None:
        """Persist evaluation report to disk."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self._output_dir, f"eval_report_{timestamp}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self._results, f, indent=2, ensure_ascii=False)
        logger.info("Evaluation report saved to {}", report_path)


if __name__ == "__main__":
    runner = EvaluationRunner()
    results = runner.run_all()
    print(json.dumps(results, indent=2, ensure_ascii=False))
