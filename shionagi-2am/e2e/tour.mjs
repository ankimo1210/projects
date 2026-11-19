// Dev helper: teleport around the map and save a screenshot at each stop.
//   node e2e/tour.mjs <outDir> [name,name,...]
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";

const outDir = process.argv[2] ?? ".";
const only = process.argv[3] ? process.argv[3].split(",") : null;
const N = 0, W = Math.PI / 2, S = Math.PI, E = -Math.PI / 2;
// name, x, z, yaw, pitch, [setup js]
const STOPS = [
  ["01-start", -8.5, -2.2, -1.12, -0.06],
  ["02-glass", -2, -9.5, 0.25, 0.02, "s.fired.glass=true; const e=sim.enemy('P1'); e.mode='home'; e.x=e.px=-4; e.z=e.pz=-16.3; e.yaw=Math.PI/2;"],
  ["03-door1", 3.6, -5.2, E, -0.05],
  ["04-corridor", 7.6, -5.5, N, -0.03, "s.doors.D1=true; sim.syncDynamic();"],
  ["05-backdoor", 11.5, -12.1, E, -0.03, "s.doors.D1=true; sim.syncDynamic();"],
  ["06-lane", 16.2, -12, N, -0.02, "s.doors.D2=true; sim.syncDynamic();"],
  ["07-tjunction", 16, -21, 0.5, 0.0],
  ["08-plaza", 12.5, -22.6, W, 0.0],
  ["09-arch", 3, -22, 0.3, 0.05],
  ["10-street-s", 3.8, -27.5, 0.05, 0.0],
  ["11-patrolcar", 4.0, -38.5, 0.5, -0.12],
  ["12-laneA", 12.5, -34.6, W, -0.02],
  ["13-street-mid", 3.6, -54, 0.1, 0.0],
  ["14-street-n", 3.5, -84, 0.08, 0.0],
  ["15-alley1", 15.4, -26, N, 0.0],
  ["16-alley-jog", 15.4, -54, -0.5, -0.05],
  ["17-alley2", 18.3, -66, N, -0.02],
  ["18-junction", 15, -107, W, 0.0],
  ["19-yardgate", 11.5, -108, N, 0.02],
  ["20-yard", 11, -113, 0.0, 0.05],
  ["21-panel", 9.5, -128.6, 0.3, -0.12],
  ["22-quay", 12, -129.5, E, 0.06],
  ["23-bridge-up", 21, -128.5, -0.45, 0.2],
  ["24-bridge-down", 24.25, -133.5, N, 0.0, "s.bridge.state='down'; sim.syncDynamic();"],
  ["25-forecourt", 24.25, -148, N, 0.02, "s.bridge.state='down'; sim.syncDynamic();"],
  ["26-island", 29.5, -156, 0.25, 0.02],
  ["27-entrance", 24.25, -169.5, N, 0.05],
  ["30-enemy-near", 2.6, -100.2, N, -0.08, "for (const e of s.enemies) if (e.id!=='E6') e.mode='dormant'; const e=sim.enemy('E6'); e.mode='dormant'; e.x=e.px=2.2; e.z=e.pz=-103.2; e.yaw=Math.PI;"],
  ["31-enemy-far", 2.6, -94.5, N, -0.03, "const e=sim.enemy('E6'); e.mode='dormant'; e.x=e.px=1.2; e.z=e.pz=-103.2; e.yaw=Math.PI;"],
  ["32-enemy-chase", 2.6, -98.5, N, -0.05, "const e=sim.enemy('E6'); e.mode='chase'; e.x=e.px=1.9; e.z=e.pz=-102.6; e.yaw=Math.PI; e.speed=2.6; e.gait=1.2;"],
  ["33-dark-alcove", 18.0, -70.6, -0.9, 0.0],
];

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
page.on("pageerror", (e) => errors.push(`pageerror ${e.message}`));
await page.goto(`${BASE}/?autostart&nolock&tts=0`, { waitUntil: "load" });
await page.waitForFunction(() => window.__shio !== undefined);
// freeze the action: we are only looking
await page.evaluate(() => window.__shio.setSpeed(0.0001));
for (const [name, x, z, yaw, pitch, setup] of STOPS) {
  if (only && !only.some((o) => name.includes(o))) continue;
  await page.evaluate(
    ([x, z, yaw, pitch, setup]) => {
      const { sim } = window.__shio;
      const s = sim.s;
      if (setup) new Function("sim", "s", setup)(sim, s);
      for (const e of s.enemies) if (e.mode !== "dead" && e.mode !== "dormant") e.aware = 0;
      window.__shio.teleport(x, z, yaw);
      s.player.pitch = pitch;
      s.zone = sim.zoneAt(x, z) ?? s.zone;
    },
    [x, z, yaw, pitch, setup ?? ""],
  );
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${outDir}/${name}.png` });
}
console.log(JSON.stringify({ errors: errors.slice(0, 10), state: await page.evaluate(() => window.__shio.state()) }));
await browser.close();
