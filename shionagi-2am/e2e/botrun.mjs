// Quick check: let the scripted player run a route in the real page at high speed.
//   node e2e/botrun.mjs normal|pacifist [speed] [extra-query]
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";

const route = process.argv[2] ?? "pacifist";
const speed = Number(process.argv[3] ?? "6");
const extra = process.argv[4] ? `&${process.argv[4]}` : "";
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
await page.goto(`${BASE}/?bot=${route}&autostart&tts=0&speed=${speed}${extra}`);
const t0 = Date.now();
let st = null;
while (Date.now() - t0 < 240000) {
  await page.waitForTimeout(1000);
  st = await page.evaluate(() => window.__shio.state());
  if (st.phase === "clear") break;
}
const events = await page.evaluate(() => window.__shio.bot.events);
console.log(JSON.stringify({ wall: (Date.now() - t0) / 1000, state: st, errors }, null, 1));
console.log(events.join("\n"));
await browser.close();
