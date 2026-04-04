"""
OpenAI Whisper API transcription backend.

Uses the OpenAI API for cloud-based Whisper transcription.
"""

from bunnyscriber.backends.base import (
    TranscriptionBackend,
    TranscriptResult,
    TranscriptSegment,
)


class OpenAIWhisperBackend(TranscriptionBackend):
    """Transcription via the OpenAI Whisper API endpoint."""

    name = "OpenAI Whisper API"
    requires_api_key = True
    is_local = False

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def transcribe(self, audio_path: str, language: str = "en") -> TranscriptResult:
        """Transcribe audio using OpenAI's Whisper API.

        Args:
            audio_path: Path to audio file.
            language: Language code.

        Returns:
            TranscriptResult with timestamped segments.
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = []
        for seg in getattr(response, "segments", []):
            segments.append(TranscriptSegment(
                text=seg.get("text", "").strip(),
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                confidence=seg.get("avg_logprob", 0.0),
            ))

        return TranscriptResult(
            segments=segments,
            full_text=getattr(response, "text", ""),
            language=language,
        )

    def is_available(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    def test_connection(self) -> str:
        """Test the OpenAI API connection."""
        if not self.api_key:
            return "OpenAI API key is not set."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            client.models.list()
            return "OpenAI API connection successful."
        except Exception as e:
            return f"OpenAI API connection failed: {e}"
