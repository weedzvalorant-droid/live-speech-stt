#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Live Speech STT: installation (macOS) ==="

PYBIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYBIN="$candidate"
        break
    fi
done

if [ -z "$PYBIN" ]; then
    echo "[ERROR] No Python 3.10-3.12 found. Install it from python.org or 'brew install python@3.11'."
    exit 1
fi

echo "Using interpreter: $PYBIN ($($PYBIN --version))"

if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    "$PYBIN" -m venv venv
fi

source venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing dependencies (this can take a few minutes, especially the first time)..."
if ! pip install -r requirements.txt; then
    echo
    echo "[ERROR] Failed to install dependencies."
    echo "If PyAudio failed to build, install PortAudio first: brew install portaudio"
    echo "then re-run this script."
    exit 1
fi

echo
echo "=== Installation complete ==="
echo "Next: install BlackHole (https://existential.audio/blackhole/) if you haven't yet"
echo "      (see README.md 'macOS' section for the one-time setup), then run: ./run.sh"
