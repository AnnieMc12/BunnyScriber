"""
Phase 6: Optional LLM cleanup pass.

Sends the reassembled transcript to an LLM to check for
speaker attribution errors based on conversational context.
Flags suspicious segments for user review rather than auto-correcting.
"""

from dataclasses import dataclass
from typing import List, Optional

import requests

from bunnyscriber.reassembler import UnifiedSegment, format_timestamp


@dataclass
class CleanupFlag:
    """A flag raised by the LLM cleanup pass."""

    segment_index: int
    current_speaker: str
    suggested_speaker: Optional[str]
    reason: str
    timestamp: str


CLEANUP_PROMPT = """You are reviewing a multi-speaker transcript for speaker attribution errors.

The transcript was produced by separating speakers from audio and transcribing each separately.
Sometimes the speaker separation makes mistakes — a line attributed to one speaker may actually
belong to another based on conversational context.

Review the transcript below. For each line where the speaker attribution seems WRONG, output a
line in this exact format:
FLAG|<line_number>|<current_speaker>|<suggested_speaker>|<reason>

Only flag lines where you are fairly confident the attribution is wrong. Do not flag lines
where the attribution seems plausible.

If everything looks correct, respond with: NO_FLAGS

TRANSCRIPT:
{transcript_text}
"""


def _build_transcript_text(segments: List[UnifiedSegment]) -> str:
    """Build a numbered transcript for LLM review."""
    lines = []
    for i, seg in enumerate(segments):
        ts = format_timestamp(seg.start)
        speaker = seg.speaker_name
        if seg.is_non_speaker:
            speaker = "[AUDIO CLIP]"
        lines.append(f"{i}: [{ts}] {speaker}: {seg.text}")
    return "\n".join(lines)


def run_cleanup_openai(
    segments: List[UnifiedSegment],
    api_key: str,
    model: str = "gpt-4o-mini",
) -> List[CleanupFlag]:
    """Run LLM cleanup using OpenAI-compatible API.

    Args:
        segments: The unified transcript segments.
        api_key: API key for the LLM service.
        model: Model name to use.

    Returns:
        List of CleanupFlag objects for suspicious segments.
    """
    from openai import OpenAI

    transcript_text = _build_transcript_text(segments)
    prompt = CLEANUP_PROMPT.format(transcript_text=transcript_text)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )

    return _parse_flags(response.choices[0].message.content, segments)


def run_cleanup_generic(
    segments: List[UnifiedSegment],
    endpoint_url: str,
    api_key: str,
    model: str = "default",
) -> List[CleanupFlag]:
    """Run LLM cleanup using a generic OpenAI-compatible endpoint.

    Args:
        segments: The unified transcript segments.
        endpoint_url: Base URL of the API.
        api_key: API key.
        model: Model name.

    Returns:
        List of CleanupFlag objects.
    """
    transcript_text = _build_transcript_text(segments)
    prompt = CLEANUP_PROMPT.format(transcript_text=transcript_text)

    url = endpoint_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return _parse_flags(content, segments)


def _parse_flags(
    llm_output: str,
    segments: List[UnifiedSegment],
) -> List[CleanupFlag]:
    """Parse LLM output into CleanupFlag objects."""
    flags = []

    if "NO_FLAGS" in llm_output:
        return flags

    for line in llm_output.strip().split("\n"):
        line = line.strip()
        if not line.startswith("FLAG|"):
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        try:
            idx = int(parts[1])
            if 0 <= idx < len(segments):
                flags.append(CleanupFlag(
                    segment_index=idx,
                    current_speaker=parts[2],
                    suggested_speaker=parts[3] if parts[3] else None,
                    reason=parts[4],
                    timestamp=format_timestamp(segments[idx].start),
                ))
        except (ValueError, IndexError):
            continue

    return flags
