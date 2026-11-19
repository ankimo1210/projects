import "./ui/style.css";
import { AudioEngine } from "./audio/audio";
import { Bot } from "./dev/bot";
import { DomBridge } from "./dev/dombridge";
import type { Driver } from "./dev/driver";
import { Input } from "./input";
import { DT, Sim } from "./sim/sim";
import type { SimEvent } from "./sim/types";
import { Hud, Screens } from "./ui/hud";
import { View } from "./view/view";

type Mode = "title" | "play" | "pause";

const params = new URLSearchParams(location.search);
const canvas = document.getElementById("game") as HTMLCanvasElement;
const sim = new Sim();
const view = new View(canvas, sim);
const hud = new Hud();
const screens = new Screens();
const audio = new AudioEngine();
const input = new Input(canvas, (dy, dp) => sim.applyLook(dy, dp));

let mode: Mode = "title";
let driver: Driver | null = null;
/** the scripted test player, when the page was opened with ?bot=normal|pacifist */
let bot: Bot | null = null;
/** true when the driver feeds the game through DOM events and the Input class */
let viaDom = false;
let speed = Math.max(0.1, Number(params.get("speed") ?? "1") || 1);
let steps = 0;
const log: { t: number; ev: string }[] = [];

view.hooks.thunder = (delay, near) => audio.thunder(delay, near);
view.hooks.rattle = (x, y, z) => audio.rattle(x, y, z);

function onEvent(ev: SimEvent): void {
  view.onEvent(ev);
  audio.onEvent(ev, sim);
  driver?.observe?.(ev, sim);
  switch (ev.t) {
    case "hint":
      hud.setHint(ev.id, ev.id === "aim" ? 9 : 7);
      break;
    case "death":
      screens.show("dead");
      break;
    case "clear":
      if (document.pointerLockElement) document.exitPointerLock();
      screens.show("clear", sim.s);
      break;
    case "retry":
      screens.show("none");
      break;
    default:
      break;
  }
  if (ev.t !== "step" && ev.t !== "estep" && ev.t !== "vocal") {
    log.push({ t: Math.round(sim.s.time * 10) / 10, ev: ev.t + ("id" in ev ? `:${ev.id}` : "phase" in ev ? `:${ev.phase}` : "") });
    if (log.length > 400) log.shift();
  }
}

function stepOnce(): void {
  const inp = driver ? driver.step(sim) : input.frame();
  sim.step(inp);
  steps++;
  if (sim.events.length > 0) {
    for (const ev of sim.events) onEvent(ev);
    sim.events.length = 0;
  }
  if (hud.currentHint === "move" && sim.s.stats.distance > 2.5) hud.clearHint("move");
  if (hud.currentHint === "aim" && sim.s.player.aim > 0.9) hud.clearHint("aim");
  // a scripted player gets back up on its own
  if (driver && sim.s.phase === "dead" && sim.s.phaseT > 1.6) retry();
}

function start(): void {
  if (mode === "play") return;
  audio.start();
  audio.setPaused(false);
  screens.show(sim.s.phase === "dead" ? "dead" : "none");
  hud.show(true);
  if (mode === "title") hud.setHint("move", 14);
  mode = "play";
  // with a scripted player at the controls a stray mouse must not turn the view
  input.enabled = !driver || viaDom;
  if (!driver && !params.has("nolock")) input.requestLock();
}

function pause(): void {
  if (mode !== "play" || sim.s.phase !== "play") return;
  mode = "pause";
  input.enabled = false;
  input.release();
  if (document.pointerLockElement) document.exitPointerLock();
  audio.setPaused(true);
  screens.show("pause");
}

function retry(): void {
  if (sim.s.phase !== "dead" || sim.s.phaseT < 1.4) return;
  sim.retry();
  for (const ev of sim.events) onEvent(ev);
  sim.events.length = 0;
}

function restart(): void {
  sim.restart();
  for (const ev of sim.events) onEvent(ev);
  sim.events.length = 0;
  hud.setHint("move", 14);
  mode = "title";
  start();
}

input.onLock = (locked) => {
  if (!locked && input.everLocked) pause();
};
input.onAnyKey = (code) => {
  if (code === "KeyE" && sim.s.phase === "dead") retry();
  // Esc with the pointer captured is taken by the browser (it frees the pointer,
  // which pauses the game); P pauses either way
  if (code === "KeyP" || (code === "Escape" && !input.locked)) {
    if (mode === "play") pause();
    else if (mode === "pause") start();
  }
};
window.addEventListener("mousedown", (e) => {
  if (e.button !== 0) return;
  if (mode === "title" || mode === "pause") start();
  else if (sim.s.phase === "dead") retry();
  else if (sim.s.phase === "clear" && sim.s.phaseT > 1.6) restart();
  else if (mode === "play" && !driver && !input.locked && !params.has("nolock")) input.requestLock();
});
window.addEventListener("resize", () => view.resize());

