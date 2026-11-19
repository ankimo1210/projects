// Real keyboard and mouse events (not the bot) against the real page: start,
// move, look, run, doors, pick up and fire the revolver, pause, die, retry,
// reach the station doors, play again.
//   node e2e/smoke.mjs <outDir> [headed]
import { chromium } from "playwright-core";

// the dev server by default; set SHIO_URL to test a production build (pnpm preview)
const BASE = process.env.SHIO_URL ?? "http://localhost:5183";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const outDir = process.argv[2] ?? "smoke-out";
const headed = process.argv[3] === "headed";
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({
  channel: "chrome",
  headless: !headed,
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") errors.push(`${m.type()}: ${m.text()}`);
});
page.on("pageerror", (e) => errors.push(`pageerror: ${e}`));

const checks = [];
const check = (name, ok, detail = "") => {
  checks.push({ name, ok: Boolean(ok), detail: String(detail) });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
};
const state = () => page.evaluate(() => window.__shio.state());
const ev = (fn, arg) => page.evaluate(fn, arg);
const wait = (ms) => page.waitForTimeout(ms);
const shot = (name) => page.screenshot({ path: join(outDir, `${name}.png`) });
const quiet = () =>
  ev(() => {
    for (const e of window.__shio.sim.s.enemies) if (e.mode !== "dead") e.mode = "dormant";
  });

await page.goto(`${BASE}/?tts=0`);
await page.waitForFunction(() => window.__shio);
await wait(600);
let st = await state();
check("title screen is shown before any input", st.mode === "title" && st.screen === "title", `mode=${st.mode}`);
const hudHidden = await ev(() => document.getElementById("hud").hidden);
check("HUD is hidden on the title screen", hudHidden);
await shot("01-title");

// --- start with a click
await page.mouse.click(640, 420);
await wait(500);
st = await state();
check("a click starts the game in control of the player", st.mode === "play" && st.phase === "play" && st.screen === "none");
check("pointer is captured after the click", st.locked, `locked=${st.locked} (headless Chrome may refuse pointer lock)`);
check("audio context is running", st.audio.running === 1, JSON.stringify(st.audio));
const hint0 = await ev(() => document.getElementById("hint").textContent);
check("movement hint is shown at the start", /移動/.test(hint0 ?? ""), hint0);
await quiet();
await shot("02-start");

// --- walk
let a = await state();
await page.keyboard.down("KeyW");
await wait(1500);
await page.keyboard.up("KeyW");
await wait(200);
let b = await state();
let moved = Math.hypot(b.x - a.x, b.z - a.z);
check("holding W walks forward at walking pace", moved > 2.2 && moved < 3.4, `${moved.toFixed(2)} m in 1.5 s`);

// --- look
a = await state();
await page.mouse.move(640, 420);
await page.mouse.move(760, 420, { steps: 8 });
await wait(150);
b = await state();
const dyaw = b.yaw - a.yaw;
check("moving the mouse right turns the view right", dyaw < -0.1 && dyaw > -0.6, `yaw ${a.yaw} → ${b.yaw}`);

// --- strafe + run (in the open strip in front of the glass, facing west)
await ev(() => window.__shio.teleport(-2, -12.2, Math.PI / 2));
await wait(150);
a = await state();
await page.keyboard.down("KeyA");
await wait(600);
await page.keyboard.up("KeyA");
await wait(200);
b = await state();
check("A strafes left without turning", b.z - a.z > 0.7 && Math.abs(b.x - a.x) < 0.3, `dx=${(b.x - a.x).toFixed(2)} dz=${(b.z - a.z).toFixed(2)}`);
await page.keyboard.down("KeyS");
await wait(600);
await page.keyboard.up("KeyS");
await wait(200);
const c = await state();
check("S backs away", c.x - b.x > 0.5, `dx=${(c.x - b.x).toFixed(2)}`);
await ev(() => window.__shio.teleport(-2, -12.2, Math.PI / 2));
a = await state();
await page.keyboard.down("ShiftLeft");
await page.keyboard.down("KeyW");
await wait(1200);
await page.keyboard.up("KeyW");
await page.keyboard.up("ShiftLeft");
await wait(200);
b = await state();
moved = Math.hypot(b.x - a.x, b.z - a.z);
check("Shift + W runs (faster than walking)", moved > 3.6, `${moved.toFixed(2)} m in 1.2 s`);

