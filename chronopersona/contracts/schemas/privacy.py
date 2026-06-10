"""Privacy filter schemas for PII detection and content filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FilterLevel(Enum):
    """Privacy filter level hierarchy."""
    L0 = "L0"  # Regex-based: phone, id_card, email, bank_card
    L1 = "L1"  # NER-based: person_name, address, organization [FUTURE]
    L2 = "L2"  # Semantic: medical, emotional privacy [FUTURE]


class PiiType(Enum):
    """PII entity types."""
    PHONE = "phone"
    ID_CARD = "id_card"
    EMAIL = "email"
    BANK_CARD = "bank_card"
    PERSON_NAME = "person_name"
    ADDRESS = "address"
    ORGANIZATION = "organization"


@dataclass
class PiiSpan:
    """A detected PII span in text content."""
    start: int
    end: int
    pii_type: PiiType
    text: str
    confidence: float = 1.0
    replacement: str = ""


@dataclass
class FilteredContent:
    """Result of privacy filtering operation."""
    original_content: str
    filtered_content: str
    detected_spans: List[PiiSpan] = field(default_factory=list)
    sensitive_ratio: float = 0.0
    is_blocked: bool = False
    filter_level: FilterLevel = FilterLevel.L0
    branch_id: str = ""


@dataclass
class PrivacyFilterStats:
    """Statistics for privacy filter operations."""
    total_filter_calls: int = 0
    total_pii_detected: int = 0
    total_blocked: int = 0
    pii_by_type: Dict[str, int] = field(default_factory=dict)
    accuracy_metrics: Dict[str, Any] = field(default_factory=dict)
