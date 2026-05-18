"""Insight schema for periodic active reflection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
