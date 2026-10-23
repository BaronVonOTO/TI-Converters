// TI-CREATE web engine: HD Picture Viewer logic + convimg (WebAssembly) runner + zip.
// Pure ES module, no DOM access, so it runs in the browser and in Node tests.
import { WASI, File, OpenFile, ConsoleStdout, PreopenDirectory } from "./vendor/wasi/index.js";

const TILE = 80;
const B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const enc = new TextEncoder();

export const validId = (s) => /^[A-Z][A-Z0-9]$/.test(s || "");

export function nextId(id) {
  const n = (id.charCodeAt(0) - 65) * 36 + B36.indexOf(id[1]) + 1;
  if (n >= 26 * 36) throw new Error("Ran out of picture IDs.");
  return String.fromCharCode(65 + Math.floor(n / 36)) + B36[n % 36];
}

// Same maths as the original app: fit inside maxW x maxH.
export function fitSize(w, h, maxW, maxH) {
  if (w === maxW && h === maxH) return [w, h];
  let ratio = w / maxW, nh = h / ratio, nw = w / ratio;
  if (nh > maxH) { ratio = h / maxH; nh = h / ratio; nw = w / ratio; }
  return [Math.ceil(nw), Math.ceil(nh)];
}

const pad3 = (n) => String(n).padStart(3, "0");
const name8 = (s) => s.slice(0, 8).padEnd(8, "_");

export function cleanStem(filename) {
  let stem = filename.replace(/\.[^.]*$/, "").replace(/[^A-Za-z0-9_]/g, "_") || "PIC";
  if (!/^[A-Za-z]/.test(stem)) stem = "P" + stem;
  return stem;
}

/** Draw `src` (anything drawImage accepts) scaled to w x h, over black, onto a new canvas. */
function scaled(cv, src, sw, sh, w, h) {
  const c = cv.create(w, h), g = c.getContext("2d");
  g.fillStyle = "#000"; g.fillRect(0, 0, w, h);
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(src, 0, 0, sw, sh, 0, 0, w, h);
  return c;
}

/**
 * Build the convimg job for one picture.
 * cv: { create(w,h) -> canvas, toPNG(canvas) -> Promise<Uint8Array> }
 * Returns the files (PNG tiles, palette PNG, convimg.yaml) ready for runConvimg.
 */
export async function hdJob(cv, source, sw, sh, filename, picId, resize) {
  if (!validId(picId)) throw new Error("Picture ID must be a capital letter then a letter or digit, like A1.");
  const stem = cleanStem(filename);
  let [w, h] = [sw, sh];
  if (resize === 1) [w, h] = fitSize(sw, sh, 320, 240);
  else if (resize === 2) [w, h] = [320, 240];
  const img = scaled(cv, source, sw, sh, w, h);

  const files = [];
  const [pw, ph] = Math.max(w, h) > 2800 ? fitSize(w, h, 2800, 2800) : [w, h];
  const pal = pw === w && ph === h ? img : scaled(cv, img, w, h, pw, ph);
  files.push({ name: stem + "Palette.png", data: await cv.toPNG(pal) });

  const hs = Math.ceil(w / TILE), vs = Math.ceil(h / TILE);
  const full = cv.create(hs * TILE, vs * TILE), fg = full.getContext("2d");
  fg.fillStyle = "#000"; fg.fillRect(0, 0, hs * TILE, vs * TILE);
  fg.drawImage(img, 0, 0);

  const n8 = name8(stem), converts = [], outputs = [];
  let coords = "";
  for (let y = 0; y < vs; y++) for (let x = 0; x < hs; x++) {
    coords = pad3(x) + pad3(y);
    const png = coords + stem + ".png", nm = picId + coords;
    const t = cv.create(TILE, TILE);
    t.getContext("2d").drawImage(full, x * TILE, y * TILE, TILE, TILE, 0, 0, TILE, TILE);
    files.push({ name: png, data: await cv.toPNG(t) });
    converts.push(`  - name: ${nm}\n    palette: my_palette\n    images:\n      - ${png}\n    compress: zx0`);
    outputs.push(`  - type: appvar\n    name: ${nm}\n    source-format: ice\n    header-string: HDPICCV4${n8}\n    archived: true\n    converts:\n      - ${nm}`);
  }
  outputs.push(`  - type: appvar\n    name: HP${picId}0000\n    source-format: ice\n    header-string: HDPALV10${n8}${picId}${coords}\n    archived: true\n    palettes:\n      - my_palette`);
  const yaml = `palettes:\n  - name: my_palette\n    fixed-entries:\n      - color: { index: 0,   r: 0,   g: 0,   b: 0}\n      - color: { index: 255, r: 255, g: 255, b: 255}\n    images:\n      - ${stem}Palette.png\n\nconverts:\n${converts.join("\n")}\n\noutputs:\n${outputs.join("\n")}\n`;
  files.push({ name: "convimg.yaml", data: enc.encode(yaml) });
  return { files, yamlName: "convimg.yaml" };
}