// --- examine the dead automatic doors
await ev(() => window.__shio.teleport(0, -12.7, 0));
await wait(250);
st = await state();
check("standing at the front doors offers an interaction", st.prompt === "frontDoor", `prompt=${st.prompt}`);
const promptText = await ev(() => document.getElementById("prompt").textContent);
check("the prompt names the key", /E/.test(promptText ?? ""), promptText);
await page.keyboard.press("KeyE");
await wait(300);
const msg = await ev(() => document.getElementById("message").textContent);
check("E examines: a line of text appears", (msg ?? "").length > 4, msg);
await shot("03-frontdoor");

// --- open the staff door
await ev(() => window.__shio.teleport(5.05, -5.5, -Math.PI / 2));
await wait(250);
st = await state();
check("the staff door prompt appears", st.prompt === "D1", `prompt=${st.prompt}`);
await page.keyboard.press("KeyE");
await wait(400);
st = await state();
check("E opens the door", st.doors.includes("D1"), JSON.stringify(st.doors));
await page.keyboard.down("KeyW");
await wait(1300);
await page.keyboard.up("KeyW");
st = await state();
check("and the doorway can be walked through", st.x > 6.3, `x=${st.x}`);

// --- the revolver
await ev(() => window.__shio.teleport(4.15, -34.4, Math.PI / 2));
await quiet();
await wait(300);
st = await state();
check("the revolver on the patrol car can be picked up", st.prompt === "gun", `prompt=${st.prompt}`);
await page.keyboard.press("KeyE");
await wait(300);
st = await state();
check("E picks it up with a few rounds", st.hasGun && st.ammo === 5, `ammo=${st.ammo}`);
const ammoShown = await ev(() => !document.getElementById("ammo").hidden);
check("ammo count appears on the HUD only now", ammoShown);
await page.mouse.click(640, 420); // left click without aiming must not fire
await wait(200);
st = await state();
check("left click without aiming does not fire", st.stats.shots === 0 && st.ammo === 5);
await ev(() => window.__shio.teleport(3.5, -45, 0));
await wait(100);
await page.mouse.down({ button: "right" });
await wait(450);
st = await state();
check("holding the right button raises the revolver", st.aim > 0.9, `aim=${st.aim}`);
const cross = await ev(() => !document.getElementById("crosshair").hidden);
check("crosshair is visible while aiming", cross);
await shot("04-aim");
await page.mouse.down({ button: "left" });
await page.mouse.up({ button: "left" });
await wait(250);
st = await state();
check("left click while aiming fires one round", st.stats.shots === 1 && st.ammo === 4, `shots=${st.stats.shots} ammo=${st.ammo}`);
await shot("05-shot");
await ev(() => {
  window.__shio.sim.s.player.ammo = 0;
});
await wait(700);
await page.mouse.down({ button: "left" });
await page.mouse.up({ button: "left" });
await wait(250);
st = await state();
check("an empty revolver only clicks", st.stats.shots === 1 && st.sounds.dry >= 1, `dry=${st.sounds.dry}`);
await page.mouse.up({ button: "right" });
await wait(300);
st = await state();
check("releasing the right button lowers it", st.aim < 0.1, `aim=${st.aim}`);

// --- pause and resume
// (Esc itself is handled by the browser, which releases the pointer; a
// synthetic key press cannot trigger that, so release it the way Esc would.)
await ev(() => document.exitPointerLock());
await wait(500);
st = await state();
check("losing the pointer (what Esc does) pauses", st.mode === "pause" && st.screen === "pause", `mode=${st.mode}`);
await shot("06-pause");
const tPause = st.time;
await wait(600);
st = await state();
check("time does not advance while paused", st.time === tPause, `${tPause} → ${st.time}`);
await page.mouse.click(640, 420);
await wait(500);
st = await state();
check("a click resumes and captures the pointer again", st.mode === "play" && st.screen === "none" && st.locked, `mode=${st.mode} locked=${st.locked}`);
await page.keyboard.press("KeyP");
await wait(500);
st = await state();
check("P pauses even with the pointer captured", st.mode === "pause" && !st.locked, `mode=${st.mode} locked=${st.locked}`);
await page.keyboard.press("KeyP");
await wait(500);
st = await state();
check("P resumes", st.mode === "play", `mode=${st.mode}`);

