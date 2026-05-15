"""Model routing and cost tracking schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ModelRequest:
    """Request payload for model routing."""

    task_type: str = ""
    prompt: str = ""
    context: Optional[Any] = None
    model_preference: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Response payload from model routing."""

    content: str = ""
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetStatus:
    """Budget consumption status."""

    branch_id: str = ""
    session_id: str = ""
    token_budget: int = 0
    tokens_used: int = 0
    usd_budget: float = 0.0
    usd_used: float = 0.0
    warning_level: str = "normal"  # normal / warning / exceeded
    last_updated: str = ""


@dataclass
class CostRecord:
    """Skill execution internal cost."""

    internal_tokens: int = 0
    internal_latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostReport:
    """Aggregated cost report."""

    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    breakdown_by_model: Dict[str, Any] = field(default_factory=dict)
    breakdown_by_branch: Dict[str, Any] = field(default_factory=dict)
