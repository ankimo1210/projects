// Does the spoken disaster-radio announcement actually run on this machine?
// It is played at zero volume here (tts=silent): the point is the code path.
import { chromium } from "playwright-core";

const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`${BASE}/?tts=silent`);
await page.waitForFunction(() => window.__shio);
await page.mouse.click(480, 300); // speech needs a user gesture
await page.evaluate(() => {
  for (const e of window.__shio.sim.s.enemies) e.mode = "dormant";
});
let info = null;
for (let i = 0; i < 40; i++) {
  await page.waitForTimeout(1000);
  info = await page.evaluate(() => ({
    sounds: window.__shio.audio.counts,
    voices: speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("ja")).map((v) => `${v.name} (${v.lang}${v.localService ? ", local" : ""})`),
    speaking: speechSynthesis.speaking,
    chosen: window.__shio.audio.voice?.name ?? null,
  }));
  if (info.sounds["radio:speech-ended"] || info.sounds["radio:speech-error"] || info.sounds["radio:murmur"]) break;
}
console.log(JSON.stringify({ ...info, errors }, null, 1));
await browser.close();
