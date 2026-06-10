"""Conditional distiller: extract conditional rules from episodic memory."""

import re
import uuid
from typing import List, Optional

from loguru import logger

from chronopersona.contracts.schemas import BehavioralRule, MemoryEntry


class ConditionalDistiller:
    """MVA conditional rule extractor using regex templates.

    Extracts trigger/action pairs from Chinese conditional sentences.
    Preserves negation words ("不", "没有", "别") and conditional markers.
    """

    CONDITIONAL_PATTERNS = [
        (r"如果(.+?)(?:，|,)?\s*(?:就|应该|可以|需要|必须|要)(.+?)(?:[。！；]|$)", "如果"),
        (r"当(.+?)时(?:，|,)?\s*(.+?)(?:[。！；]|$)", "当"),
        (r"除非(.+?)(?:，|,)?\s*(?:否则|不然)(.+?)(?:[。！；]|$)", "除非"),
        (r"(.+?)的话(?:，|,)?\s*(?:就|应该|可以|需要|必须|要)(.+?)(?:[。！；]|$)", "的话"),
    ]

    NEGATION_WORDS = {"不", "没有", "别", "未", "否", "无", "莫"}

    def __init__(self, min_confidence: float = 0.7) -> None:
        self._min_confidence = min_confidence

    def distill(self, memories: List[MemoryEntry]) -> List[BehavioralRule]:
        """Extract conditional rules from a batch of memories."""
        rules: List[BehavioralRule] = []
        for mem in memories:
            rule = self._distill_single(mem)
            if rule is not None:
                rules.append(rule)
        logger.info("Distilled {} rules from {} memories", len(rules), len(memories))
        return rules

    def _distill_single(self, memory: MemoryEntry) -> Optional[BehavioralRule]:
        """Attempt to extract one BehavioralRule from a MemoryEntry."""
        content = memory.content
        if not content:
            return None

        for pattern, marker in self.CONDITIONAL_PATTERNS:
            match = re.search(pattern, content)
            if match:
                trigger = match.group(1).strip()
                action = match.group(2).strip()

                if not trigger or not action:
                    continue

                has_negation = any(w in trigger for w in self.NEGATION_WORDS)

                # MVA heuristic: longer conditions → higher confidence
                confidence = min(0.95, 0.7 + 0.01 * (len(trigger) + len(action)))
                if confidence < self._min_confidence:
                    continue

                return BehavioralRule(
                    id=f"rule-{uuid.uuid4().hex[:8]}",
                    trigger=f"{marker}：{trigger}" if marker not in trigger else trigger,
                    action=action,
                    confidence=confidence,
                    source_memory_ids=[memory.id] if memory.id else [],
                    branch_id=memory.branch_id,
                    negation_preserved=has_negation,
                )

        return None
