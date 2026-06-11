"""Abstract interface for speech recognition (ASR)."""

from abc import ABC, abstractmethod


class AbstractSpeechRecognizer(ABC):
    """Interface for converting audio input to text.

    Implementations may use local models (e.g., Whisper.cpp) or
    cloud APIs. All operations require an explicit branch_id.
    """

    @abstractmethod
    def transcribe(self, audio_data: bytes, branch_id: str) -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio bytes (e.g., PCM, WAV).
            branch_id: Explicit branch isolation identifier.

        Returns:
            Transcribed text string. Empty string if no speech detected.

        Raises:
            ValueError: If branch_id is empty.
            RuntimeError: If transcription fails irreparably.
        """
        ...
