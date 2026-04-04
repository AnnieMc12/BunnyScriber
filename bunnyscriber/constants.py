"""
Theme colors, bunny messages, and application constants for BunnyScriber.
"""

import os
import sys

# ── Color Palette (Pastel Pink Theme) ────────────────────────────────

COLORS = {
    "bg": "#FFF5F5",
    "frame_bg": "#FFE4E6",
    "button": "#F9A8D4",
    "button_hover": "#F472B6",
    "button_pressed": "#EC4899",
    "accent": "#FDA4AF",
    "text": "#831843",
    "text_light": "#BE185D",
    "white": "#FFFFFF",
    "success": "#86EFAC",
    "success_text": "#065F46",
    "error": "#FCA5A5",
    "error_text": "#991B1B",
    "warning": "#FDE68A",
    "warning_text": "#92400E",
    "disabled": "#D1D5DB",
    "disabled_text": "#6B7280",
    "progress_bar": "#F472B6",
    "progress_bg": "#FCE7F3",
}

# ── Bunny Image States ───────────────────────────────────────────────

BUNNY_IMG_HEIGHT = 150


def _pics_dir():
    """Return path to the pics directory, works both in dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "pics")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "pics")


BUNNY_IMAGES = {
    "idle": "basebun.png",
    "working": "workbun.png",
    "happy": "winbun.png",
    "chomp": "chompbun.png",
    "error": "madbun.png",
    "shock": "shockbun.png",
    "sleepy": "sleepbun.png",
    "listen": "listenbun.png",
}


def bunny_path(state: str) -> str:
    """Return the full file path for a bunny image state."""
    filename = BUNNY_IMAGES.get(state, BUNNY_IMAGES["idle"])
    return os.path.join(_pics_dir(), filename)


# ── Bunny Messages ───────────────────────────────────────────────────

IDLE_MESSAGES = [
    "Hop hop! Ready to transcribe some audio!",
    "Welcome to my cozy transcription burrow!",
    "*wiggles nose* Got podcasts? I'll sort out who said what!",
    "Your friendly neighborhood transcription bunny!",
    "Ready to nibble through your audio files!",
]

WORKING_MESSAGES = [
    "*nibble nibble* Processing audio...",
    "*munch munch* Separating speakers...",
    "Hopping through the waveforms!",
    "*busy bunny noises* Almost there...",
    "Nom nom nom... tasty audio data!",
]

SUCCESS_MESSAGES = [
    "Yay! Transcript is ready! *happy bunny dance*",
    "Your transcript is done! *wiggles tail*",
    "Transcription complete! Time for a carrot break!",
    "*happy nose wiggles* All speakers identified!",
    "Hop-pily transcribed!",
]

ERROR_MESSAGES = [
    "*sad bunny noises*",
    "Oh no! Something went wrong...",
    "*flops ears* That didn't work...",
]

# ── Pipeline Phase Names ─────────────────────────────────────────────

PHASE_NAMES = {
    "chunking": "Splitting Audio",
    "separation": "Separating Speakers",
    "verification": "Speaker Verification",
    "transcription": "Transcribing",
    "reassembly": "Assembling Transcript",
    "cleanup": "LLM Cleanup",
}

# ── Audio Settings ───────────────────────────────────────────────────

SUPPORTED_AUDIO_FORMATS = (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac")
CHUNK_DURATION_MINUTES = 18
CHUNK_OVERLAP_SECONDS = 3
MIN_SILENCE_LEN_MS = 500
SILENCE_THRESH_DB = -40
CONFIDENCE_THRESHOLD = 0.65
SPEAKER_SAMPLE_SECONDS = 8

# ── Whisper Model Sizes ──────────────────────────────────────────────

WHISPER_MODELS = {
    "tiny": {"vram": "~1 GB", "speed": "Fastest", "quality": "Low"},
    "base": {"vram": "~1 GB", "speed": "Fast", "quality": "Fair"},
    "small": {"vram": "~2 GB", "speed": "Moderate", "quality": "Good"},
    "medium": {"vram": "~5 GB", "speed": "Slow", "quality": "Great"},
    "large": {"vram": "~10 GB", "speed": "Slowest", "quality": "Best"},
}

# ── Default Config ───────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "backend": None,
    "api_keys": {},
    "whisper_model_size": "base",
    "output_format": "txt",
    "llm_cleanup_enabled": False,
    "llm_cleanup_backend": None,
    "llm_cleanup_api_key": None,
    "auto_delete_intermediates": False,
    "work_dir": None,
    "custom_endpoints": [],
    "first_run_complete": False,
}

APP_NAME = "BunnyScriber"
CONFIG_FILENAME = "bunnyscriber_config.json"
WORK_DIR_NAME = "bunnyscriber_work"