screens.show("title");

const dev = params.has("dev") ? document.createElement("div") : null;
if (dev) {
  dev.id = "dev";
  document.body.appendChild(dev);
}

let last = performance.now();
let acc = 0;
let fps = 60;

function render(real: number, alpha: number): void {
  view.frame(alpha, real);
  hud.update(sim.s, real);
  const p = sim.s.player;
  audio.update(real, sim, {
    x: view.camera.position.x,
    y: view.camera.position.y,
    z: view.camera.position.z,
    yaw: p.yaw,
    indoor: view.indoorAmount,
  });
  if (dev) {
    const info = view.info();
    const hunting = sim.s.enemies.filter((e) => e.mode === "chase" || e.mode === "windup").map((e) => e.id);
    dev.textContent =
      `${fps.toFixed(0)} fps  ${info.calls} calls  ${(info.triangles / 1000).toFixed(0)}k tris\n` +
      `pos ${p.x.toFixed(1)}, ${p.z.toFixed(1)}  yaw ${p.yaw.toFixed(2)}  ${sim.s.zone}  t=${sim.s.time.toFixed(1)}\n` +
      `hp ${p.hp}  ammo ${p.ammo}  cp ${sim.s.checkpoint}  hunting [${hunting.join(" ")}]\n` +
      (driver ? driver.status() : "");
  }
}

function tick(now: number): void {
  requestAnimationFrame(tick);
  const real = Math.min(0.1, (now - last) / 1000);
  last = now;
  fps += (1 / Math.max(real, 1e-3) - fps) * 0.05;
  if (mode === "play") {
    acc += real * speed;
    const cap = Math.ceil(6 * speed);
    let n = 0;
    while (acc >= DT && n < cap) {
      stepOnce();
      acc -= DT;
      n++;
    }
    if (n === cap) acc = 0;
  }
  render(real, mode === "play" ? Math.min(1, acc / DT) : 1);
}
requestAnimationFrame(tick);

// ---------------------------------------------------------------- dev / test hooks
const api = {
  sim,
  view,
  hud,
  input,
  audio,
  log,
  get mode(): Mode {
    return mode;
  },
  get steps(): number {
    return steps;
  },
  start,
  setSpeed(v: number): void {
    speed = v;
  },
  setDriver(d: Driver | null): void {
    driver = d;
  },
  get bot(): Bot | null {
    return bot;
  },
  /** Advance the game without waiting for animation frames (background tabs, tests). */
  advance(seconds: number, renderFrame = true): void {
    const n = Math.round(seconds / DT);
    for (let i = 0; i < n && mode === "play"; i++) stepOnce();
    if (renderFrame) render(DT, 1);
  },
  teleport(x: number, z: number, yaw?: number): void {
    const p = sim.s.player;
    p.x = p.px = x;
    p.z = p.pz = z;
    if (yaw !== undefined) p.yaw = p.bodyYaw = yaw;
    view.reset();
  },
  state(): Record<string, unknown> {
    const s = sim.s;
    const p = s.player;
    return {
      mode,
      phase: s.phase,
      time: Math.round(s.time * 10) / 10,
      zone: s.zone,
      checkpoint: s.checkpoint,
      x: Math.round(p.x * 100) / 100,
      z: Math.round(p.z * 100) / 100,
      yaw: Math.round(p.yaw * 1000) / 1000,
      hp: p.hp,
      ammo: p.ammo,
      hasGun: p.hasGun,
      bridge: s.bridge.state,
      prompt: s.prompt?.id ?? null,
      stats: s.stats,
      hunting: s.enemies.filter((e) => e.mode === "chase" || e.mode === "windup" || e.mode === "recover").map((e) => e.id),
      dead: s.enemies.filter((e) => e.mode === "dead").map((e) => e.id),
      driver: driver ? driver.status() : null,
      fps: Math.round(fps),
      render: view.info(),
      doors: Object.keys(s.doors),
      used: Object.keys(s.used),
      aim: Math.round(p.aim * 100) / 100,
      locked: input.locked,
      screen: screens.kind,
      audio: audio.levels(),
      sounds: audio.counts,
    };
  },
};
(window as unknown as { __shio: typeof api }).__shio = api;

const botRoute = params.get("bot");
if (botRoute === "normal" || botRoute === "pacifist") {
  const plan = params.get("bridge");
  bot = new Bot(botRoute, {
    aim: params.get("aim") === "head" ? "head" : "body",
    bridge: plan === "lure" || plan === "shoot" ? plan : "hide",
  });
  viaDom = params.get("via") === "dom";
  driver = viaDom ? new DomBridge(bot, input, canvas) : bot;
}

if (params.has("autostart")) start();
