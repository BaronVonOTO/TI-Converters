"""HD Picture Viewer conversion (port of HDPictureViewerConverter.exe's logic).
Resize -> pad to a multiple of 80 -> 80x80 tiles -> convimg YAML -> convimg (zx0, 'ice' appvars)."""
import math, os, re, shutil, subprocess
from PIL import Image

TILE = 80
BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def valid_id(s):
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]", s or ""))


def next_id(pid):
    """Next 2-character ID (A0, A1 ... A9, AA ... AZ, B0 ...)."""
    n = (ord(pid[0]) - 65) * 36 + BASE36.index(pid[1]) + 1
    if n >= 26 * 36:
        raise ValueError("Ran out of picture IDs.")
    return chr(65 + n // 36) + BASE36[n % 36]


def fit(img, max_w, max_h):
    """Same maths as the original resizeMaintainAspectRatio (fits inside max_w x max_h)."""
    w, h = img.size
    if w == max_w and h == max_h:
        return img
    ratio = w / max_w
    nh, nw = h / ratio, w / ratio
    if nh > max_h:
        ratio = h / max_h
        nh, nw = h / ratio, w / ratio
    return img.resize((math.ceil(nw), math.ceil(nh)), Image.LANCZOS)


def name8(stem):
    s = stem[:8]
    return s + "_" * (8 - len(s))


def pad3(n):
    return "%03d" % n


def convert(image_path, pic_id, resize, out_dir, work_dir, convimg):
    """resize: 0 = keep size, 1 = fit inside 320x240, 2 = exactly 320x240. Returns list of output files."""
    if not valid_id(pic_id):
        raise ValueError("Picture ID must be 2 characters: a capital letter, then a letter or digit (e.g. A1).")
    stem = re.sub(r"[^A-Za-z0-9_]", "_", os.path.splitext(os.path.basename(image_path))[0]) or "PIC"
    if not stem[0].isalpha():
        stem = "P" + stem
    img = Image.open(image_path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")
    if resize == 1:
        img = fit(img, 320, 240)
    elif resize == 2 and img.size != (320, 240):
        img = img.resize((320, 240), Image.LANCZOS)

    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)
    pal = img if max(img.size) <= 2800 else fit(img, 2800, 2800)
    pal.save(os.path.join(work_dir, stem + "Palette.png"))

    hs, vs = math.ceil(img.width / TILE), math.ceil(img.height / TILE)
    full = img
    if (img.width, img.height) != (hs * TILE, vs * TILE):
        full = Image.new("RGB", (hs * TILE, vs * TILE), (0, 0, 0))
        full.paste(img, (0, 0))

    n8 = name8(stem)
    converts, outputs, coords = [], [], ""
    for y in range(vs):
        for x in range(hs):
            coords = pad3(x) + pad3(y)
            png = coords + stem + ".png"
            full.crop((x * TILE, y * TILE, x * TILE + TILE, y * TILE + TILE)).save(os.path.join(work_dir, png))
            nm = pic_id + coords
            converts.append("  - name: %s\n    palette: my_palette\n    images:\n      - %s\n    compress: zx0" % (nm, png))
            outputs.append("  - type: appvar\n    name: %s\n    source-format: ice\n    header-string: HDPICCV4%s\n"
                           "    archived: true\n    converts:\n      - %s" % (nm, n8, nm))
    outputs.append("  - type: appvar\n    name: HP%s0000\n    source-format: ice\n    header-string: HDPALV10%s%s%s\n"
                   "    archived: true\n    palettes:\n      - my_palette" % (pic_id, n8, pic_id, coords))
    yaml = ("palettes:\n  - name: my_palette\n    fixed-entries:\n"
            "      - color: { index: 0,   r: 0,   g: 0,   b: 0}\n"
            "      - color: { index: 255, r: 255, g: 255, b: 255}\n    images:\n      - %sPalette.png\n\n"
            "converts:\n%s\n\noutputs:\n%s\n") % (stem, "\n".join(converts), "\n".join(outputs))
    with open(os.path.join(work_dir, "convimg.yaml"), "w") as f:
        f.write(yaml)
    return run_convimg(work_dir, "convimg.yaml", out_dir, convimg)


def run_convimg(work_dir, yaml_name, out_dir, convimg, only_8xv=True):
    before = set(os.listdir(work_dir))
    r = subprocess.run([os.path.abspath(convimg), "-i", yaml_name], cwd=work_dir, capture_output=True, text=True, timeout=900)
    log = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        raise RuntimeError(log.splitlines()[-1] if log else "convimg failed.")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for f in sorted(set(os.listdir(work_dir)) - before):
        p = os.path.join(work_dir, f)
        if os.path.isfile(p) and f != "convimg.out" and not f.endswith(".lst") and (f.lower().endswith(".8xv") or not only_8xv):
            shutil.copy(p, os.path.join(out_dir, f))
            made.append(f)
    if not made:
        raise RuntimeError(log or "convimg produced no files. Check your YAML.")
    return made
