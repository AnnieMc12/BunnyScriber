"""
Base class for transcription backend adapters.

All backends produce the same output format: a list of timestamped segments.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranscriptSegment:
    """A single segment of transcribed text with timing info."""

    text: str
    start: float   # seconds from start of audio
    end: float     # seconds from start of audio
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class TranscriptResult:
    """Complete transcription result from a backend."""

    segments: List[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = ""

    def to_text(self) -> str:
        """Return the full transcript as plain text."""
        if self.full_text:
            return self.full_text
        return " ".join(seg.text for seg in self.segments)


class TranscriptionBackend(ABC):
    """Abstract base class for transcription backends."""

    name: str = "Base"
    requires_api_key: bool = False
    is_local: bool = False

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "en") -> TranscriptResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to a WAV audio file.
            language: Language code (e.g., "en").

        Returns:
            TranscriptResult with timestamped segments.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this backend is ready to use.

        Returns:
            True if the backend has all requirements met (API key, model, etc.).
        """
        ...

    def test_connection(self) -> str:
        """Test the backend connection/setup. Returns status message."""
        if self.is_available():
            return f"{self.name} is ready."
        return f"{self.name} is not available."
