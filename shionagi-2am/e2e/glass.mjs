// How does the figure outside the fogged glass read from inside the hall?
//   node e2e/glass.mjs <outDir>          three posed views (figure placed by hand)
//   node e2e/glass.mjs <outDir> live     the real opening: walk off, then watch
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
const out = process.argv[2];
const live = process.argv[3] === "live";
const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--mute-audio"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(`${BASE}/?autostart&nolock&tts=0`);
await page.waitForFunction(() => window.__shio && window.__shio.mode === "play");

if (live) {
  // A first-time player: walks a few steps the way they are facing, hears something, stops.
  await page.keyboard.down("KeyW");
  await page.waitForTimeout(1900);
  await page.keyboard.up("KeyW");
  const info = () =>
    page.evaluate(() => {
      const a = window.__shio;
      const e = a.sim.enemy("P1");
      const p = a.sim.s.player;
      return { t: +a.sim.s.time.toFixed(1), px: +p.x.toFixed(1), pz: +p.z.toFixed(1), yaw: +p.yaw.toFixed(2), ex: +e.x.toFixed(1), ez: +e.z.toFixed(1), mode: e.mode, sounds: a.audio.counts };
    });
  // (a) not turning at all: the lightning that follows the cue, then ordinary moments
  await page.waitForFunction(() => window.__shio.sim.s.time > 3 && window.__shio.view.flash > 0.25, null, { timeout: 20000 });
  await page.screenshot({ path: `${out}/live-ahead-flash.png` });
  console.log("flash", JSON.stringify(await info()));
  for (const at of [6.6, 8.5]) {
    await page.waitForFunction((t) => window.__shio.sim.s.time >= t && window.__shio.view.flash < 0.02, at);
    await page.screenshot({ path: `${out}/live-ahead-${String(at).replace(".", "_")}.png` });
    console.log("ahead", JSON.stringify(await info()));
  }
  // (b) turning to where the sound comes from, as someone who heard it would
  for (const at of [10.5, 14, 19]) {
    await page.waitForFunction((t) => window.__shio.sim.s.time >= t, at);
    await page.evaluate(() => {
      const a = window.__shio;
      const e = a.sim.enemy("P1");
      const p = a.sim.s.player;
      p.yaw = p.bodyYaw = Math.atan2(-(e.x - p.x), -(e.z - p.z)); // figure at the crosshair, right of the player model
      p.pitch = 0.02;
    });
    await page.waitForFunction(() => window.__shio.view.flash < 0.02);
    await page.waitForTimeout(450);
    await page.screenshot({ path: `${out}/live-turned-${String(at).replace(".", "_")}.png` });
    console.log("turned", JSON.stringify(await info()));
  }
  await browser.close();
  process.exit(0);
}

const stops = [
  ["glass-a", -5.5, -9.0, 0.25, -6.5, -15.25],
  ["glass-b", -1.0, -11.5, 0.3, -3.4, -15.25],
  ["glass-c", -8.5, -2.2, -0.75, -1.5, -15.25],
];
for (const [name, x, z, yaw, ex, ez] of stops) {
  await page.evaluate(
    ([x, z, yaw, ex, ez]) => {
      const a = window.__shio;
      a.setSpeed(0);
      for (const e of a.sim.s.enemies) e.mode = "dormant";
      const e = a.sim.enemy("P1");
      e.mode = "home";
      e.x = e.px = ex;
      e.z = e.pz = ez;
      e.yaw = Math.PI / 2;
      e.gait = 1.1;
      e.speed = 0.7;
      a.teleport(x, z, yaw);
      a.sim.s.player.pitch = 0.02;
      a.sim.step({ mx: 0, mz: 0, run: false, aim: false, fire: false, interact: false });
      a.sim.events.length = 0;
    },
    [x, z, yaw, ex, ez],
  );
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${out}/${name}.png` });
}
await browser.close();