let modulePromise = null;
/** wasmSource: URL string (browser) or bytes (Node). */
export function loadConvimg(wasmSource) {
  if (!modulePromise) {
    modulePromise = typeof wasmSource === "string"
      ? WebAssembly.compileStreaming(fetch(wasmSource)).catch(async () => WebAssembly.compile(await (await fetch(wasmSource)).arrayBuffer()))
      : WebAssembly.compile(wasmSource);
  }
  return modulePromise;
}

/** Run convimg on in-memory files. Returns { outputs: [{name,data}], log }. */
export async function runConvimg(wasmSource, files, yamlName, { onlyAppvars = true } = {}) {
  const mod = await loadConvimg(wasmSource);
  const dir = new Map(files.map((f) => [f.name, new File(f.data)]));
  const before = new Set(dir.keys()), log = [];
  const out = ConsoleStdout.lineBuffered((m) => log.push(m.replace(/\x1b\[[0-9;]*m/g, "")));
  const wasi = new WASI(["convimg", "-i", yamlName], [],
    [new OpenFile(new File([])), out, out, new PreopenDirectory(".", dir)], { debug: false });
  const inst = await WebAssembly.instantiate(mod, { wasi_snapshot_preview1: wasi.wasiImport });
  let code;
  try { code = wasi.start(inst); } catch (e) { throw new Error("convimg stopped unexpectedly: " + e.message); }
  const text = log.join("\n");
  if (code !== 0) {
    const errs = log.filter((l) => /error/i.test(l));
    throw new Error((errs[errs.length - 1] || log[log.length - 1] || "convimg failed.").replace(/^\[\w+\]\s*/, ""));
  }
  const outputs = [];
  for (const [name, f] of dir) {
    if (before.has(name) || name === "convimg.out" || name.endsWith(".lst")) continue;
    if (onlyAppvars && !/\.8xv$/i.test(name)) continue;
    outputs.push({ name, data: f.data });
  }
  if (!outputs.length) throw new Error(text || "convimg produced no files. Check your YAML.");
  return { outputs: outputs.sort((a, b) => a.name.localeCompare(b.name)), log: text };
}

// ---- minimal zip (store only) ----
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = (d) => { let c = ~0; for (let i = 0; i < d.length; i++) c = CRC[(c ^ d[i]) & 255] ^ (c >>> 8); return ~c >>> 0; };
export function zip(files) {
  const parts = [], central = []; let off = 0;
  for (const f of files) {
    const nm = enc.encode(f.name), crc = crc32(f.data), sz = f.data.length;
    const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, sz, true); lh.setUint32(22, sz, true); lh.setUint16(26, nm.length, true);
    parts.push(new Uint8Array(lh.buffer), nm, f.data);
    const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true);
    ch.setUint32(16, crc, true); ch.setUint32(20, sz, true); ch.setUint32(24, sz, true); ch.setUint16(28, nm.length, true); ch.setUint32(42, off, true);
    central.push(new Uint8Array(ch.buffer), nm);
    off += 30 + nm.length + sz;
  }
  const csz = central.reduce((a, b) => a + b.length, 0);
  const end = new DataView(new ArrayBuffer(22)); end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, csz, true); end.setUint32(16, off, true);
  return new Blob([...parts, ...central, new Uint8Array(end.buffer)], { type: "application/zip" });
}
