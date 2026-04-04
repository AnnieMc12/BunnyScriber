"""
Mistral API transcription backend.

Uses Mistral's audio transcription endpoint.
"""

import requests

from bunnyscriber.backends.base import (
    TranscriptionBackend,
    TranscriptResult,
    TranscriptSegment,
)


class MistralTranscriptionBackend(TranscriptionBackend):
    """Transcription via the Mistral API."""

    name = "Mistral API"
    requires_api_key = True
    is_local = False

    ENDPOINT = "https://api.mistral.ai/v1/audio/transcriptions"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def transcribe(self, audio_path: str, language: str = "en") -> TranscriptResult:
        """Transcribe audio using Mistral's API.

        Args:
            audio_path: Path to audio file.
            language: Language code.

        Returns:
            TranscriptResult with timestamped segments.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {
                "model": "mistral-asr",
                "language": language,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            }
            resp = requests.post(
                self.ENDPOINT,
                headers=headers,
                files=files,
                data=data,
                timeout=300,
            )

        resp.raise_for_status()
        result = resp.json()

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                text=seg.get("text", "").strip(),
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                confidence=seg.get("avg_logprob", 0.0),
            ))

        return TranscriptResult(
            segments=segments,
            full_text=result.get("text", ""),
            language=language,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> str:
        if not self.api_key:
            return "Mistral API key is not set."
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                "https://api.mistral.ai/v1/models",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            return "Mistral API connection successful."
        except Exception as e:
            return f"Mistral API connection failed: {e}"
