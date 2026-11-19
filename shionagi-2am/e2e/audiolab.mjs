// There are no ears in this pipeline, so: play every sound in the real page,
// record the final mix, and write (a) a spectrogram to look at, (b) level
// numbers per sound, (c) a WAV a person can listen to.
//   node e2e/audiolab.mjs <outDir>
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const outDir = process.argv[2] ?? "audio-out";
const mode = process.argv[3] ?? "mix"; // "dry" leaves the rain and wind out, to measure each sound alone
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`${BASE}/?autostart&nolock&tts=0`);
await page.waitForFunction(() => window.__shio && window.__shio.mode === "play");
await page.waitForTimeout(400);

const result = await page.evaluate(async (mode) => {
  const api = window.__shio;
  const { audio, sim } = api;
  const ctx = audio.context;
  if (!ctx) return { error: "no AudioContext" };
  await ctx.resume();
  api.setSpeed(0); // freeze the simulation: only what we trigger is heard
  for (const e of sim.s.enemies) e.mode = "dormant";
  // the engine's own schedulers stay out of the catalogue
  audio.radioT = 1e9;
  audio.creakT = 1e9;
  audio.sirenT = 1e9;
  api.view.hooks.thunder = undefined;
  api.view.hooks.rattle = undefined;
  if (mode === "dry") audio.amb.disconnect();

  // --- recorder
  const sp = ctx.createScriptProcessor(4096, 2, 2);
  const chunksL = [];
  const chunksR = [];
  sp.onaudioprocess = (e) => {
    chunksL.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    chunksR.push(new Float32Array(e.inputBuffer.getChannelData(1)));
  };
  const mute = ctx.createGain();
  mute.gain.value = 0;
  audio.output.connect(sp);
  sp.connect(mute);
  mute.connect(ctx.destination);
  const t0 = ctx.currentTime;
  const marks = [];
  const mark = (name) => marks.push({ name, t: ctx.currentTime - t0 });
  const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));
  const ev = (e) => audio.onEvent(e, sim);
  const place = async (x, z, yaw) => {
    api.teleport(x, z, yaw);
    await sleep(0.05);
  };

  // --- catalogue
  await place(-8.5, -2.2, -1.12);
  mark("室内の雨（ターミナル）");
  await sleep(3);
  mark("足音: タイル×4");
  for (let i = 0; i < 4; i++) {
    ev({ t: "step", x: 0, z: 0, surface: "tile", run: false });
    await sleep(0.5);
  }
  mark("扉");
  ev({ t: "door", id: "D1", x: -6.5, z: -3.2 });
  await sleep(1.6);
  mark("自動ドア（開かない）");
  ev({ t: "locked", id: "frontDoor", x: -7, z: -4 });
  await sleep(1.0);
  mark("ガラス越しの気配（壁越し）");
  ev({ t: "cue", id: "glass", x: 6.8, z: -16.3 });
  for (let i = 0; i < 4; i++) {
    ev({ t: "estep", id: "P1", x: 2 - i, z: -16.3, surface: "asphalt", fast: false });
    await sleep(0.9);
  }
  ev({ t: "vocal", id: "P1", x: -2, z: -16.3, kind: "idle" });
  await sleep(2.4);

  await place(3, -60, 0);
  mark("屋外の雨（商店街・浸水）");
  await sleep(4);
  mark("足音: 水×4（歩き）");
  for (let i = 0; i < 4; i++) {
    ev({ t: "step", x: 3, z: -60, surface: "water", run: false });
    await sleep(0.5);
  }
  mark("足音: 水×4（走り）");
  for (let i = 0; i < 4; i++) {
    ev({ t: "step", x: 3, z: -60, surface: "water", run: true });
    await sleep(0.32);
  }
  for (const d of [4, 8, 16, 28]) {
    mark(`敵の足音: 水 ${d}m×3`);
    for (let i = 0; i < 3; i++) {
      ev({ t: "estep", id: "E3", x: 3, z: -60 - d, surface: "water", fast: false });
      await sleep(0.8);
    }
  }
  for (const d of [6, 14, 26]) {
    mark(`声: idle ${d}m`);
    ev({ t: "vocal", id: "E3", x: 3, z: -60 - d, kind: "idle" });
    await sleep(2.4);
  }
  mark("壁越し: 足音×2＋声 12m");
  // behind the shop fronts to the east: line of sight is blocked
  for (let i = 0; i < 2; i++) {
    ev({ t: "estep", id: "S1", x: 15, z: -60, surface: "asphalt", fast: false });
    await sleep(0.8);
  }
  ev({ t: "vocal", id: "S1", x: 15, z: -60, kind: "idle" });
  await sleep(2.4);
  for (const kind of ["suspicious", "search", "alert", "attack", "hurt", "die"]) {
    mark(`声: ${kind} 8m`);
    ev({ t: "vocal", id: "E3", x: 3, z: -68, kind });
    await sleep(kind === "die" ? 2.4 : 1.5);
  }
  mark("シャッターの物音");
  audio.rattle(5.1, 1.1, -64);
  await sleep(1.8);
  mark("発砲（命中: 壁）");
  ev({ t: "shot", x: 3, y: 1.4, z: -60, hx: 4.9, hy: 1.5, hz: -70, hit: "world" });
  await sleep(1.6);
  mark("発砲（命中: 体）");
  ev({ t: "shot", x: 3, y: 1.4, z: -60, hx: 2, hy: 1.2, hz: -65, hit: "body" });
  await sleep(1.6);
  mark("空撃ち");
  ev({ t: "dry" });
  await sleep(0.7);
  for (const kind of ["gun", "ammo", "medkit"]) {
    mark(`拾う: ${kind}`);
    ev({ t: "pickup", kind, id: kind });
    await sleep(1.1);
  }
  mark("遠雷");
  audio.thunder(0.05, false);
  await sleep(5.5);
  mark("近い落雷");
  audio.thunder(0.05, true);
  await sleep(7);

  await place(16, -128.5, -1.2);
  mark("水門の環境音");
  await sleep(3);
  mark("足音: 金属×4");
  for (let i = 0; i < 4; i++) {
    ev({ t: "step", x: 16, z: -129, surface: "metal", run: false });
    await sleep(0.5);
  }
  mark("金属の軋み");
  audio.creak({ x: 24, y: 2, z: -137 }, ctx.currentTime + 0.05, 2.2, 100, 1.6, false);
  await sleep(2.8);
  mark("橋: ブザーとモーター（降下中）");
  sim.s.bridge.state = "lowering";
  ev({ t: "bridge", phase: "start" });
  await sleep(5);
  mark("橋: 着地");
  sim.s.bridge.state = "down";
  ev({ t: "bridge", phase: "down" });
  await sleep(3);
  mark("振り下ろし＋被弾");
  ev({ t: "swipe", id: "Y1", x: 17, z: -128, hit: true });
  await sleep(0.2);
  sim.s.player.hp = 25;
  ev({ t: "hurt", hp: 25 });
  mark("心音（体力25）");
  await sleep(4);
  sim.s.player.hp = 100;
  mark("防災無線（チャイム＋拡声器）");
  audio.radioT = 0;
  await sleep(0.1);
  audio.radioT = 1e9;
  await sleep(14);
  mark("最後の合図（暗がりの唸り）");
  ev({ t: "cue", id: "final", x: 16, z: -140 });
  await sleep(2.2);
  mark("死亡");
  ev({ t: "death" });
  await sleep(2.6);
  mark("リトライ");
  ev({ t: "retry" });
  await sleep(1.5);
  mark("クリア（暗転）");
  ev({ t: "clear" });
  await sleep(3.5);
  mark("end");

  sp.disconnect();
  audio.output.disconnect(sp);

  // --- analysis
  const sr = ctx.sampleRate;
  const total = chunksL.reduce((n, c) => n + c.length, 0);
  const L = new Float32Array(total);
  const R = new Float32Array(total);
  let o = 0;
  for (let i = 0; i < chunksL.length; i++) {
    L.set(chunksL[i], o);
    R.set(chunksR[i], o);
    o += chunksL[i].length;
  }
  const mono = new Float32Array(total);
  let bad = 0;
  for (let i = 0; i < total; i++) {
    const v = (L[i] + R[i]) * 0.5;
    if (!Number.isFinite(v)) bad++;
    mono[i] = Number.isFinite(v) ? v : 0;
  }
  const db = (v) => (v > 1e-7 ? 20 * Math.log10(v) : -140);
  const segs = [];
  for (let k = 0; k < marks.length - 1; k++) {
    const a = Math.floor(marks[k].t * sr);
    const b = Math.min(total, Math.floor(marks[k + 1].t * sr));
    let peak = 0;
    let sum = 0;
    let lr = 0;
    let lo = 0;
    let hi = 0;
    let lp = 0;
    for (let i = a; i < b; i++) {
      const v = mono[i];
      const av = Math.max(Math.abs(L[i]), Math.abs(R[i]));
      if (av > peak) peak = av;
      sum += v * v;
      lr += L[i] * L[i] - R[i] * R[i];
      // crude split at ~300 Hz with a one-pole
      lp += (v - lp) * 0.04;
      lo += lp * lp;
      hi += (v - lp) * (v - lp);
    }
    const n = Math.max(1, b - a);
    segs.push({
      name: marks[k].name,
      at: +marks[k].t.toFixed(2),
      len: +((b - a) / sr).toFixed(2),
      peakDb: +db(peak).toFixed(1),
      rmsDb: +db(Math.sqrt(sum / n)).toFixed(1),
      lowDb: +db(Math.sqrt(lo / n)).toFixed(1),
      highDb: +db(Math.sqrt(hi / n)).toFixed(1),
      balance: +(lr / Math.max(1e-9, sum * 2)).toFixed(2),
    });
  }

  // --- spectrogram (log frequency), 4 rows
  const N = 2048;
  const hop = 1024;
  const frames = Math.floor((total - N) / hop);
  const win = new Float32Array(N);
  for (let i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1));
  const rev = new Uint32Array(N);
  const bits = Math.log2(N);
  for (let i = 0; i < N; i++) {
    let r = 0;
    for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b);
    rev[i] = r;
  }
  const re = new Float32Array(N);
  const im = new Float32Array(N);
  const rows = 4;
  const H = 230;
  const perRow = Math.ceil(frames / rows);
  const scaleX = Math.max(1, Math.ceil(perRow / 1500));
  const W = Math.ceil(perRow / scaleX);
  const cv = document.createElement("canvas");
  cv.width = W;
  cv.height = rows * (H + 34);
  const g = cv.getContext("2d");
  g.fillStyle = "#000";
  g.fillRect(0, 0, cv.width, cv.height);
  const fMin = 30;
  const fMax = 16000;
  const binOf = new Float32Array(H);
  for (let y = 0; y < H; y++) {
    const f = fMin * Math.pow(fMax / fMin, 1 - y / (H - 1));
    binOf[y] = (f / sr) * N;
  }
  const img = g.createImageData(W, H);
  for (let row = 0; row < rows; row++) {
    img.data.fill(0);
    const acc = new Float32Array(H);
    for (let x = 0; x < W; x++) {
      acc.fill(0);
      for (let s = 0; s < scaleX; s++) {
        const fr = row * perRow + x * scaleX + s;
        if (fr >= frames) break;
        const off = fr * hop;
        for (let i = 0; i < N; i++) {
          re[rev[i]] = mono[off + i] * win[i];
          im[rev[i]] = 0;
        }
        for (let size = 2; size <= N; size <<= 1) {
          const half = size >> 1;
          const ang = (-2 * Math.PI) / size;
          for (let st = 0; st < N; st += size) {
            for (let k2 = 0; k2 < half; k2++) {
              const c = Math.cos(ang * k2);
              const sn = Math.sin(ang * k2);
              const xr = re[st + k2 + half] * c - im[st + k2 + half] * sn;
              const xi = re[st + k2 + half] * sn + im[st + k2 + half] * c;
              re[st + k2 + half] = re[st + k2] - xr;
              im[st + k2 + half] = im[st + k2] - xi;
              re[st + k2] += xr;
              im[st + k2] += xi;
            }
          }
        }
        for (let y = 0; y < H; y++) {
          const b0 = Math.max(1, Math.floor(binOf[y]));
          const m = Math.hypot(re[b0], im[b0]) / (N / 4);
          if (m > acc[y]) acc[y] = m;
        }
      }
      for (let y = 0; y < H; y++) {
        const d = Math.max(0, Math.min(1, (db(acc[y]) + 90) / 80));
        const i4 = (y * W + x) * 4;
        img.data[i4] = Math.min(255, d * d * 400);
        img.data[i4 + 1] = Math.min(255, d * 230);
        img.data[i4 + 2] = Math.min(255, 60 + d * 120 * (1 - d));
        img.data[i4 + 3] = 255;
      }
    }
    const y0 = row * (H + 34) + 30;
    g.putImageData(img, 0, y0);
    g.font = "11px sans-serif";
    g.textBaseline = "alphabetic";
    const tA = (row * perRow * hop) / sr;
    const tB = ((row + 1) * perRow * hop) / sr;
    let lane = 0;
    for (const m of marks) {
      if (m.t < tA || m.t >= tB) continue;
      const x = ((m.t - tA) * sr) / hop / scaleX;
      g.fillStyle = "rgba(255,255,255,0.5)";
      g.fillRect(x, y0 - 4, 1, H + 4);
      g.fillStyle = "#ffe98a";
      g.fillText(m.name, x + 3, y0 - 6 - (lane % 2) * 12);
      lane++;
    }
    g.fillStyle = "#8fd";
    for (const f of [100, 1000, 10000]) {
      const y = y0 + (1 - Math.log(f / fMin) / Math.log(fMax / fMin)) * (H - 1);
      g.fillRect(0, y, 6, 1);
      g.fillText(f >= 1000 ? `${f / 1000}k` : `${f}`, 8, y + 4);
    }
  }

  // --- a WAV to listen to (mono, half rate)
  const step = 2;
  const outN = Math.floor(total / step);
  const wav = new DataView(new ArrayBuffer(44 + outN * 2));
  const wr = (off, str) => [...str].forEach((c, i) => wav.setUint8(off + i, c.charCodeAt(0)));
  wr(0, "RIFF");
  wav.setUint32(4, 36 + outN * 2, true);
  wr(8, "WAVEfmt ");
  wav.setUint32(16, 16, true);
  wav.setUint16(20, 1, true);
  wav.setUint16(22, 1, true);
  wav.setUint32(24, sr / step, true);
  wav.setUint32(28, (sr / step) * 2, true);
  wav.setUint16(32, 2, true);
  wav.setUint16(34, 16, true);
  wr(36, "data");
  wav.setUint32(40, outN * 2, true);
  for (let i = 0; i < outN; i++) {
    const v = Math.max(-1, Math.min(1, (mono[i * step] + mono[i * step + 1]) * 0.5));
    wav.setInt16(44 + i * 2, Math.round(v * 32767), true);
  }
  const bytes = new Uint8Array(wav.buffer);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));

  return {
    sampleRate: sr,
    seconds: total / sr,
    nonFinite: bad,
    counts: audio.counts,
    levels: audio.levels(),
    segs,
    png: cv.toDataURL("image/png"),
    wav: btoa(bin),
  };
}, mode);

if (result.error) {
  console.log(JSON.stringify({ error: result.error, errors }));
  await browser.close();
  process.exit(1);
}
writeFileSync(join(outDir, `catalogue-${mode}.png`), Buffer.from(result.png.split(",")[1], "base64"));
writeFileSync(join(outDir, `catalogue-${mode}.wav`), Buffer.from(result.wav, "base64"));
const { png: _p, wav: _w, ...rest } = result;
writeFileSync(join(outDir, `catalogue-${mode}.json`), JSON.stringify(rest, null, 1));
console.log(`recorded ${result.seconds.toFixed(1)}s @${result.sampleRate}Hz  nonFinite=${result.nonFinite}  errors=${JSON.stringify(errors)}`);
console.log("counts", JSON.stringify(result.counts));
for (const s of result.segs) {
  console.log(
    `${String(s.at).padStart(6)}s ${s.name.padEnd(22, "　")} peak ${String(s.peakDb).padStart(6)} dB  rms ${String(s.rmsDb).padStart(6)} dB  low ${String(s.lowDb).padStart(6)}  high ${String(s.highDb).padStart(6)}  L-R ${s.balance}`,
  );
}
await browser.close();
