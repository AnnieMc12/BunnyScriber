# BunnyScriber

```
       /)  /)
      ( ^.^ )    BunnyScriber
      (")_(")    Accurate Speaker-Attributed Transcripts
```

**BunnyScriber** is a desktop application that produces accurate, speaker-attributed transcripts of multi-speaker audio files — podcasts, interviews, panel discussions, and more.

## The Problem with Conventional Diarization

Most transcription tools try to figure out *what was said* and *who said it* simultaneously. This approach (speaker diarization) is notoriously unreliable, especially with crosstalk, similar-sounding speakers, or noisy audio.

## BunnyScriber's Approach

Instead of asking one model to do everything at once, BunnyScriber uses a multi-phase pipeline:

1. **Split** — Divide the audio into manageable chunks at natural silence points
2. **Separate** — Use speaker diarization to identify and extract per-speaker audio tracks
3. **Verify** — You listen to a short sample of each speaker and assign names (takes ~30 seconds)
4. **Transcribe** — Each speaker's track is transcribed independently using your choice of backend
5. **Reassemble** — All transcripts are merged into a single unified document with speaker labels and timestamps
6. **Cleanup** (optional) — An LLM reviews the transcript for attribution errors

The result: a clean transcript where you know exactly who said what.

## Installation

### From Source

```bash
git clone https://github.com/AnnieMc12/BunnyScriber.git
cd BunnyScriber
pip install -r requirements.txt
python run.py
```

### From a Packaged Release

Download the latest release from the [Releases](https://github.com/AnnieMc12/BunnyScriber/releases) page and run `BunnyScriber.exe` (Windows) or the equivalent for your platform.

### Building from Source with PyInstaller

```bash
pip install pyinstaller
pyinstaller bunnyscriber.spec
```

The packaged app will be in `dist/BunnyScriber/`.

## Transcription Backends

BunnyScriber supports multiple transcription backends. You choose one during the first-run setup, and can change it anytime in Settings.

### Built-in Backends

| Backend | Type | Requirements |
|---------|------|-------------|
| **OpenAI Whisper API** | Cloud | OpenAI API key |
| **Groq Whisper API** | Cloud | Groq API key (fast inference) |
| **Mistral API** | Cloud | Mistral API key |
| **Local Whisper** | Local | GPU recommended; model downloaded on first use |

### Local Whisper Model Sizes

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| tiny | ~1 GB | Fastest | Low |
| base | ~1 GB | Fast | Fair |
| small | ~2 GB | Moderate | Good |
| medium | ~5 GB | Slow | Great |
| large | ~10 GB | Slowest | Best |

Models are **not bundled** with the app. When you select Local Whisper, you'll be prompted to download the model you want. The base install is lightweight (GUI + pipeline logic + API integration only).

### Custom Endpoints

You can add any OpenAI-compatible transcription API via **Settings > Add Custom Endpoint**. Provide:

- A display name
- The endpoint URL
- An API key
- The model name (defaults to `whisper-1`)

This future-proofs the app against new services without requiring updates.

## Speaker Separation

BunnyScriber uses [pyannote.audio](https://github.com/pyannote/pyannote-audio) for speaker diarization. This requires:

- A HuggingFace account
- Accepting the pyannote model terms on HuggingFace
- A HuggingFace auth token (enter in Settings)

If pyannote is not available, a simple energy-based fallback is used (lower quality).

## Supported Audio Formats

MP3, WAV, FLAC, M4A, OGG, WMA, AAC

Requires [FFmpeg](https://ffmpeg.org/) installed on your system for format conversion.

## Output Formats

- **Plain text** (`.txt`) — default
- **Subtitles** (`.srt`) — for video use
- **Word document** (`.docx`) — formatted with speaker labels

## Crash Recovery

All intermediate files (chunks, separated tracks, individual transcripts) are saved to a working directory. If the app closes mid-process, it will offer to resume from where it left off on next launch.

You can configure auto-deletion of intermediate files in Settings.

## Dependencies

- Python 3.10+
- PyQt6 (GUI)
- pydub + FFmpeg (audio processing)
- pyannote.audio (speaker diarization)
- torch + torchaudio (ML backend)
- openai-whisper (optional, for local transcription)
- openai (for OpenAI API backend)
- requests (for API backends)
- python-docx (for .docx output)
- Pillow (for bunny image generation)

### GPU Notes

- Local Whisper benefits significantly from a CUDA-capable GPU
- The `large` model requires ~10 GB VRAM
- CPU-only inference works but is much slower
- pyannote.audio also benefits from GPU acceleration

## Configuration

Settings are stored in `~/.bunnyscriber_config.json`. This file contains your API keys and preferences — it is listed in `.gitignore` and should never be committed to version control.

## Project Structure

```
BunnyScriber/
|-- run.py                    # Entry point
|-- requirements.txt          # Dependencies
|-- bunnyscriber.spec         # PyInstaller packaging
|-- generate_bunny_images.py  # Bunny artwork generator
|-- pics/                     # Bunny emoji images
|-- bunnyscriber/
    |-- __init__.py
    |-- app.py                # Main GUI (window, wizard, settings, dialogs)
    |-- constants.py          # Colors, messages, configuration
    |-- config.py             # Settings persistence
    |-- progress.py           # Thread-safe progress signaling
    |-- audio_utils.py        # Audio loading, chunking, format handling
    |-- pipeline.py           # Pipeline orchestrator (runs in worker thread)
    |-- separator.py          # Phase 2: Speaker separation/diarization
    |-- transcriber.py        # Phase 4: Per-speaker transcription
    |-- reassembler.py        # Phase 5: Transcript merging and output
    |-- cleanup.py            # Phase 6: Optional LLM cleanup pass
    |-- backends/
        |-- __init__.py
        |-- base.py           # Abstract backend interface
        |-- whisper_local.py  # Local Whisper adapter
        |-- openai_api.py     # OpenAI Whisper API adapter
        |-- groq_api.py       # Groq Whisper API adapter
        |-- mistral_api.py    # Mistral API adapter
        |-- custom.py         # Custom endpoint adapter
```

## License

This project is provided as-is for personal use.

---

*Made with love and carrots*
