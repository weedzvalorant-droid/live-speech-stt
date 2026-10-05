#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

source venv/bin/activate

echo "Building LiveSpeechSTT.app with PyInstaller..."
pyinstaller --name LiveSpeechSTT --windowed --onedir --noconfirm \
    --icon=assets/icon.icns \
    --add-data "assets:assets" \
    --collect-all faster_whisper \
    --collect-all ctranslate2 \
    --hidden-import=webrtcvad \
    main.py

echo
echo "=== Build complete ==="
echo "App bundle: dist/LiveSpeechSTT.app"
echo "Drag it into /Applications, or zip dist/LiveSpeechSTT.app to share via USB/AirDrop."
