#!/usr/bin/env bash
# Linux launcher for BunnyScriber — mirrors launch.bat.
# Creates a venv on first run, installs deps (CPU-only torch if no NVIDIA GPU),
# then starts the app.
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if command -v nvidia-smi >/dev/null 2>&1; then
        .venv/bin/pip install "torch>=2.0,<2.5" "torchaudio>=2.0,<2.5"
    else
        echo "No NVIDIA GPU detected — installing CPU-only torch (much smaller)."
        .venv/bin/pip install "torch>=2.0,<2.5" "torchaudio>=2.0,<2.5" \
            --index-url https://download.pytorch.org/whl/cpu
    fi
    .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python run.py
