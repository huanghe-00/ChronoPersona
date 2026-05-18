"""Evaluation metrics using ranx for IR-quality assessment."""

from __future__ import annotations

from typing import Dict, List, Set

from ranx import Qrels, Run, evaluate


class Metrics:
    """Retrieval quality metrics backed by ranx."""

    @staticmethod
    def _to_ranx(
        retrieved_ids: List[str],
        expected_ids: List[str],
    ) -> tuple[Qrels, Run]:
        """Convert flat id lists to ranx Qrels / Run objects."""
        qrels_data: Dict[str, Dict[str, int]] = {"q1": {}}
        for eid in expected_ids:
            qrels_data["q1"][eid] = 1

        run_data: Dict[str, Dict[str, float]] = {"q1": {}}
        for rank, rid in enumerate(retrieved_ids, start=1):
            run_data["q1"][rid] = 1.0 / rank

        # ranx Run requires at least one document per query
        if not retrieved_ids:
            run_data["q1"]["__dummy__"] = 0.0

        return Qrels(qrels_data), Run(run_data)

    @staticmethod
    def _eval_metric(qrels: Qrels, run: Run, metric: str) -> float:
        """Safely evaluate a single metric, handling ranx return type variance."""
        try:
            result = evaluate(qrels, run, [metric])
            # ranx may return dict-like Report or raw scalar depending on version
            if hasattr(result, "get"):
                return float(result.get(metric, 0.0))
            return float(result)
        except Exception:
            return 0.0

    @staticmethod
    def recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
        if not expected_ids:
            return 0.0
        qrels, run = Metrics._to_ranx(retrieved_ids, expected_ids)
        return Metrics._eval_metric(qrels, run, f"recall@{k}")

    @staticmethod
    def mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        if not expected_ids:
            return 0.0
        qrels, run = Metrics._to_ranx(retrieved_ids, expected_ids)
        return Metrics._eval_metric(qrels, run, "mrr")

    @staticmethod
    def ndcg_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
        if not expected_ids:
            return 0.0
        qrels, run = Metrics._to_ranx(retrieved_ids, expected_ids)
        return Metrics._eval_metric(qrels, run, f"ndcg@{k}")

    @staticmethod
    def map(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        if not expected_ids:
            return 0.0
        qrels, run = Metrics._to_ranx(retrieved_ids, expected_ids)
        return Metrics._eval_metric(qrels, run, "map")

    @staticmethod
    def answer_f1(prediction: str, reference: str) -> float:
        pred_tokens: Set[str] = set(prediction.lower().split())
        ref_tokens: Set[str] = set(reference.lower().split())
        if not pred_tokens or not ref_tokens:
            return 0.0
        common = len(pred_tokens & ref_tokens)
        precision = common / len(pred_tokens)
        recall = common / len(ref_tokens)
        if precision + recall == 0.0:
            return 0.0
        return 2.0 * precision * recall / (precision + recall)
