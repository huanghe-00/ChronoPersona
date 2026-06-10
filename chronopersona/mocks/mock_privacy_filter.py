"""Mock implementation of IPrivacyFilter."""

from chronopersona.contracts.interfaces.abstract_privacy_filter import IPrivacyFilter
from chronopersona.contracts.schemas.privacy import (
    FilterLevel,
    FilteredContent,
    PiiSpan,
    PrivacyFilterStats,
)


class MockPrivacyFilter(IPrivacyFilter):
    """Mock privacy filter for testing — no actual filtering."""

    def __init__(self) -> None:
        self._call_count: int = 0

    def apply(
        self,
        content: str,
        filter_level: FilterLevel,
        branch_id: str,
    ) -> FilteredContent:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._call_count += 1
        return FilteredContent(
            original_content=content,
            filtered_content=content,
            detected_spans=[],
            sensitive_ratio=0.0,
            is_blocked=False,
            filter_level=filter_level,
            branch_id=branch_id,
        )

    def detect_pii(self, content: str) -> list:
        """Mock detection returns empty list."""
        return []

    def get_stats(self, branch_id: str) -> PrivacyFilterStats:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return PrivacyFilterStats(total_filter_calls=self._call_count)
