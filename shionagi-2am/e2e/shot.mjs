// Dev helper: load the game in real Chrome, run a snippet, save a screenshot.
//   node e2e/shot.mjs <out.png> [--url=...] [--eval="js run in the page"] [--wait=ms] [--size=1280x720]
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";

const args = process.argv.slice(2);
const out = args.find((a) => !a.startsWith("--")) ?? "shot.png";
const opt = (name, def) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : def;
};
const url = opt("url", `${BASE}/?autostart&nolock&dev&tts=0`);
const [w, h] = opt("size", "1280x720").split("x").map(Number);
const wait = Number(opt("wait", "1500"));
const code = opt("eval", "");
const headless = opt("headed", "") === "";

const browser = await chromium.launch({
  channel: "chrome",
  headless,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") errors.push(`[${m.type()}] ${m.text()}`);
});
page.on("pageerror", (e) => errors.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: "load" });
await page.waitForFunction(() => window.__shio !== undefined, null, { timeout: 15000 }).catch(() => {});
let result;
if (code) result = await page.evaluate(code).catch((e) => `eval failed: ${e.message}`);
await page.waitForTimeout(wait);
const info = await page
  .evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl2");
    const ext = gl && gl.getExtension("WEBGL_debug_renderer_info");
    return {
      renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "?",
      state: window.__shio ? window.__shio.state() : null,
    };
  })
  .catch((e) => ({ error: e.message }));
await page.screenshot({ path: out });
console.log(JSON.stringify({ result, info, errors: errors.slice(0, 12) }, null, 1));
await browser.close();
