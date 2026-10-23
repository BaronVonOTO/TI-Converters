#!/usr/bin/env python3
"""TI-CREATE web UI: tiny local server that drives bin/tcli.exe (Mono)."""
import hd, io, json, os, re, shutil, subprocess, sys, tempfile, threading, uuid, webbrowser, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "bin", "tcli.exe")
CONVIMG = os.path.join(ROOT, "bin", "convimg")
JOBS = os.path.join(tempfile.gettempdir(), "ti-create-jobs")
LOCK = threading.Lock()  # tcli uses shared scratch folders, so run one conversion at a time
FORMATS = {"rgb16", "rgb16_32k", "rgb16_16k", "rgb16_8k", "rgb16_4k", "rgb16_2k", "rgb8", "rgb8_32k",
           "rgb8_16k", "rgb8_8k", "rgb8_4k", "rgb8_2k", "1bpp", "txt"}
os.makedirs(JOBS, exist_ok=True)


def safe(name):
    name = os.path.basename(unquote(name))
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "file"


def jobdir(job):
    if not re.fullmatch(r"[0-9a-f]{12}", job or ""):
        raise ValueError("bad job id")
    return os.path.join(JOBS, job)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        try:
            if not parts:
                with open(os.path.join(ROOT, "web", "index.html"), "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8")
            if parts[0] == "files" and len(parts) == 3:
                p = os.path.join(jobdir(parts[1]), "out", safe(parts[2]))
                if not os.path.isfile(p):
                    return self.send(404, {"error": "not found"})
                with open(p, "rb") as f:
                    return self.send(200, f.read(), "application/octet-stream",
                                     {"Content-Disposition": 'attachment; filename="%s"' % safe(parts[2])})
            if parts[0] == "zip" and len(parts) == 2:
                out = os.path.join(jobdir(parts[1]), "out")
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for f in sorted(os.listdir(out)):
                        z.write(os.path.join(out, f), f)
                return self.send(200, buf.getvalue(), "application/zip",
                                 {"Content-Disposition": 'attachment; filename="ti-create-output.zip"'})
        except Exception as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            n = int(self.headers.get("Content-Length", 0))
            if u.path == "/upload":
                job = (q.get("job") or [uuid.uuid4().hex[:12]])[0]
                d = os.path.join(jobdir(job), "in")
                os.makedirs(d, exist_ok=True)
                name = safe((q.get("name") or ["file"])[0])
                with open(os.path.join(d, name), "wb") as f:
                    left = n
                    while left > 0:
                        chunk = self.rfile.read(min(1 << 20, left))
                        if not chunk:
                            break
                        f.write(chunk)
                        left -= len(chunk)
                return self.send(200, {"job": job, "name": name})
            if u.path == "/convert":
                req = json.loads(self.rfile.read(n) or b"{}")
                job = req["job"]
                base = jobdir(job)
                inp, out = os.path.join(base, "in"), os.path.join(base, "out")
                files = sorted(os.listdir(inp))
                shutil.rmtree(out, ignore_errors=True)
                if not files:
                    return self.send(400, {"error": "No files were uploaded."})
                if req.get("mode") in ("hd", "convimg"):
                    if not os.path.isfile(CONVIMG):
                        return self.send(500, {"error": "convimg isn't built yet. Run ./run.command (or scripts/build_convimg.sh)."})
                    os.makedirs(out, exist_ok=True)
                    if req["mode"] == "hd":
                        pid = str(req.get("id", "A1")).upper()
                        if not hd.valid_id(pid):
                            return self.send(400, {"error": "Picture ID must be a capital letter then a letter or digit, like A1."})
                        for f in files:
                            hd.convert(os.path.join(inp, f), pid, int(req.get("resize", 0)), out,
                                       os.path.join(base, "work_" + pid), CONVIMG)
                            pid = hd.next_id(pid)
                    else:
                        ym = [f for f in files if f.lower().endswith((".yaml", ".yml"))]
                        if len(ym) != 1:
                            return self.send(400, {"error": "Add exactly one convimg .yaml file along with the images it uses."})
                        work = os.path.join(base, "work")
                        shutil.rmtree(work, ignore_errors=True)
                        shutil.copytree(inp, work)
                        hd.run_convimg(work, ym[0], out, CONVIMG, only_8xv=False)
                    made = sorted(os.listdir(out))
                    return self.send(200, {"job": job, "files": [
                        {"name": f, "size": os.path.getsize(os.path.join(out, f)),
                         "url": "/files/%s/%s" % (job, f)} for f in made]})
                if req.get("mode") == "video":
                    name = re.sub(r"[^A-Z0-9]", "", str(req.get("name", "VIDEO")).upper())[:6] or "VIDEO"
                    if name[0].isdigit():
                        name = "V" + name[1:]
                    cmd = ["mono", BIN, "video", out, os.path.join(inp, files[0]), name,
                           str(int(req.get("fps", 10))), str(int(req.get("maxdif", 80))),
                           str(int(req.get("rle", 10)))]
                else:
                    fmt = req.get("format", "rgb16")
                    if fmt not in FORMATS:
                        return self.send(400, {"error": "Unknown format."})
                    cmd = ["mono", BIN, "image", fmt, out] + [os.path.join(inp, f) for f in files]
                with LOCK:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                log = (r.stdout + r.stderr).strip()
                made = sorted(os.listdir(out)) if os.path.isdir(out) else []
                if r.returncode != 0 or not made:
                    msg = log.splitlines()[-1] if log else "Conversion failed."
                    return self.send(500, {"error": msg, "log": log[-2000:]})
                return self.send(200, {"job": job, "files": [
                    {"name": f, "size": os.path.getsize(os.path.join(out, f)),
                     "url": "/files/%s/%s" % (job, f)} for f in made]})
        except FileNotFoundError:
            return self.send(500, {"error": "A required tool is missing (Mono or convimg). Run ./run.command once to set it up."})
        except (ValueError, RuntimeError) as e:
            return self.send(400, {"error": str(e)})
        except Exception as e:
            return self.send(500, {"error": str(e)})
        self.send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("CODESPACES") else "127.0.0.1"
    srv = ThreadingHTTPServer((host, port), H)
    url = "http://localhost:%d" % port
    print("TI-CREATE running at", url, "(Ctrl+C to quit)")
    if not os.environ.get("CODESPACES") and "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
