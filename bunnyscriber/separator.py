"""
Phase 2: Speaker separation using pyannote.audio for diarization.

Performs speaker diarization on each audio chunk, then extracts
per-speaker audio segments. Segments below the confidence threshold
are flagged as uncertain for user review.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from pydub import AudioSegment

from bunnyscriber.constants import CONFIDENCE_THRESHOLD, SPEAKER_SAMPLE_SECONDS


@dataclass
class SpeakerSegment:
    """A segment of audio attributed to one speaker."""

    speaker_label: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0
    is_uncertain: bool = False

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass
class SeparationResult:
    """Result of speaker separation for one audio chunk."""

    chunk_path: str
    speaker_segments: List[SpeakerSegment] = field(default_factory=list)
    speaker_labels: List[str] = field(default_factory=list)
    uncertain_segments: List[SpeakerSegment] = field(default_factory=list)
    speaker_tracks: Dict[str, str] = field(default_factory=dict)  # label -> wav path
    speaker_samples: Dict[str, str] = field(default_factory=dict)  # label -> sample wav path


def run_diarization(
    audio_path: str,
    num_speakers: int,
    auth_token: Optional[str] = None,
) -> List[SpeakerSegment]:
    """Run pyannote.audio diarization on an audio file.

    Args:
        audio_path: Path to WAV audio file.
        num_speakers: Expected number of speakers.
        auth_token: HuggingFace auth token for pyannote models.

    Returns:
        List of SpeakerSegment with timing and speaker labels.
    """
    try:
        from pyannote.audio import Pipeline as PyannotePipeline

        pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=auth_token,
        )

        diarization = pipeline(
            audio_path,
            num_speakers=num_speakers,
        )

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                speaker_label=speaker,
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000),
                confidence=1.0,
            ))

        return segments

    except ImportError:
        raise RuntimeError(
            "pyannote.audio is not installed. "
            "Install it with: pip install pyannote.audio"
        )
    except Exception as e:
        raise RuntimeError(f"Diarization failed: {e}")


def _simple_energy_diarization(
    audio_path: str,
    num_speakers: int,
) -> List[SpeakerSegment]:
    """Fallback diarization using simple energy-based voice activity detection.

    This is a simplified fallback when pyannote is not available.
    It splits audio into voiced segments and assigns speakers round-robin.
    Not recommended for production use.
    """
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_path)
    voiced = detect_nonsilent(audio, min_silence_len=500, silence_thresh=-40)

    segments = []
    speaker_idx = 0
    for start_ms, end_ms in voiced:
        segments.append(SpeakerSegment(
            speaker_label=f"SPEAKER_{speaker_idx:02d}",
            start_ms=start_ms,
            end_ms=end_ms,
            confidence=0.5,
            is_uncertain=True,
        ))
        speaker_idx = (speaker_idx + 1) % num_speakers

    return segments


def separate_chunk(
    chunk_path: str,
    output_dir: str,
    num_speakers: int,
    chunk_index: int = 0,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    auth_token: Optional[str] = None,
    on_progress=None,
) -> SeparationResult:
    """Separate speakers in one audio chunk.

    Runs diarization, extracts per-speaker tracks, generates samples,
    and identifies uncertain segments.

    Args:
        chunk_path: Path to the audio chunk WAV file.
        output_dir: Directory to save separated tracks.
        num_speakers: Expected number of speakers.
        chunk_index: Index of this chunk (for file naming).
        confidence_threshold: Below this, segments are flagged uncertain.
        auth_token: HuggingFace auth token for pyannote.
        on_progress: Optional callback(message, percent).

    Returns:
        SeparationResult with speaker tracks and samples.
    """
    os.makedirs(output_dir, exist_ok=True)

    if on_progress:
        on_progress("Running speaker diarization...", 0.1)

    # Try pyannote first, fall back to simple method
    try:
        segments = run_diarization(chunk_path, num_speakers, auth_token)
    except RuntimeError:
        if on_progress:
            on_progress("pyannote unavailable, using fallback diarization...", 0.1)
        segments = _simple_energy_diarization(chunk_path, num_speakers)

    if on_progress:
        on_progress("Extracting speaker tracks...", 0.4)

    audio = AudioSegment.from_file(chunk_path)

    # Collect unique speaker labels
    labels = sorted(set(seg.speaker_label for seg in segments))

    # Separate confident vs uncertain segments
    confident = [s for s in segments if s.confidence >= confidence_threshold]
    uncertain = [s for s in segments if s.confidence < confidence_threshold]

    # Mark uncertain
    for seg in uncertain:
        seg.is_uncertain = True

    # Build per-speaker audio tracks from confident segments
    speaker_tracks = {}
    speaker_samples = {}

    for label in labels:
        speaker_segs = [s for s in confident if s.speaker_label == label]
        if not speaker_segs:
            continue

        # Concatenate all segments for this speaker
        track = AudioSegment.silent(duration=0)
        for seg in speaker_segs:
            track += audio[seg.start_ms:seg.end_ms]

        # Save full track
        track_path = os.path.join(
            output_dir, f"chunk{chunk_index:03d}_{label}.wav"
        )
        track.export(track_path, format="wav")
        speaker_tracks[label] = track_path

        # Save a sample clip for verification
        sample_ms = SPEAKER_SAMPLE_SECONDS * 1000
        sample = track[:sample_ms] if len(track) > sample_ms else track
        sample_path = os.path.join(
            output_dir, f"chunk{chunk_index:03d}_{label}_sample.wav"
        )
        sample.export(sample_path, format="wav")
        speaker_samples[label] = sample_path

    if on_progress:
        on_progress(
            f"Found {len(labels)} speakers, {len(uncertain)} uncertain segments",
            1.0,
        )

    return SeparationResult(
        chunk_path=chunk_path,
        speaker_segments=confident,
        speaker_labels=labels,
        uncertain_segments=uncertain,
        speaker_tracks=speaker_tracks,
        speaker_samples=speaker_samples,
    )
