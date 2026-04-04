"""
Local Whisper transcription backend.

Uses the openai-whisper package for local inference.
Models are downloaded on first use at the user's request.
"""

import os
from typing import Optional

from bunnyscriber.backends.base import (
    TranscriptionBackend,
    TranscriptResult,
    TranscriptSegment,
)


class WhisperLocalBackend(TranscriptionBackend):
    """Transcription using locally-running Whisper models."""

    name = "Local Whisper"
    requires_api_key = False
    is_local = True

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _get_model_dir(self) -> str:
        """Return the directory where Whisper models are cached."""
        return os.path.join(os.path.expanduser("~"), ".cache", "whisper")

    def is_model_downloaded(self) -> bool:
        """Check whether the selected model size has been downloaded."""
        try:
            import whisper
            model_dir = self._get_model_dir()
            # Whisper stores models as .pt files
            expected = os.path.join(model_dir, f"{self.model_size}.pt")
            return os.path.exists(expected)
        except ImportError:
            return False

    def download_model(self, on_progress=None) -> str:
        """Download the Whisper model. Returns status message."""
        try:
            import whisper
            if on_progress:
                on_progress(f"Downloading Whisper {self.model_size} model...")
            self._model = whisper.load_model(
                self.model_size,
                device=self.device if self.device != "auto" else None,
                download_root=self._get_model_dir(),
            )
            return f"Whisper {self.model_size} model downloaded successfully."
        except Exception as e:
            return f"Failed to download model: {e}"

    def _ensure_model(self):
        """Load the model if not already loaded."""
        if self._model is None:
            import whisper
            self._model = whisper.load_model(
                self.model_size,
                device=self.device if self.device != "auto" else None,
                download_root=self._get_model_dir(),
            )

    def transcribe(self, audio_path: str, language: str = "en") -> TranscriptResult:
        """Transcribe audio using local Whisper model.

        Args:
            audio_path: Path to WAV audio file.
            language: Language code.

        Returns:
            TranscriptResult with timestamped segments.
        """
        self._ensure_model()

        result = self._model.transcribe(
            audio_path,
            language=language,
            verbose=False,
            word_timestamps=True,
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                confidence=seg.get("avg_logprob", 0.0),
            ))

        return TranscriptResult(
            segments=segments,
            full_text=result.get("text", ""),
            language=result.get("language", language),
        )

    def is_available(self) -> bool:
        """Check if whisper is installed and model is downloaded."""
        try:
            import whisper
            return self.is_model_downloaded() or self._model is not None
        except ImportError:
            return False

    def test_connection(self) -> str:
        """Test local Whisper availability."""
        try:
            import whisper
            if self.is_model_downloaded() or self._model is not None:
                return f"Local Whisper ({self.model_size}) is ready."
            return (
                f"Whisper is installed but the {self.model_size} model "
                "has not been downloaded yet."
            )
        except ImportError:
            return "openai-whisper package is not installed."
