// Frame rate at a Retina-sized window (the renderer caps its pixel ratio at 1.5).
//   node e2e/perf.mjs [seconds]
import { chromium } from "playwright-core";

const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
const seconds = Number(process.argv[2] ?? "40");
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 1728, height: 1080 }, deviceScaleFactor: 2 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`${BASE}/?bot=normal&autostart&tts=0`);
await page.waitForFunction(() => window.__shio && window.__shio.mode === "play");
const fps = [];
const ms = [];
let st = null;
for (let i = 0; i < seconds; i++) {
  await page.waitForTimeout(1000);
  st = await page.evaluate(() => window.__shio.state());
  if (i >= 3) {
    fps.push(st.fps);
    ms.push(st.render.frameMs);
  }
}
const s = [...fps].sort((a, b) => a - b);
const gl = await page.evaluate(() => {
  const c = document.getElementById("game");
  return { canvas: `${c.width}x${c.height}`, dpr: window.devicePixelRatio };
});
console.log(
  JSON.stringify({
    ...gl,
    pixelRatioUsed: st.render.pixelRatio,
    fpsMin: s[0],
    fpsMedian: s[Math.floor(s.length / 2)],
    renderMsMax: +Math.max(...ms).toFixed(2),
    calls: st.render.calls,
    triangles: st.render.triangles,
    zoneAtEnd: st.zone,
    errors,
  }),
);
await browser.close();
