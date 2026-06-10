"""Insight schema for periodic active reflection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Insight:
    """Periodic active reflection output."""

    id: str
    insight_type: str  # pattern, trend, conflict, recommendation
    source_memory_ids: List[str]
    content: str
    confidence: float  # 0.0 ~ 1.0
    valid_until: Optional[datetime] = None
    branch_id: str = "main"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BehavioralRule:
    """Distilled conditional rule from episodic memory.

    Preserves trigger conditions (e.g., "如果/除非/当...") intact.
    Negation words ("不", "没有") are retained and never eliminated.
    """

    id: str
    trigger: str  # Condition clause, e.g., "用户提及性能优化"
    action: str  # Action clause, e.g., "主动建议查看火焰图"
    confidence: float  # 0.0 ~ 1.0
    source_memory_ids: List[str]
    branch_id: str = "main"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    negation_preserved: bool = True  # MVA: always True, marks negation retention
