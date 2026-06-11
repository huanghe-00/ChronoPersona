"""Tests for speech recognizer interface and mock."""

import pytest

from chronopersona.contracts.interfaces import AbstractSpeechRecognizer
from chronopersona.mocks.mock_speech_recognizer import MockSpeechRecognizer


class TestMockSpeechRecognizer:
    """T01-T03: Mock ASR tests."""

    def test_transcribe_returns_fixed_text(self) -> None:
        """T01: Mock returns configured fixed text."""
        recognizer = MockSpeechRecognizer(fixed_text="到沙发旁边")
        result = recognizer.transcribe(b"fake_audio", branch_id="main")
        assert result == "到沙发旁边"

    def test_empty_branch_raises_valueerror(self) -> None:
        """T02: Empty branch_id raises ValueError."""
        recognizer = MockSpeechRecognizer()
        with pytest.raises(ValueError):
            recognizer.transcribe(b"audio", branch_id="")

    def test_transcribe_records_calls(self) -> None:
        """T03: Mock records invocation arguments."""
        recognizer = MockSpeechRecognizer(fixed_text="你好")
        recognizer.transcribe(b"audio1", branch_id="main")
        recognizer.transcribe(b"audio2", branch_id="main")
        assert len(recognizer._calls) == 2
        assert recognizer._calls[0] == (b"audio1", "main")
