"""
Custom endpoint transcription backend.

Supports any OpenAI-compatible audio transcription API.
"""

import requests

from bunnyscriber.backends.base import (
    TranscriptionBackend,
    TranscriptResult,
    TranscriptSegment,
)


class CustomEndpointBackend(TranscriptionBackend):
    """Transcription via a user-defined OpenAI-compatible API endpoint."""

    requires_api_key = True
    is_local = False

    def __init__(
        self,
        display_name: str = "Custom",
        endpoint_url: str = "",
        api_key: str = "",
        model: str = "whisper-1",
    ):
        self.name = display_name
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def transcribe(self, audio_path: str, language: str = "en") -> TranscriptResult:
        """Transcribe audio using a custom OpenAI-compatible endpoint.

        Args:
            audio_path: Path to audio file.
            language: Language code.

        Returns:
            TranscriptResult with timestamped segments.
        """
        url = self.endpoint_url
        if not url.endswith("/transcriptions"):
            url = f"{url}/audio/transcriptions"

        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {
                "model": self.model,
                "language": language,
                "response_format": "verbose_json",
            }
            resp = requests.post(
                url,
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
        return bool(self.api_key and self.endpoint_url)

    def test_connection(self) -> str:
        if not self.endpoint_url:
            return "Endpoint URL is not set."
        if not self.api_key:
            return "API key is not set."
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                self.endpoint_url.rstrip("/").rsplit("/audio", 1)[0] + "/models",
                headers=headers,
                timeout=10,
            )
            if resp.status_code < 500:
                return f"Connection to {self.name} successful."
            return f"Server returned status {resp.status_code}."
        except Exception as e:
            return f"Connection to {self.name} failed: {e}"

    def to_dict(self) -> dict:
        """Serialize for config storage."""
        return {
            "display_name": self.name,
            "endpoint_url": self.endpoint_url,
            "api_key": self.api_key,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CustomEndpointBackend":
        """Deserialize from config storage."""
        return cls(
            display_name=data.get("display_name", "Custom"),
            endpoint_url=data.get("endpoint_url", ""),
            api_key=data.get("api_key", ""),
            model=data.get("model", "whisper-1"),
        )
