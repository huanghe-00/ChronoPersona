"""Tests for privacy filter: L0 regex detection, blocking threshold, and mock."""

import pytest

from chronopersona.contracts.schemas.privacy import (
    FilterLevel,
    FilteredContent,
    PiiType,
    PrivacyFilterStats,
)
from chronopersona.memory_system.privacy.simple_privacy_filter import (
    SimplePrivacyFilter,
    SENSITIVE_RATIO_THRESHOLD,
)
from chronopersona.mocks.mock_privacy_filter import MockPrivacyFilter


class TestSimplePrivacyFilterL0:
    """L0 regex-based PII detection tests."""

    def setup_method(self):
        self.filter = SimplePrivacyFilter()

    def test_phone_detection_and_replacement(self):
        """T01: Chinese mobile phone number detection and redaction."""
        # Use longer text to keep sensitive ratio below 0.3 threshold
        content = "我的手机号是13812345678，请记住，这是非常重要的联系方式，请妥善保管"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert result.filtered_content != content
        assert "<REDACTED:phone:" in result.filtered_content
        assert "13812345678" not in result.filtered_content
        assert len(result.detected_spans) == 1
        assert result.detected_spans[0].pii_type == PiiType.PHONE
        assert result.detected_spans[0].confidence == 1.0
        assert result.sensitive_ratio > 0
        assert not result.is_blocked

    def test_id_card_detection(self):
        """T02: Chinese ID card number detection."""
        content = "身份证号110101199003071234"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert "<REDACTED:id_card:" in result.filtered_content
        assert "110101199003071234" not in result.filtered_content
        assert len(result.detected_spans) == 1
        assert result.detected_spans[0].pii_type == PiiType.ID_CARD

    def test_email_detection(self):
        """T03: Email address detection."""
        content = "发邮件到test@example.com"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert "<REDACTED:email:" in result.filtered_content
        assert "test@example.com" not in result.filtered_content
        assert len(result.detected_spans) == 1
        assert result.detected_spans[0].pii_type == PiiType.EMAIL

    def test_multiple_pii_types(self):
        """T04: Multiple PII types in single content."""
        content = "手机13812345678，邮箱test@example.com，身份证110101199003071234"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert len(result.detected_spans) == 3
        types = {s.pii_type for s in result.detected_spans}
        assert PiiType.PHONE in types
        assert PiiType.EMAIL in types
        assert PiiType.ID_CARD in types

    def test_no_pii_content(self):
        """T05: Content without PII passes through unchanged."""
        content = "今天天气不错，适合散步"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert result.filtered_content == content
        assert len(result.detected_spans) == 0
        assert result.sensitive_ratio == 0.0
        assert not result.is_blocked

    def test_sensitive_ratio_blocking(self):
        """T06: Content with >30% sensitive ratio is blocked for migration."""
        phone = "13812345678"
        content = f"号码{phone}"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert result.sensitive_ratio > SENSITIVE_RATIO_THRESHOLD
        assert result.is_blocked

    def test_empty_content(self):
        """T07: Empty content returns empty result."""
        result = self.filter.apply("", FilterLevel.L0, branch_id="main")
        assert result.filtered_content == ""
        assert len(result.detected_spans) == 0

    def test_empty_branch_id_raises(self):
        """T08: Empty branch_id raises ValueError."""
        with pytest.raises(ValueError, match="branch_id must not be empty"):
            self.filter.apply("test", FilterLevel.L0, branch_id="")

    def test_stats_tracking(self):
        """T09: Stats are tracked per branch."""
        self.filter.apply("手机13812345678", FilterLevel.L0, branch_id="main")
        self.filter.apply("无PII内容", FilterLevel.L0, branch_id="main")
        stats = self.filter.get_stats("main")
        assert stats.total_filter_calls == 2
        assert stats.total_pii_detected == 1
        assert stats.pii_by_type.get("phone", 0) == 1

    def test_stats_branch_isolation(self):
        """T10: Stats are isolated per branch."""
        self.filter.apply("手机13812345678", FilterLevel.L0, branch_id="branch_a")
        self.filter.apply("无PII内容", FilterLevel.L0, branch_id="branch_b")
        stats_a = self.filter.get_stats("branch_a")
        stats_b = self.filter.get_stats("branch_b")
        assert stats_a.total_filter_calls == 1
        assert stats_a.total_pii_detected == 1
        assert stats_b.total_filter_calls == 1
        assert stats_b.total_pii_detected == 0

    def test_l1_returns_empty_spans(self):
        """T11: L1 NER filtering returns empty spans in MVA ([FUTURE])."""
        content = "张三住在北京市朝阳区"
        result = self.filter.apply(content, FilterLevel.L1, branch_id="main")
        assert result.filtered_content == content
        assert len(result.detected_spans) == 0

    def test_l2_returns_empty_spans(self):
        """T12: L2 semantic filtering returns empty spans in MVA ([FUTURE])."""
        content = "我有抑郁症的诊断记录"
        result = self.filter.apply(content, FilterLevel.L2, branch_id="main")
        assert result.filtered_content == content
        assert len(result.detected_spans) == 0

    def test_detect_pii_only(self):
        """T13: detect_pii returns spans without filtering."""
        content = "手机13812345678"
        spans = self.filter.detect_pii(content)
        assert len(spans) == 1
        assert spans[0].pii_type == PiiType.PHONE
        assert spans[0].text == "13812345678"
        assert "13812345678" in content


class TestMockPrivacyFilter:
    """Mock privacy filter tests."""

    def setup_method(self):
        self.filter = MockPrivacyFilter()

    def test_mock_apply_no_filtering(self):
        """T14: Mock apply returns content unchanged."""
        content = "手机13812345678"
        result = self.filter.apply(content, FilterLevel.L0, branch_id="main")
        assert result.filtered_content == content
        assert len(result.detected_spans) == 0
        assert not result.is_blocked

    def test_mock_detect_pii_empty(self):
        """T15: Mock detect_pii returns empty list."""
        spans = self.filter.detect_pii("任何内容")
        assert spans == []

    def test_mock_stats_call_count(self):
        """T16: Mock stats track call count."""
        self.filter.apply("test1", FilterLevel.L0, branch_id="main")
        self.filter.apply("test2", FilterLevel.L0, branch_id="main")
        stats = self.filter.get_stats("main")
        assert stats.total_filter_calls == 2

    def test_mock_empty_branch_id_raises(self):
        """T17: Mock raises ValueError for empty branch_id."""
        with pytest.raises(ValueError, match="branch_id must not be empty"):
            self.filter.apply("test", FilterLevel.L0, branch_id="")
