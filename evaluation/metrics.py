"""Evaluation metrics for memory retrieval quality."""

from __future__ import annotations

from typing import List, Set


class Metrics:
    """Retrieval quality metrics."""

    @staticmethod
    def recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
        """Calculate Recall@K."""
        if not expected_ids:
            return 0.0
        retrieved_set: Set[str] = set(retrieved_ids[:k])
        expected_set: Set[str] = set(expected_ids)
        hits = len(retrieved_set & expected_set)
        return hits / len(expected_set)

    @staticmethod
    def mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        if not expected_ids:
            return 0.0
        expected_set: Set[str] = set(expected_ids)
        for rank, mid in enumerate(retrieved_ids, start=1):
            if mid in expected_set:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def answer_f1(prediction: str, reference: str) -> float:
        """Token-level F1 between prediction and reference."""
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
