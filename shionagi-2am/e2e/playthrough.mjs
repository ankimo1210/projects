// Let the scripted player run a whole route in the real page, in real time,
// with rendering and audio on, and keep screenshots of what happened.
//   node e2e/playthrough.mjs <normal|pacifist> <outDir> [direct|dom] [speed]
// "dom" makes the bot press keys and move the mouse through DOM events, so the
// game's own input handling is what drives the simulation.
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const route = process.argv[2] ?? "pacifist";
const outDir = process.argv[3] ?? `play-${route}`;
const via = process.argv[4] ?? "direct";
const speed = Number(process.argv[5] ?? "1");
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") errors.push(`${m.type()}: ${m.text()}`);
});
page.on("pageerror", (e) => errors.push(`pageerror: ${e}`));

const q = `bot=${route}&autostart&tts=0${via === "dom" ? "&via=dom" : ""}${speed !== 1 ? `&speed=${speed}` : ""}`;
await page.goto(`${BASE}/?${q}`);
await page.waitForFunction(() => window.__shio && window.__shio.mode === "play");
const wall0 = Date.now();

let shot = 0;
const shots = [];
async function snap(label, st) {
  const name = `${String(++shot).padStart(2, "0")}-t${String(Math.round(st.time)).padStart(3, "0")}-${label}.png`;
  await page.screenshot({ path: join(outDir, name) });
  shots.push(name);
}

const wanted = [
  [/door D1/, "door1"],
  [/door D2/, "backdoor"],
  [/checkpoint lane/, "lane"],
  [/hold for/, "hold"],
  [/spotted by/, "spotted"],
  [/pickup gun/, "gun"],
  [/pickup ammo/, "ammo"],
  [/shot/, "shot"],
  [/HURT/, "hurt"],
  [/DEATH/, "death"],
  [/retry/, "retry"],
  [/checkpoint junction/, "junction"],
  [/bridge start/, "bridge-start"],
  [/bridge down/, "bridge-down"],
  [/checkpoint forecourt/, "forecourt"],
  [/cue final/, "final"],
];
const perLabel = {};
let seen = 0;
let nextPeriodic = 4;
const fps = [];
const frameMs = [];
const rms = [];
let st = null;
let last = null;
let cleared = false;
while (Date.now() - wall0 < 420000) {
  await page.waitForTimeout(200);
  st = await page.evaluate(() => {
    const a = window.__shio;
    return { ...a.state(), events: a.bot.events.slice() };
  });
  fps.push(st.fps);
  frameMs.push(st.render.frameMs);
  if (st.audio && st.audio.rms !== undefined) rms.push(st.audio.rms);
  for (; seen < st.events.length; seen++) {
    const ev = st.events[seen];
    for (const [re, label] of wanted) {
      if (!re.test(ev)) continue;
      perLabel[label] = (perLabel[label] ?? 0) + 1;
      if (perLabel[label] <= 3) await snap(label, st);
      break;
    }
  }
  if (st.time >= nextPeriodic) {
    await snap(`${st.zone}`, st);
    nextPeriodic += 9;
  }
  last = st;
  if (st.phase === "clear") {
    cleared = true;
    await snap("clear-cut", st);
    await page.waitForTimeout(2600);
    st = await page.evaluate(() => ({ ...window.__shio.state(), events: window.__shio.bot.events.slice() }));
    await snap("clear-screen", st);
    break;
  }
}

const sorted = [...fps].sort((a, b) => a - b);
const summary = {
  route,
  via,
  speed,
  cleared,
  wallSeconds: +((Date.now() - wall0) / 1000).toFixed(1),
  gameSeconds: st?.time,
  hp: st?.hp,
  ammo: st?.ammo,
  hasGun: st?.hasGun,
  stats: st?.stats,
  screen: st?.screen,
  fps: { min: sorted[0], median: sorted[Math.floor(sorted.length / 2)], samples: sorted.length },
  frameMsMax: +Math.max(...frameMs).toFixed(2),
  audio: {
    running: st?.audio?.running,
    rmsMax: rms.length ? +Math.max(...rms).toFixed(4) : null,
    rmsMedian: rms.length ? +[...rms].sort((a, b) => a - b)[Math.floor(rms.length / 2)].toFixed(4) : null,
    sounds: st?.sounds,
  },
  driver: st?.driver,
  errors,
  events: st?.events,
  shots,
};
writeFileSync(join(outDir, "summary.json"), JSON.stringify(summary, null, 1));
const { events, shots: _s, ...brief } = summary;
console.log(JSON.stringify(brief));
console.log(events.filter((e) => !/hold for|move on/.test(e)).join("\n"));
await browser.close();
process.exit(cleared && errors.length === 0 ? 0 : 1);
