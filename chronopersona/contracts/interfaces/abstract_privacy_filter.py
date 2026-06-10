"""Abstract interface for privacy filtering."""

from abc import ABC, abstractmethod
from typing import List

from chronopersona.contracts.schemas.privacy import (
    FilterLevel,
    FilteredContent,
    PiiSpan,
    PrivacyFilterStats,
)


class IPrivacyFilter(ABC):
    """Interface for PII detection and content filtering.

    Supports multi-level privacy filtering:
    - L0: Regex-based (phone, id_card, email, bank_card) — MVA implemented
    - L1: NER-based (person_name, address, organization) — [FUTURE]
    - L2: Semantic (medical, emotional) — [FUTURE]

    Accuracy targets (MVA):
    - L0 regex: recall >= 95%, precision >= 90%
    - L1 NER: recall >= 80% (post-MVA target >= 95%)
    """

    @abstractmethod
    def apply(
        self,
        content: str,
        filter_level: FilterLevel,
        branch_id: str,
    ) -> FilteredContent:
        """Apply privacy filtering to content at specified level.

        Args:
            content: Raw text content to filter.
            filter_level: Filter level (L0/L1/L2).
            branch_id: Explicit branch identifier for stats tracking.

        Returns:
            FilteredContent with PII replaced and detection metadata.
        """
        ...

    @abstractmethod
    def detect_pii(self, content: str) -> List[PiiSpan]:
        """Detect PII spans in content without filtering.

        Args:
            content: Raw text content to scan.

        Returns:
            List of detected PII spans with type, position, and confidence.
        """
        ...

    @abstractmethod
    def get_stats(self, branch_id: str) -> PrivacyFilterStats:
        """Get privacy filter statistics for a branch.

        Args:
            branch_id: Explicit branch identifier.

        Returns:
            Aggregated statistics including detection counts and accuracy.
        """
        ...
