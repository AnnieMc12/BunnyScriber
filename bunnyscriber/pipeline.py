"""
Pipeline orchestrator for BunnyScriber.

Coordinates all processing phases: chunking, separation, verification,
transcription, reassembly, and optional LLM cleanup.

Runs in a worker thread with signal-based communication to the GUI.
Supports crash recovery by detecting existing intermediate files.
"""

import os
import json
import shutil
import threading
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread

from bunnyscriber.progress import PipelineSignals, ProgressMessage
from bunnyscriber.config import get_work_dir
from bunnyscriber.audio_utils import chunk_audio_file, load_audio
from bunnyscriber.separator import separate_chunk, SeparationResult
from bunnyscriber.transcriber import (
    transcribe_all_tracks,
    save_transcript,
    load_transcript,
    SpeakerTranscript,
)
from bunnyscriber.reassembler import (
    reassemble_transcripts,
    write_txt,
    write_srt,
    write_docx,
    UnifiedSegment,
)
from bunnyscriber.cleanup import run_cleanup_openai, run_cleanup_generic, CleanupFlag
from bunnyscriber.backends.base import TranscriptionBackend


# ── State file for crash recovery ────────────────────────────────────

STATE_FILENAME = "pipeline_state.json"


def _state_path(work_dir: str) -> str:
    return os.path.join(work_dir, STATE_FILENAME)


