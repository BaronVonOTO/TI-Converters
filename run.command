#!/bin/bash
# Double-click on Mac (or run ./run.command). Installs what's missing, then opens the app.
cd "$(dirname "$0")"
if [ "$(uname)" = "Darwin" ]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is needed once. Install it from https://brew.sh, then run this again."; read -p "Press Return to close"; exit 1
  fi
  for pkg in mono mono-libgdiplus ffmpeg; do
    brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"
  done
  export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
fi
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is needed (run: xcode-select --install)"; read -p "Press Return to close"; exit 1; }
python3 server.py
