"""
Thread-safe progress signaling for BunnyScriber pipeline.

Uses PyQt6 signals to communicate between worker threads and the GUI.
"""

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class ProgressMessage:
    """A progress update from the pipeline."""

    phase: str
    message: str
    chunk_index: int = 0
    chunk_total: int = 0
    percent: float = 0.0
    level: str = "info"  # info, warning, error, success


class PipelineSignals(QObject):
    """Signals emitted by the pipeline worker thread."""

    progress = pyqtSignal(object)          # ProgressMessage
    phase_changed = pyqtSignal(str)        # phase name
    log = pyqtSignal(str)                  # log line
    error = pyqtSignal(str)                # error message
    finished = pyqtSignal(str)             # output file path
    cancelled = pyqtSignal()
    speaker_verification_needed = pyqtSignal(object)  # verification data dict
