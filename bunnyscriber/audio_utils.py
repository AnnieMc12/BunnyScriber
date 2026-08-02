"""
Audio file utilities for BunnyScriber.

Handles format conversion, chunking at silence points, and audio I/O.

Duration probing, silence detection, and chunk extraction stream through
ffmpeg/ffprobe subprocesses so that arbitrarily long recordings never
need to be decoded into memory at once. (A 3-hour MP3 decodes to ~2 GB
of raw PCM — loading that via pydub can OOM-kill the process on smaller
machines.) pydub is still used for the small per-chunk operations.
"""

import os
import re
import subprocess
from typing import List, Optional

from pydub import AudioSegment

from bunnyscriber.constants import (
    SUPPORTED_AUDIO_FORMATS,
    CHUNK_DURATION_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    MIN_SILENCE_LEN_MS,
    SILENCE_THRESH_DB,
)

# Chunks are exported mono 16 kHz: both pyannote and Whisper downmix to
# 16 kHz mono internally anyway, and this keeps chunk files and the
# memory needed to process them ~12x smaller than 48 kHz stereo.
CHUNK_SAMPLE_RATE = 16000


def _check_supported(file_path: str) -> None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {ext}. "
            f"Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
        )


def load_audio(file_path: str) -> AudioSegment:
    """Load an audio file in any supported format.

    NOTE: decodes the whole file into memory — only use this for chunks
    and other short clips, never for the full-length input recording.

    Args:
        file_path: Path to the audio file.

    Returns:
        AudioSegment loaded from the file.

    Raises:
        ValueError: If the file format is not supported.
    """
    _check_supported(file_path)
    fmt = os.path.splitext(file_path)[1].lower().lstrip(".")
    return AudioSegment.from_file(file_path, format=fmt)


def get_duration_ms(file_path: str) -> int:
    """Return the duration of an audio file in milliseconds via ffprobe.

    Streams file metadata only — does not decode the audio.
    """
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(float(result.stdout.strip()) * 1000)


def get_audio_duration_str(file_path: str) -> str:
    """Return a human-readable duration string for an audio file."""
    total_seconds = get_duration_ms(file_path) / 1000
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m {seconds}s"


def detect_silence_midpoints(
    file_path: str,
    min_silence_len_ms: int = MIN_SILENCE_LEN_MS,
    silence_thresh_db: int = SILENCE_THRESH_DB,
) -> List[int]:
    """Find midpoints (ms) of silence windows using ffmpeg silencedetect.

    Streams the file through ffmpeg — constant memory regardless of length.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-i", file_path,
            "-af",
            f"silencedetect=noise={silence_thresh_db}dB:"
            f"d={min_silence_len_ms / 1000}",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", result.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", result.stderr)]

    midpoints = []
    for start, end in zip(starts, ends):
        midpoints.append(int((start + end) / 2 * 1000))
    return midpoints


def find_split_points(
    total_ms: int,
    silence_midpoints: List[int],
    chunk_ms: int,
    tolerance_ms: int = 60_000,
) -> List[int]:
    """Find good split points near target chunk boundaries.

    Prefers splitting inside a silence window near each target point.
    Falls back to the exact target if no silence is found nearby.

    Args:
        total_ms: Total audio duration in milliseconds.
        silence_midpoints: Midpoints (ms) of detected silence windows.
        chunk_ms: Target chunk duration in milliseconds.
        tolerance_ms: How far from the target to search for silence.

    Returns:
        List of split point positions in milliseconds.
    """
    if total_ms <= chunk_ms:
        return []

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


def _extract_chunk(
    file_path: str,
    start_ms: int,
    end_ms: Optional[int],
    out_path: str,
) -> None:
    """Extract [start_ms, end_ms) from an audio file to a mono 16 kHz WAV.

    Decodes only the requested span — memory use is bounded by ffmpeg's
    internal buffers, not the file length.
    """
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start_ms / 1000:.3f}"]
    if end_ms is not None:
        cmd += ["-to", f"{end_ms / 1000:.3f}"]
    cmd += [
        "-i", file_path,
        "-ac", "1", "-ar", str(CHUNK_SAMPLE_RATE),
        "-y", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


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
    _check_supported(file_path)
    os.makedirs(output_dir, exist_ok=True)

    if on_progress:
        on_progress("Reading audio duration...", 0.0)

    total_ms = get_duration_ms(file_path)
    chunk_ms = chunk_minutes * 60 * 1000
    overlap_ms = overlap_seconds * 1000

    if total_ms <= chunk_ms:
        # Audio is shorter than one chunk — convert as-is
        chunk_path = os.path.join(output_dir, "chunk_000.wav")
        _extract_chunk(file_path, 0, None, chunk_path)
        return [chunk_path]

    if on_progress:
        on_progress("Scanning for silence (streaming pass)...", 0.05)

    silence_midpoints = detect_silence_midpoints(file_path)

    if on_progress:
        on_progress("Finding optimal split points...", 0.15)

    split_points = find_split_points(total_ms, silence_midpoints, chunk_ms)

    # Build [start, end) ranges with overlap at the boundaries
    ranges = []
    prev = 0
    for point in split_points:
        ranges.append((prev, min(point + overlap_ms, total_ms)))
        prev = max(point - overlap_ms, 0)
    ranges.append((prev, None))  # final chunk runs to end of file

    if on_progress:
        on_progress(f"Splitting into {len(ranges)} chunks...", 0.2)

    chunk_paths = []
    for i, (start_ms, end_ms) in enumerate(ranges):
        chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.wav")
        _extract_chunk(file_path, start_ms, end_ms, chunk_path)
        chunk_paths.append(chunk_path)

        if on_progress:
            pct = 0.2 + 0.8 * ((i + 1) / len(ranges))
            on_progress(f"Saved chunk {i + 1}/{len(ranges)}", pct)

    return chunk_paths


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