// --- get hit, die, retry
await ev(() => {
  const { sim } = window.__shio;
  const p = sim.s.player;
  p.hp = 50;
  window.__shio.teleport(16.3, -12, 0); // the first checkpoint, in the service lane
  window.__shio.advance(0.2, false);
  window.__shio.teleport(16.3, -16, 0);
  const e = sim.enemy("E1");
  e.mode = "chase";
  e.x = e.px = 16.3;
  e.z = e.pz = -18.2;
  e.yaw = Math.PI;
  e.aware = 1;
  e.lostT = 0;
  e.path = null;
});
let sawHurt = false;
let dead = false;
for (let i = 0; i < 60 && !dead; i++) {
  await wait(120);
  st = await state();
  if (st.hp < 50 && st.hp > 0 && !sawHurt) {
    sawHurt = true;
    await shot("07-hurt");
  }
  dead = st.phase === "dead";
}
check("an attack takes a quarter of the health", sawHurt, `hp=${st.hp}`);
check("health running out kills the player", dead && st.screen === "dead", `phase=${st.phase} screen=${st.screen}`);
await wait(1700);
await shot("08-dead");
const deathText = await ev(() => document.getElementById("screen").textContent);
check("the death screen says how to retry", /やり直す/.test(deathText ?? ""), (deathText ?? "").replace(/\s+/g, " ").trim());
await page.keyboard.press("KeyE");
await wait(500);
st = await state();
check(
  "E retries from the last checkpoint with health topped up to 60",
  st.phase === "play" && st.hp === 60 && st.screen === "none" && st.checkpoint === "lane" && Math.abs(st.x - 16.3) < 0.2 && Math.abs(st.z + 12) < 0.5,
  `cp=${st.checkpoint} hp=${st.hp} at (${st.x}, ${st.z})`,
);
check("the retry is counted", st.stats.deaths === 1);
await shot("09-retry");

// --- the bridge panel
await quiet();
await ev(() => window.__shio.teleport(9.0, -129.95, Math.PI));
await wait(250);
st = await state();
check("the control panel prompt appears", st.prompt === "panel", `prompt=${st.prompt}`);
await page.keyboard.press("KeyE");
await wait(400);
st = await state();
check("E starts the footbridge coming down", st.bridge === "lowering", st.bridge);
await ev(() => window.__shio.teleport(21.5, -130.2, -0.6));
await wait(5000);
await shot("10-bridge-lowering");
await ev(() => window.__shio.advance(8, true));
await wait(300);
st = await state();
check("after twelve seconds the bridge is down", st.bridge === "down", st.bridge);
await shot("11-bridge-down");

// --- the station doors
await ev(() => window.__shio.teleport(24.25, -170.2, 0));
await quiet();
await wait(400);
await shot("12-entrance");
await page.keyboard.down("KeyW");
await wait(1150);
await page.keyboard.up("KeyW");
await wait(200);
st = await state();
check("the station doors offer an interaction", st.prompt === "exit", `prompt=${st.prompt} z=${st.z}`);
await page.keyboard.press("KeyE");
await wait(250);
st = await state();
check("E at the station doors clears the game", st.phase === "clear", st.phase);
const black = await ev(() => {
  const c = document.getElementById("game");
  const t = document.createElement("canvas");
  t.width = 64;
  t.height = 36;
  const g = t.getContext("2d");
  g.drawImage(c, 0, 0, 64, 36);
  const d = g.getImageData(0, 0, 64, 36).data;
  let m = 0;
  for (let i = 0; i < d.length; i += 4) m = Math.max(m, d[i], d[i + 1], d[i + 2]);
  return m;
});
check("the picture cuts to black at once", black <= 6, `brightest pixel ${black}/255 after 0.25 s`);
await wait(2600);
st = await state();
check("the clear screen follows", st.screen === "clear");
await shot("13-clear");
const clearText = await ev(() => document.getElementById("screen").textContent);
check("it reports time, shots and retries", /所要時間/.test(clearText ?? "") && /発砲/.test(clearText ?? ""), (clearText ?? "").replace(/\s+/g, " ").trim());
await page.mouse.click(640, 420);
await wait(700);
st = await state();
check("clicking plays again from the terminal", st.phase === "play" && st.time < 2 && st.zone === "terminal" && !st.hasGun, `t=${st.time} zone=${st.zone}`);

check("no console errors or warnings", errors.length === 0, errors.join(" | "));
const failed = checks.filter((c) => !c.ok);
writeFileSync(join(outDir, "smoke.json"), JSON.stringify({ headed, checks, errors }, null, 1));
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
await browser.close();
process.exit(failed.length === 0 ? 0 : 1);
