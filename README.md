# TI-CREATE

Turn pictures and video into `.8xv` files for the TI-84 CE, from a simple web page.
Runs on a Mac with one double-click, or in your browser with GitHub Codespaces.

## Option A: run on your Mac
1. Click **Code → Download ZIP** and unzip it.
2. Double-click **run.command**. If macOS blocks it, right-click → Open.
   The first run installs Mono and ffmpeg with Homebrew (needs [Homebrew](https://brew.sh)).
3. Your browser opens the app. Drop in images or a video, press **Convert**.

## Option B: nothing to install (GitHub Codespaces)
Click **Code → Codespaces → Create codespace**. It sets everything up and opens the app in a browser tab
(first build takes a few minutes). Download your files from the page.

## Notes
- Send all downloaded `.8xv` files to the calculator with TI Connect CE, including the index file.
- `bin/TICREATE_mac.exe` is the original conversion engine with Windows paths patched for Mac/Linux.
  Only publish this repo if you have the right to share that program.
