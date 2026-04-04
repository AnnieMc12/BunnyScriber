"""
Audio file utilities for BunnyScriber.

Handles format conversion, chunking at silence points, and audio I/O.
Relies on pydub (which uses ffmpeg under the hood).
"""

import os
from typing import List, Tuple, Optional

from pydub import AudioSegment
from pydub.silence import detect_silence

from bunnyscriber.constants import (
    SUPPORTED_AUDIO_FORMATS,
    CHUNK_DURATION_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    MIN_SILENCE_LEN_MS,
    SILENCE_THRESH_DB,
)


def load_audio(file_path: str) -> AudioSegment:
    """Load an audio file in any supported format.

    Args:
        file_path: Path to the audio file.

    Returns:
        AudioSegment loaded from the file.

    Raises:
        ValueError: If the file format is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {ext}. "
            f"Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
        )
    fmt = ext.lstrip(".")
    if fmt == "m4a":
        fmt = "m4a"
    return AudioSegment.from_file(file_path, format=fmt)


def find_split_points(
    audio: AudioSegment,
    chunk_ms: int,
    tolerance_ms: int = 60_000,
) -> List[int]:
    """Find good split points near target chunk boundaries.

    Looks for silence windows near each target split point and prefers
    splitting there. Falls back to the exact target if no silence found.

    Args:
        audio: The full audio segment.
        chunk_ms: Target chunk duration in milliseconds.
        tolerance_ms: How far from the target to search for silence.

    Returns:
        List of split point positions in milliseconds.
    """
    total_ms = len(audio)
    if total_ms <= chunk_ms:
        return []

    silences = detect_silence(
        audio,
        min_silence_len=MIN_SILENCE_LEN_MS,
        silence_thresh=SILENCE_THRESH_DB,
    )
    # silences is a list of [start_ms, end_ms] pairs
    silence_midpoints = [(s + e) // 2 for s, e in silences]

    split_points = []
    target = chunk_ms

    while target < total_ms:
        best = target
        best_dist = tolerance_ms + 1

        for mid in silence_midpoints:
            dist = abs(mid - target)
            if dist < best_dist:
                best = mid
                best_dist = dist

        split_points.append(best)
        target = best + chunk_ms

    return split_points


def split_audio(
    audio: AudioSegment,
    split_points: List[int],
    overlap_ms: int,
) -> List[AudioSegment]:
    """Split audio at the given points with overlap.

    Args:
        audio: The full audio segment.
        split_points: Positions (ms) at which to split.
        overlap_ms: Overlap in milliseconds to include at boundaries.

    Returns:
        List of audio chunks.
    """
    chunks = []
    prev = 0

    for point in split_points:
        end = min(point + overlap_ms, len(audio))
        chunks.append(audio[prev:end])
        prev = max(point - overlap_ms, 0)

    # Final chunk
    chunks.append(audio[prev:])
    return chunks


def chunk_audio_file(
    file_path: str,
    output_dir: str,
    chunk_minutes: int = CHUNK_DURATION_MINUTES,
    overlap_seconds: int = CHUNK_OVERLAP_SECONDS,
    on_progress=None,
) -> List[str]:
    """Split an audio file into chunks and save them.

    Args:
        file_path: Path to the input audio file.
        output_dir: Directory to save chunk files.
        chunk_minutes: Target chunk duration in minutes.
        overlap_seconds: Overlap at chunk boundaries in seconds.
        on_progress: Optional callback(message: str, percent: float).

    Returns:
        List of paths to saved chunk files.
    """
    os.makedirs(output_dir, exist_ok=True)

    if on_progress:
        on_progress("Loading audio file...", 0.0)

    audio = load_audio(file_path)
    chunk_ms = chunk_minutes * 60 * 1000
    overlap_ms = overlap_seconds * 1000

    if on_progress:
        on_progress("Finding optimal split points...", 0.1)

    split_points = find_split_points(audio, chunk_ms)

    if not split_points:
        # Audio is shorter than one chunk — save as-is
        chunk_path = os.path.join(output_dir, "chunk_000.wav")
        audio.export(chunk_path, format="wav")
        return [chunk_path]

    if on_progress:
        on_progress(f"Splitting into {len(split_points) + 1} chunks...", 0.2)

    chunks = split_audio(audio, split_points, overlap_ms)
    chunk_paths = []

    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.wav")
        chunk.export(chunk_path, format="wav")
        chunk_paths.append(chunk_path)

        if on_progress:
            pct = 0.2 + 0.8 * ((i + 1) / len(chunks))
            on_progress(f"Saved chunk {i + 1}/{len(chunks)}", pct)

    return chunk_paths


def get_audio_duration_str(file_path: str) -> str:
    """Return a human-readable duration string for an audio file."""
    audio = load_audio(file_path)
    total_seconds = len(audio) / 1000
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m {seconds}s"


def extract_segment(
    audio: AudioSegment,
    start_ms: int,
    end_ms: int,
) -> AudioSegment:
    """Extract a segment from an audio clip."""
    return audio[start_ms:end_ms]


def export_wav(audio: AudioSegment, path: str) -> str:
    """Export an AudioSegment as WAV and return the path."""
    audio.export(path, format="wav")
    return path
