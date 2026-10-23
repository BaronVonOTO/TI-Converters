# TI-CREATE

Make TI-84 CE picture files in your browser. Nothing to install, nothing uploaded.

**Use it:** open this repo's GitHub Pages site (see "Publish" below).

## What the web page does
| Tab | What it does |
|---|---|
| HD picture | Resizes pictures, cuts them into 80x80 tiles and builds the `HDPICCV4` picture files plus an `HP...` palette file for the HD Picture Viewer |
| convimg | Runs your own convimg `.yaml` (plus the images it uses) |

Both run the real [convimg](https://github.com/mateoconlechuga/convimg) v9.3 (BSD licence), compiled to WebAssembly, so the output matches the desktop tool.
Send every `.8xv` file to your calculator with TI Connect CE.

## Publish (one time, about a minute)
1. Put this folder's contents in a GitHub repository.
2. Repo **Settings, Pages**: deploy from branch `main`, folder `/docs`.
3. Share the link GitHub shows you.

## Maintain
- The whole site is the `docs/` folder: `index.html` (page), `engine.js` (HD logic, convimg runner, zip), `convimg.wasm`, `vendor/wasi/` (browser WASI shim, MIT/Apache).
- No build step. Edit and push. To preview locally: `python3 -m http.server -d docs`, then open http://localhost:8000.
- To upgrade or rebuild convimg: `scripts/build_wasm.sh` (needs clang, lld, wasi-libc; see the script header).

## Also in this repo: desktop version (TI-CREATE images and video)
TI-CREATE's own image and video converters can't run inside a web page yet. They are available as a local web app:
double-click `run.command` on a Mac, or open the repo in a GitHub Codespace. It also includes the same HD picture and convimg tools.
`bin/TICREATE_mac.exe` is the original TI-CREATE engine with Windows paths patched. Only publish this repo if you have the right to share it.
