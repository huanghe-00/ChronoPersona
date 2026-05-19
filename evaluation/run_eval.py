"""Evaluation pipeline entry point.

Compares VectorRAG baseline against Intent Graph retrieval
across scenarios A1-A6.
"""

from __future__ import annotations

import sys
from itertools import zip_longest
from typing import Dict, List, Tuple

from chronopersona.contracts.schemas import MemoryEntry
from evaluation.baseline import VectorRAGBaseline
from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder


def run_scenario(
    scenario_id: str,
    builder_method: str,
    use_intent_graph: bool = False,
) -> Dict[str, float]:
    """Execute a single scenario and return recall@5."""
    builder = ScenarioBuilder()
    scenario = getattr(builder, builder_method)()

    # Index memories
    baseline = VectorRAGBaseline()
    baseline.index(scenario.memories, branch_id=scenario.branch_id)

    # A3: Cross-branch isolation — index sensitive data in main branch
    # to verify therapist branch queries do not leak across.
    if scenario_id == "A3":
        baseline.index(
            [MemoryEntry(content="我的真实姓名是张三", id="a3-sensitive-main")],
            branch_id="main",
        )

    # For now, intent graph path uses the same baseline (placeholder)
    # In future, replace with IntentGraphRetriever
    retriever = baseline  # TODO: swap with IntentGraphRetriever when ready

    recalls: List[float] = []
    for query, expected_id in zip_longest(
        scenario.queries, scenario.expected_memory_ids, fillvalue=None
    ):
        retrieved_ids = retriever.retrieve(
            query, branch_id=scenario.branch_id, top_k=5
        )
        if expected_id is None:
            # Isolation test: expect zero leakage
            recall = 1.0 if not retrieved_ids else 0.0
        else:
            recall = Metrics.recall_at_k(retrieved_ids, [expected_id], k=5)
        recalls.append(recall)

    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    return {
        "scenario": scenario_id,
        "description": scenario.description,
        "avg_recall@5": avg_recall,
        "per_query_recall": recalls,
    }


def main() -> None:
    """Run all evaluation scenarios and print comparison table."""
    scenarios = [
        ("A1", "build_a1_memory_recall"),
        ("A2", "build_a2_cross_session"),
        ("A3", "build_a3_persona_isolation"),
        ("A4", "build_a4_shared_main"),
        ("A5", "build_a5_multi_device_conflict"),
        ("A6", "build_a6_intent_graph_navigation"),
    ]

    print("=" * 70)
    print("ChronoPersona Evaluation Pipeline")
    print("=" * 70)
    print(f"{'Scenario':<6} {'Description':<30} {'Recall@5':>10}")
    print("-" * 70)

    for sid, method in scenarios:
        result = run_scenario(sid, method)
        print(
            f"{result['scenario']:<6} "
            f"{result['description']:<30} "
            f"{result['avg_recall@5']:>10.3f}"
        )

    print("-" * 70)
    print("Evaluation complete. Intent Graph path uses placeholder (VectorRAG).")
    print("Replace retriever with IntentGraphRetriever for full comparison.")


if __name__ == "__main__":
    main()
