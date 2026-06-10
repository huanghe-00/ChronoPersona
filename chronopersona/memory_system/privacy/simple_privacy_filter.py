"""Simple privacy filter with regex-based L0 detection."""

import hashlib
import re
from typing import Dict, List

from loguru import logger

from chronopersona.contracts.interfaces.abstract_privacy_filter import IPrivacyFilter
from chronopersona.contracts.schemas.privacy import (
    FilterLevel,
    FilteredContent,
    PiiSpan,
    PiiType,
    PrivacyFilterStats,
)

# L0 regex patterns for high-confidence PII detection
L0_PATTERNS: Dict[PiiType, re.Pattern] = {
    PiiType.PHONE: re.compile(
        r"(?:1[3-9]\d{9})"
        r"|(?:\+86\s?1[3-9]\d{9})"
        r"|(?:\d{3}-\d{4}-\d{4})"
    ),
    PiiType.ID_CARD: re.compile(
        r"(?:[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])"
        r"|(?:[1-9]\d{7}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})"
    ),
    PiiType.EMAIL: re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    ),
    PiiType.BANK_CARD: re.compile(
        r"\b\d{16,19}\b"
    ),
}

SENSITIVE_RATIO_THRESHOLD: float = 0.3


class SimplePrivacyFilter(IPrivacyFilter):
    """MVA privacy filter with L0 regex detection.

    L0: Regex-based detection for phone, ID card, email, bank card.
    L1: [FUTURE] NER-based detection — returns empty spans in MVA.
    L2: [FUTURE] Semantic detection — returns empty spans in MVA.
    """

    def __init__(self) -> None:
        self._stats: Dict[str, PrivacyFilterStats] = {}

    def apply(
        self,
        content: str,
        filter_level: FilterLevel,
        branch_id: str,
    ) -> FilteredContent:
        """Apply privacy filtering at the specified level."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not content:
            return FilteredContent(
                original_content=content,
                filtered_content=content,
                filter_level=filter_level,
                branch_id=branch_id,
            )

        spans = self.detect_pii(content)

        # Filter spans by requested level
        if filter_level == FilterLevel.L0:
            spans = [
                s for s in spans
                if s.pii_type in (PiiType.PHONE, PiiType.ID_CARD, PiiType.EMAIL, PiiType.BANK_CARD)
            ]
        elif filter_level == FilterLevel.L1:
            spans = []
            logger.debug("L1 NER filtering not implemented in MVA, returning empty spans")
        elif filter_level == FilterLevel.L2:
            spans = []
            logger.debug("L2 semantic filtering not implemented in MVA, returning empty spans")

        # Build filtered content with replacements
        filtered = content
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            hash_prefix = hashlib.sha256(span.text.encode()).hexdigest()[:8]
            replacement = f"<REDACTED:{span.pii_type.value}:{hash_prefix}>"
            filtered = filtered[:span.start] + replacement + filtered[span.end:]
            span.replacement = replacement

        # Calculate sensitive ratio
        total_sensitive_chars = sum(s.end - s.start for s in spans)
        sensitive_ratio = total_sensitive_chars / len(content) if content else 0.0
        is_blocked = sensitive_ratio > SENSITIVE_RATIO_THRESHOLD

        # Update stats
        if branch_id not in self._stats:
            self._stats[branch_id] = PrivacyFilterStats()
        stats = self._stats[branch_id]
        stats.total_filter_calls += 1
        stats.total_pii_detected += len(spans)
        if is_blocked:
            stats.total_blocked += 1
        for span in spans:
            type_key = span.pii_type.value
            stats.pii_by_type[type_key] = stats.pii_by_type.get(type_key, 0) + 1

        if is_blocked:
            logger.warning(
                "Content blocked for migration: sensitive_ratio={:.2f} > threshold={:.2f} (branch={})",
                sensitive_ratio, SENSITIVE_RATIO_THRESHOLD, branch_id,
            )

        return FilteredContent(
            original_content=content,
            filtered_content=filtered,
            detected_spans=spans,
            sensitive_ratio=sensitive_ratio,
            is_blocked=is_blocked,
            filter_level=filter_level,
            branch_id=branch_id,
        )

    def detect_pii(self, content: str) -> List[PiiSpan]:
        """Detect PII spans using L0 regex patterns."""
        if not content:
            return []

        spans: List[PiiSpan] = []
        for pii_type, pattern in L0_PATTERNS.items():
            for match in pattern.finditer(content):
                matched_text = match.group()
                if pii_type == PiiType.BANK_CARD and len(matched_text) < 16:
                    continue
                spans.append(PiiSpan(
                    start=match.start(),
                    end=match.end(),
                    pii_type=pii_type,
                    text=matched_text,
                    confidence=1.0,
                ))

        spans.sort(key=lambda s: s.start)
        return spans

    def get_stats(self, branch_id: str) -> PrivacyFilterStats:
        """Get privacy filter statistics for a branch."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return self._stats.get(branch_id, PrivacyFilterStats())
