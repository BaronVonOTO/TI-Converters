#!/bin/bash
# Double-click on Mac (or run ./run.command). Installs what's missing, then opens the app.
cd "$(dirname "$0")"
pause() { read -p "Press Return to close"; }
if [ "$(uname)" = "Darwin" ]; then
  command -v brew >/dev/null 2>&1 || { echo "Homebrew is needed once. Install it from https://brew.sh, then run this again."; pause; exit 1; }
  for pkg in mono mono-libgdiplus ffmpeg; do brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg"; done
  export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH}"
  xcode-select -p >/dev/null 2>&1 || { echo "Apple's command line tools are needed once. A window will ask to install them. Run this again afterwards."; xcode-select --install; pause; exit 1; }
fi
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is needed (run: xcode-select --install)"; pause; exit 1; }
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt || { echo "Couldn't install Python packages."; pause; exit 1; }
./scripts/build_convimg.sh || { echo "Couldn't build convimg (needs internet, git, make)."; pause; exit 1; }
.venv/bin/python server.py
