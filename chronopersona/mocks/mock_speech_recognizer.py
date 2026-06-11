"""Mock speech recognizer for testing."""

from chronopersona.contracts.interfaces import AbstractSpeechRecognizer


class MockSpeechRecognizer(AbstractSpeechRecognizer):
    """Mock ASR that returns predetermined text."""

    def __init__(self, fixed_text: str = "") -> None:
        self._fixed_text = fixed_text
        self._calls: list[tuple[bytes, str]] = []

    def transcribe(self, audio_data: bytes, branch_id: str) -> str:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._calls.append((audio_data, branch_id))
        return self._fixed_text