def _save_state(work_dir: str, state: dict):
    with open(_state_path(work_dir), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _load_state(work_dir: str) -> Optional[dict]:
    path = _state_path(work_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def check_resumable(work_dir: str) -> Optional[dict]:
    """Check if there is a resumable pipeline run in the work directory.

    Returns:
        State dict if resumable, None otherwise.
    """
    state = _load_state(work_dir)
    if state and state.get("status") != "complete":
        return state
    return None


# ── Pipeline Worker Thread ───────────────────────────────────────────


class PipelineWorker(QThread):
    """Worker thread that runs the full BunnyScriber pipeline.

    Communicates with the GUI via PipelineSignals.
    Can be paused at the speaker verification step.
    """

    def __init__(
        self,
        audio_path: str,
        num_speakers: int,
        backend: TranscriptionBackend,
        config: dict,
        signals: PipelineSignals,
        resume_state: Optional[dict] = None,
    ):
        super().__init__()
        self.audio_path = audio_path
        self.num_speakers = num_speakers
        self.backend = backend
        self.config = config
        self.signals = signals
        self.resume_state = resume_state

        self._cancelled = False
        self._verification_event = threading.Event()
        self._speaker_names: Dict[str, str] = {}
        self._non_speaker_labels: set = set()
        self._uncertain_assignments: Dict[int, str] = {}

    def cancel(self):
        """Request cancellation of the pipeline."""
        self._cancelled = True

    def set_verification_result(
        self,
        speaker_names: Dict[str, str],
        non_speaker_labels: set,
        uncertain_assignments: Dict[int, str],
    ):
        """Provide speaker verification results from the GUI.

        Called by the GUI thread after the user completes verification.
        """
        self._speaker_names = speaker_names
        self._non_speaker_labels = non_speaker_labels
        self._uncertain_assignments = uncertain_assignments
        self._verification_event.set()

    def _check_cancel(self):
        if self._cancelled:
            self.signals.cancelled.emit()
            raise _CancelledError()

    def _emit_progress(self, phase: str, message: str, percent: float = 0.0):
        self.signals.progress.emit(ProgressMessage(
            phase=phase,
            message=message,
            percent=percent,
        ))

    def _emit_log(self, msg: str):
        self.signals.log.emit(msg)

    def run(self):
        """Execute the pipeline."""
        try:
            self._run_pipeline()
        except _CancelledError:
            self._emit_log("Pipeline cancelled by user.")
        except Exception as e:
            self.signals.error.emit(str(e))
            self._emit_log(f"Pipeline error: {e}")

    def _run_pipeline(self):
        work_dir = get_work_dir(self.config)
        job_name = os.path.splitext(os.path.basename(self.audio_path))[0]
        job_dir = os.path.join(work_dir, job_name)
        os.makedirs(job_dir, exist_ok=True)

        state = self.resume_state or {
            "status": "starting",
            "job_dir": job_dir,
            "audio_path": self.audio_path,
            "num_speakers": self.num_speakers,
        }

        # ── Phase 1: Chunking ────────────────────────────────────────
        chunks_dir = os.path.join(job_dir, "chunks")

        if state.get("status") in ("starting", None):
            self.signals.phase_changed.emit("chunking")
            self._emit_log("Phase 1: Splitting audio into chunks...")

            chunk_paths = chunk_audio_file(
                self.audio_path,
                chunks_dir,
                on_progress=lambda msg, pct: self._emit_progress("chunking", msg, pct),
            )

            state["chunk_paths"] = chunk_paths
            state["status"] = "chunked"
            _save_state(job_dir, state)
            self._emit_log(f"Split into {len(chunk_paths)} chunks.")
        else:
            chunk_paths = state.get("chunk_paths", [])
            self._emit_log(f"Resuming with {len(chunk_paths)} existing chunks.")

        self._check_cancel()

        # ── Phase 2: Speaker Separation ──────────────────────────────
        separation_dir = os.path.join(job_dir, "separated")

        if state.get("status") in ("chunked",):
            self.signals.phase_changed.emit("separation")
            self._emit_log("Phase 2: Separating speakers...")

            separation_results: List[SeparationResult] = []

            for i, chunk_path in enumerate(chunk_paths):
                self._check_cancel()
                self._emit_progress(
                    "separation",
                    f"Processing chunk {i + 1}/{len(chunk_paths)}...",
                    i / len(chunk_paths),
                )

                result = separate_chunk(
                    chunk_path=chunk_path,
                    output_dir=separation_dir,
                    num_speakers=self.num_speakers,
                    chunk_index=i,
                    auth_token=self.config.get("api_keys", {}).get("huggingface"),
                    on_progress=lambda msg, pct: self._emit_log(f"  {msg}"),
                )
                separation_results.append(result)

            # Serialize separation results for state
            state["separation_results"] = [
                {
                    "chunk_path": r.chunk_path,
                    "speaker_labels": r.speaker_labels,
                    "speaker_tracks": r.speaker_tracks,
                    "speaker_samples": r.speaker_samples,
                    "uncertain_count": len(r.uncertain_segments),
                }
                for r in separation_results
            ]
            state["status"] = "separated"
            _save_state(job_dir, state)
        else:
            separation_results = None  # Will load from state if needed

        self._check_cancel()

        # ── Phase 3: Speaker Verification (GUI interaction) ──────────
        if state.get("status") in ("separated",):
            self.signals.phase_changed.emit("verification")
            self._emit_log("Phase 3: Waiting for speaker verification...")

            # Collect all unique speakers and samples across chunks
            all_samples = {}
            all_uncertain = []

            if separation_results:
                for result in separation_results:
                    all_samples.update(result.speaker_samples)
                    all_uncertain.extend(result.uncertain_segments)
            else:
                # Rebuild from state
                for sr in state.get("separation_results", []):
                    all_samples.update(sr.get("speaker_samples", {}))

            # Signal the GUI to show verification panel
            verification_data = {
                "speaker_samples": all_samples,
                "uncertain_count": len(all_uncertain),
            }
            self.signals.speaker_verification_needed.emit(verification_data)

            # Wait for user to complete verification
            self._verification_event.wait()
            self._check_cancel()

            state["speaker_names"] = self._speaker_names
            state["non_speaker_labels"] = list(self._non_speaker_labels)
            state["status"] = "verified"
            _save_state(job_dir, state)
            self._emit_log("Speaker verification complete.")
        else:
            self._speaker_names = state.get("speaker_names", {})
            self._non_speaker_labels = set(state.get("non_speaker_labels", []))

        self._check_cancel()

        # ── Phase 4: Transcription ───────────────────────────────────
        transcript_dir = os.path.join(job_dir, "transcripts")

        if state.get("status") in ("verified",):
            self.signals.phase_changed.emit("transcription")
            self._emit_log("Phase 4: Transcribing speaker tracks...")

            all_transcripts: List[SpeakerTranscript] = []

            # Get speaker tracks from separation results or state
            if separation_results:
                chunk_tracks = [
                    (i, r.speaker_tracks)
                    for i, r in enumerate(separation_results)
                ]
            else:
                chunk_tracks = [
                    (i, sr.get("speaker_tracks", {}))
                    for i, sr in enumerate(state.get("separation_results", []))
                ]

            total_chunks = len(chunk_tracks)
            for idx, (chunk_i, tracks) in enumerate(chunk_tracks):
                self._check_cancel()
                self._emit_progress(
                    "transcription",
                    f"Transcribing chunk {idx + 1}/{total_chunks}...",
                    idx / total_chunks,
                )

                # Skip non-speaker tracks
                tracks_filtered = {
                    label: path
                    for label, path in tracks.items()
                    if label not in self._non_speaker_labels
                }

                transcripts = transcribe_all_tracks(
                    speaker_tracks=tracks_filtered,
                    speaker_names=self._speaker_names,
                    chunk_index=chunk_i,
                    backend=self.backend,
                    on_progress=lambda msg, pct: self._emit_log(f"  {msg}"),
                )

                # Save individual transcripts
                for t in transcripts:
                    save_transcript(t, transcript_dir)

                all_transcripts.extend(transcripts)

            state["status"] = "transcribed"
            _save_state(job_dir, state)
            self._emit_log(f"Transcribed {len(all_transcripts)} speaker tracks.")
        else:
            # Resume: reload saved transcripts from the transcripts directory
            all_transcripts = []
            if os.path.isdir(transcript_dir):
                for fname in sorted(os.listdir(transcript_dir)):
                    if fname.endswith("_transcript.txt"):
                        fpath = os.path.join(transcript_dir, fname)
                        try:
                            t = load_transcript(fpath)
                            all_transcripts.append(t)
                        except Exception as e:
                            self._emit_log(f"Warning: could not reload {fname}: {e}")
                self._emit_log(f"Reloaded {len(all_transcripts)} transcripts from disk.")

        self._check_cancel()

        # ── Phase 5: Reassembly ──────────────────────────────────────
        self.signals.phase_changed.emit("reassembly")
        self._emit_log("Phase 5: Assembling unified transcript...")

        # Calculate chunk time offsets
        chunk_offsets = {}
        offset = 0.0
        for i, chunk_path in enumerate(chunk_paths):
            chunk_offsets[i] = offset
            try:
                audio = load_audio(chunk_path)
                offset += len(audio) / 1000.0
            except Exception:
                pass

        unified = reassemble_transcripts(
            transcripts=all_transcripts,
            non_speaker_labels=self._non_speaker_labels,
            chunk_offsets=chunk_offsets,
        )

        # Write output files
        output_format = self.config.get("output_format", "txt")
        output_base = os.path.join(
            os.path.dirname(self.audio_path),
            f"{job_name}_transcript",
        )

        output_path = f"{output_base}.txt"
        write_txt(unified, output_path, title=f"Transcript: {job_name}")
        self._emit_log(f"Wrote: {output_path}")

        if output_format == "srt":
            srt_path = f"{output_base}.srt"
            write_srt(unified, srt_path)
            self._emit_log(f"Wrote: {srt_path}")

        if output_format == "docx":
            docx_path = f"{output_base}.docx"
            write_docx(unified, docx_path, title=f"Transcript: {job_name}")
            self._emit_log(f"Wrote: {docx_path}")

        self._emit_progress("reassembly", "Transcript assembled.", 1.0)

        # ── Phase 6: Optional LLM Cleanup ────────────────────────────
        cleanup_flags: List[CleanupFlag] = []

        if self.config.get("llm_cleanup_enabled"):
            self.signals.phase_changed.emit("cleanup")
            self._emit_log("Phase 6: Running LLM cleanup pass...")

            try:
                cleanup_key = self.config.get("llm_cleanup_api_key", "")
                cleanup_backend = self.config.get("llm_cleanup_backend", "openai")

                if cleanup_backend == "openai":
                    cleanup_flags = run_cleanup_openai(unified, cleanup_key)
                else:
                    cleanup_flags = run_cleanup_generic(
                        unified,
                        endpoint_url=cleanup_backend,
                        api_key=cleanup_key,
                    )

                if cleanup_flags:
                    self._emit_log(
                        f"LLM flagged {len(cleanup_flags)} potential attribution errors."
                    )
                    # Write flags to a review file
                    flags_path = f"{output_base}_review_flags.txt"
                    with open(flags_path, "w", encoding="utf-8") as f:
                        f.write("BunnyScriber LLM Cleanup Flags\n")
                        f.write("=" * 40 + "\n\n")
                        for flag in cleanup_flags:
                            f.write(
                                f"[{flag.timestamp}] Line {flag.segment_index}: "
                                f"Currently '{flag.current_speaker}', "
                                f"suggested '{flag.suggested_speaker}'\n"
                                f"  Reason: {flag.reason}\n\n"
                            )
                    self._emit_log(f"Wrote review flags: {flags_path}")
                else:
                    self._emit_log("LLM cleanup found no attribution issues.")

            except Exception as e:
                self._emit_log(f"LLM cleanup failed (non-fatal): {e}")

        # ── Finish ───────────────────────────────────────────────────
        state["status"] = "complete"
        _save_state(job_dir, state)

        # Optionally clean up intermediate files
        if self.config.get("auto_delete_intermediates"):
            for subdir in ("chunks", "separated", "transcripts"):
                path = os.path.join(job_dir, subdir)
                if os.path.exists(path):
                    shutil.rmtree(path)
            self._emit_log("Cleaned up intermediate files.")

        self.signals.finished.emit(output_path)
        self._emit_log("Pipeline complete!")


class _CancelledError(Exception):
    """Raised when the pipeline is cancelled."""
    pass
