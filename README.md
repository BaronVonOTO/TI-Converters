# TI-CREATE

A simple web page for making TI-84 CE files. Four tools in one place:

| Tab | What it does | Engine |
|---|---|---|
| Images | TI-CREATE image appvars (rgb16, rgb8, 1bpp, txt, size caps) | original TI-CREATE code (Mono) |
| Video | TI-CREATE video appvars | original TI-CREATE code + ffmpeg |
| HD picture | HD Picture Viewer tiles + palette (`HDPICCV4` / `HDPALV10`) | `convimg` v9.3 |
| convimg | Run your own convimg `.yaml` with its images | `convimg` v9.3 |

## Run it
**Mac:** click **Code, Download ZIP**, unzip, double-click **run.command** (right-click, Open if blocked).
First run installs Mono, ffmpeg and builds convimg (needs [Homebrew](https://brew.sh); a few minutes).
**No install:** click **Code, Codespaces, Create codespace**. It opens in your browser.
**Landing page:** in repo Settings, Pages, deploy from branch `main`, folder `/docs`. It gives friends one-click buttons.

Send every `.8xv` file to the calculator with TI Connect CE (include the index/palette files).

## Maintaining it
- `server.py` is the whole backend, `web/index.html` the whole UI, `hd.py` the HD Picture logic.
- convimg is built from the pinned tag in `scripts/build_convimg.sh` (BSD-licensed). Change the tag to upgrade.
- `bin/TICREATE_mac.exe` is the original TI-CREATE engine with Windows paths patched; `bin/tcli.exe` is the command-line wrapper.
  Only publish this repo if you have the right to share that program.
