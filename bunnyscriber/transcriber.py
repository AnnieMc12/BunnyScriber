"""
Phase 4: Transcription of separated speaker tracks.

Transcribes each per-speaker audio track independently using
the configured transcription backend.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bunnyscriber.backends.base import (
    TranscriptionBackend,
    TranscriptResult,
    TranscriptSegment,
)


@dataclass
class SpeakerTranscript:
    """Transcript for a single speaker from one chunk."""

    speaker_label: str
    speaker_name: str
    chunk_index: int
    result: TranscriptResult
    track_path: str


def transcribe_speaker_track(
    track_path: str,
    speaker_label: str,
    speaker_name: str,
    chunk_index: int,
    backend: TranscriptionBackend,
    language: str = "en",
) -> SpeakerTranscript:
    """Transcribe a single speaker's audio track.

    Args:
        track_path: Path to the speaker's WAV track.
        speaker_label: Internal speaker label (e.g., "SPEAKER_00").
        speaker_name: User-assigned name (e.g., "Steve").
        chunk_index: Index of the chunk this track belongs to.
        backend: Transcription backend to use.
        language: Language code.

    Returns:
        SpeakerTranscript with timestamped result.
    """
    result = backend.transcribe(track_path, language=language)
    return SpeakerTranscript(
        speaker_label=speaker_label,
        speaker_name=speaker_name,
        chunk_index=chunk_index,
        result=result,
        track_path=track_path,
    )


def transcribe_all_tracks(
    speaker_tracks: Dict[str, str],
    speaker_names: Dict[str, str],
    chunk_index: int,
    backend: TranscriptionBackend,
    language: str = "en",
    on_progress=None,
) -> List[SpeakerTranscript]:
    """Transcribe all speaker tracks for a chunk.

    Args:
        speaker_tracks: Dict of speaker_label -> track_path.
        speaker_names: Dict of speaker_label -> user-assigned name.
        chunk_index: Index of the chunk.
        backend: Transcription backend.
        language: Language code.
        on_progress: Optional callback(message, percent).

    Returns:
        List of SpeakerTranscript results.
    """
    transcripts = []
    total = len(speaker_tracks)

    for i, (label, track_path) in enumerate(speaker_tracks.items()):
        name = speaker_names.get(label, label)

        if on_progress:
            on_progress(
                f"Transcribing {name} ({i + 1}/{total})...",
                (i / total),
            )

        transcript = transcribe_speaker_track(
            track_path=track_path,
            speaker_label=label,
            speaker_name=name,
            chunk_index=chunk_index,
            backend=backend,
            language=language,
        )
        transcripts.append(transcript)

    if on_progress:
        on_progress(f"Transcribed {total} speaker tracks.", 1.0)

    return transcripts


def save_transcript(transcript: SpeakerTranscript, output_dir: str) -> str:
    """Save a speaker transcript to a text file.

    Args:
        transcript: The speaker transcript to save.
        output_dir: Directory to save the file.

    Returns:
        Path to the saved transcript file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = (
        f"chunk{transcript.chunk_index:03d}_{transcript.speaker_label}_transcript.txt"
    )
    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Speaker: {transcript.speaker_name}\n")
        f.write(f"Label: {transcript.speaker_label}\n")
        f.write(f"Chunk: {transcript.chunk_index}\n")
        f.write("-" * 40 + "\n\n")

        for seg in transcript.result.segments:
            start_str = _format_timestamp(seg.start)
            end_str = _format_timestamp(seg.end)
            f.write(f"[{start_str} - {end_str}] {seg.text}\n")

    return path


def load_transcript(file_path: str) -> SpeakerTranscript:
    """Load a saved transcript file back into a SpeakerTranscript.

    Parses the format written by save_transcript().

    Args:
        file_path: Path to the transcript text file.

    Returns:
        SpeakerTranscript reconstructed from the file.
    """
    import re

    speaker_name = ""
    speaker_label = ""
    chunk_index = 0
    segments = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("Speaker: "):
                speaker_name = line[len("Speaker: "):]
            elif line.startswith("Label: "):
                speaker_label = line[len("Label: "):]
            elif line.startswith("Chunk: "):
                chunk_index = int(line[len("Chunk: "):])
            elif line.startswith("["):
                match = re.match(
                    r"\[(\d+:\d+:\d+\.\d+)\s*-\s*(\d+:\d+:\d+\.\d+)\]\s*(.*)",
                    line,
                )
                if match:
                    start = _parse_timestamp(match.group(1))
                    end = _parse_timestamp(match.group(2))
                    text = match.group(3)
                    segments.append(TranscriptSegment(
                        text=text,
                        start=start,
                        end=end,
                    ))

    return SpeakerTranscript(
        speaker_label=speaker_label,
        speaker_name=speaker_name,
        chunk_index=chunk_index,
        result=TranscriptResult(
            segments=segments,
            full_text=" ".join(s.text for s in segments),
        ),
        track_path="",
    )


def _parse_timestamp(ts: str) -> float:
    """Parse HH:MM:SS.mmm into seconds."""
    parts = ts.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def _format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
