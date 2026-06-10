"""Semantic memory schemas for L3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Concept:
    """L3 concept node in the intent graph."""

    id: str
    name: str
    concept_type: str
    parent_id: Optional[str] = None
    branch_id: str = "main"


@dataclass
class SemanticEdge:
    """Typed edge in the semantic graph."""

    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    branch_id: str = "main"
    status: str = "active"  # "active" | "deprecated" | "archived"


@dataclass
class IntentPattern:
    """Navigation strategy for a specific intent type."""

    intent_type: str
    trigger_keywords: List[str]
    entry_edge_types: List[str]
    max_hops: int = 3
    target_memory_types: List[str] = field(default_factory=lambda: ["episodic", "semantic"])
    priority_score: float = 1.0
