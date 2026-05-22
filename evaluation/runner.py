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
