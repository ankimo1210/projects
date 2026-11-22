// The game itself: a deterministic fixed-step simulation with no DOM and no
// three.js. The view reads `sim.s` and drains `sim.events`; the keyboard, the
// mouse and the test bot all drive it through `step(input)` and `applyLook`.

import { camDir, updateCamera } from "./camera";
import {
  approach,
  approachAngle,
  clamp,
  fwdX,
  fwdZ,
  inRect,
  lerp,
  pushOut,
  rayBox,
  rayCylinder,
  raySphere,
  rightX,
  rightZ,
  rngNext,
  segRect,
  wrapAngle,
  yawTo,
} from "./geom";
import type { Box } from "./geom";
import { buildLevel } from "./level";
import { NavGrid } from "./nav";
import type {
  EnemyDef,
  EnemyMode,
  EnemyState,
  InputFrame,
  InteractDef,
  Level,
  SimEvent,
  SimState,
  Surface,
  VocalKind,
  ZoneName,
} from "./types";

export const DT = 1 / 60;

export const TUNE = {
  walk: 1.95,
  run: 4.3,
  aimWalk: 1.1,
  playerR: 0.35,
  enemyR: 0.32,
  navR: 0.36,
  maxHp: 100,
  hitDamage: 25,
  hurtInvuln: 0.8,
  retryMinHp: 60,
  // how far a sound carries (metres)
  noiseWalk: 2.4,
  noiseRun: 10.5,
  noiseShot: 46,
  noiseBridge: 34,
  noiseCry: 9,
  noiseDoor: 5,
  // enemy senses
  viewRange: 13.5,
  viewHalfFov: 1.08,
  chaseRange: 18,
  chaseHalfFov: 1.75,
  prox: 1.7,
  instantRange: 3.4,
  // enemy speeds
  wanderSpeed: 0.6,
  investigateSpeed: 1.05,
  hurrySpeed: 1.8,
  chaseSpeed: 2.5,
  attackRange: 1.3,
  strikeRange: 1.62,
  windup: 0.45,
  recover: 0.95,
  stagger: 0.95,
  enemyHp: 2,
  searchTime: 5.5,
  bridgeTime: 12,
  gunAmmo: 5,
  ammoBox: 3,
  medkit: 50,
  fireCooldown: 0.55,
};

const PRI_STEP = 1;
const PRI_CRY = 2;
const PRI_BRIDGE = 2;
const PRI_SHOT = 3;

const HEAD_Y = 1.58;
const HEAD_R = 0.2;
const BODY_R = 0.33;
const BODY_TOP = 1.44;

/** Pitch the camera actually uses (recoil kick included). */
export const viewPitch = (pitch: number, recoil: number): number => pitch + recoil * 0.035;

export class Sim {
  readonly level: Level;
  readonly nav: NavGrid;
  s: SimState;
  events: SimEvent[] = [];
  private saved: SimState;
  private opaques: Box[] = [];
  private solids: Box[] = [];
  private readonly tmp = { x: 0, z: 0 };
  private readonly rng: { seed: number };

  constructor(seed = 20260218) {
    this.level = buildLevel();
    this.nav = new NavGrid(this.level.bounds, 0.25);
    this.rng = { seed };
    this.s = this.initialState(seed);
    this.syncDynamic();
    this.snapCamera();
    this.saved = structuredClone(this.s);
  }

  // ------------------------------------------------------------ setup

  private spawnEnemy(def: EnemyDef, dormant: boolean): EnemyState {
    return {
      id: def.id,
      x: def.x,
      z: def.z,
      px: def.x,
      pz: def.z,
      yaw: def.yaw,
      hp: TUNE.enemyHp,
      mode: dormant ? "dormant" : "home",
      modeT: 0,
      aware: 0,
      sees: false,
      tx: def.x,
      tz: def.z,
      noisePri: 0,
      goSpeed: TUNE.investigateSpeed,
      lostT: 0,
      path: null,
      pathI: 0,
      repathT: 0,
      patrolI: 0,
      patrolDir: 1,
      waitT: 1 + (def.look % 3),
      gait: def.look * 1.3,
      stride: 0,
      speed: 0,
      vocalT: 2 + ((def.look * 37) % 50) / 10,
      searchYaw: def.yaw,
      struck: false,
    };
  }

  private initialState(seed: number): SimState {
    const st = this.level.start;
    return {
      time: 0,
      phase: "play",
      phaseT: 0,
      seed,
      player: {
        x: st.x,
        z: st.z,
        px: st.x,
        pz: st.z,
        vx: 0,
        vz: 0,
        yaw: st.yaw,
        pitch: -0.06,
        bodyYaw: st.yaw,
        hp: TUNE.maxHp,
        hurtT: 0,
        hasGun: false,
        ammo: 0,
        aiming: false,
        aim: 0,
        fireCd: 0,
        stride: 0,
        gait: 0,
        speed: 0,
        running: false,
        recoil: 0,
        surface: "tile",
      },
      enemies: this.level.enemies.map((d) => this.spawnEnemy(d, d.dormant)),
      used: {},
      doors: {},
      fired: {},
      bridge: { state: "up", t: 0, noiseT: 0 },
      cam: { x: st.x, y: 2, z: st.z, dist: 2.5, side: 0.55 },
      prompt: null,
      message: null,
      zone: "terminal",
      checkpoint: "start",
      timers: [],
      stats: { shots: 0, hits: 0, kills: 0, damage: 0, deaths: 0, distance: 0, detections: 0 },
    };
  }

  /** Push door / bridge state into the colliders and rebuild the nav grid. */
  syncDynamic(): void {
    const { dyn, boxes } = this.level;
    for (const id of Object.keys(dyn)) {
      const b = dyn[id] as Box;
      if (id === "bridgeGate") b.on = this.s.bridge.state !== "down";
      else b.on = !this.s.doors[id];
    }
    this.opaques = boxes.filter((b) => b.on && b.opaque);
    this.solids = boxes.filter((b) => b.on && b.solid);
    this.nav.rebuild(boxes, TUNE.navR);
  }

  private snapCamera(): void {
    const p = this.s.player;
    updateCamera(this.s.cam, p.x, p.z, p.yaw, viewPitch(p.pitch, p.recoil), p.aim, this.level.boxes, DT, true);
  }

  private rand(): number {
    this.rng.seed = this.s.seed;
    const v = rngNext(this.rng);
    this.s.seed = this.rng.seed;
    return v;
  }

  // ------------------------------------------------------------ queries

  los(ax: number, az: number, bx: number, bz: number): boolean {
    for (const b of this.opaques) {
      if (segRect(ax, az, bx, bz, b) >= 0) return false;
    }
    return true;
  }

  surfaceAt(x: number, z: number): Surface {
    for (const sz of this.level.surfaces) if (inRect(sz, x, z)) return sz.surface;
    return "asphalt";
  }

  zoneAt(x: number, z: number): ZoneName | null {
    for (const zn of this.level.zones) if (inRect(zn, x, z)) return zn.name;
    return null;
  }

  enemy(id: string): EnemyState | undefined {
    return this.s.enemies.find((e) => e.id === id);
  }

  /** Bridge deck angle factor: 1 = raised, 0 = down. */
  bridgeRaise(): number {
    const b = this.s.bridge;
    if (b.state === "up") return 1;
    if (b.state === "down") return 0;
    const t = clamp(b.t / TUNE.bridgeTime, 0, 1);
    return 1 - t;
  }

  private collide(x: number, z: number, r: number, self: EnemyState | null): [number, number] {
    const out = this.tmp;
    for (let it = 0; it < 3; it++) {
      let hit = false;
      for (const b of this.solids) {
        if (x + r <= b.x0 || x - r >= b.x1 || z + r <= b.z0 || z - r >= b.z1) continue;
        if (pushOut(x, z, r, b, out)) {
          x = out.x;
          z = out.z;
          hit = true;
        }
      }
      if (!hit) break;
    }
    if (self === null) {
      // the player cannot walk through standing bodies
      for (const e of this.s.enemies) {
        if (e.mode === "dead") continue;
        const dx = x - e.x;
        const dz = z - e.z;
        const d = Math.hypot(dx, dz);
        const min = r + TUNE.enemyR;
        if (d < min && d > 1e-4) {
          x = e.x + (dx / d) * min;
          z = e.z + (dz / d) * min;
        }
      }
    }
    return [x, z];
  }

  // ------------------------------------------------------------ input

  /** Turn the view. Positive `dYaw` turns left, positive `dPitch` looks up. */
  applyLook(dYaw: number, dPitch: number): void {
    if (this.s.phase !== "play") return;
    const p = this.s.player;
    p.yaw = wrapAngle(p.yaw + dYaw);
    p.pitch = clamp(p.pitch + dPitch, -1.0, 0.95);
  }

  step(inp: InputFrame): void {
    const s = this.s;
    if (s.phase !== "play") {
      s.phaseT += DT;
      for (const e of s.enemies) {
        e.px = e.x;
        e.pz = e.z;
      }
      s.player.px = s.player.x;
      s.player.pz = s.player.z;
      return;
    }
    s.time += DT;
    this.updatePlayer(inp);
    this.updateWorld();
    this.updateEnemies();
    const p = s.player;
    updateCamera(s.cam, p.x, p.z, p.yaw, viewPitch(p.pitch, p.recoil), p.aim, this.level.boxes, DT);
    this.updatePrompt();
    if (s.message) {
      s.message.ttl -= DT;
      if (s.message.ttl <= 0) s.message = null;
    }
  }

  // ------------------------------------------------------------ player

  private updatePlayer(inp: InputFrame): void {
    const s = this.s;
    const p = s.player;
    p.px = p.x;
    p.pz = p.z;
    p.aiming = inp.aim && p.hasGun;
    p.aim = approach(p.aim, p.aiming ? 1 : 0, DT / 0.16);
    p.fireCd = Math.max(0, p.fireCd - DT);
    p.hurtT = Math.max(0, p.hurtT - DT);
    p.recoil = approach(p.recoil, 0, DT * 4.5);

    let mx = inp.mx;
    let mz = inp.mz;
    const ml = Math.hypot(mx, mz);
    if (ml > 1) {
      mx /= ml;
      mz /= ml;
    }
    const moving = ml > 0.05;
    p.surface = this.surfaceAt(p.x, p.z);
    const wantRun = inp.run && moving && !p.aiming && mz > -0.3;
    let sp = p.aiming ? TUNE.aimWalk : wantRun ? TUNE.run : TUNE.walk;
    if (p.surface === "water") sp *= wantRun ? 0.88 : 0.95;
    if (mz < -0.3) sp *= 0.75;
    const wx = rightX(p.yaw) * mx + fwdX(p.yaw) * mz;
    const wz = rightZ(p.yaw) * mx + fwdZ(p.yaw) * mz;
    const k = Math.min(1, 11 * DT);
    p.vx += (wx * sp - p.vx) * k;
    p.vz += (wz * sp - p.vz) * k;
    if (!moving && Math.hypot(p.vx, p.vz) < 0.05) {
      p.vx = 0;
      p.vz = 0;
    }
    const [nx, nz] = this.collide(p.x + p.vx * DT, p.z + p.vz * DT, TUNE.playerR, null);
    const moved = Math.hypot(nx - p.x, nz - p.z);
    p.x = nx;
    p.z = nz;
    p.speed = moved / DT;
    p.running = wantRun && p.speed > TUNE.walk * 1.2;
    s.stats.distance += moved;

    const strideLen = p.running ? 1.25 : 0.72;
    p.stride += moved;
    p.gait += (moved / strideLen) * Math.PI;
    if (p.stride >= strideLen) {
      p.stride -= strideLen;
      this.events.push({ t: "step", x: p.x, z: p.z, surface: p.surface, run: p.running });
      let radius = p.running ? TUNE.noiseRun : p.aiming ? TUNE.noiseWalk * 0.85 : TUNE.noiseWalk;
      if (p.surface === "water") radius *= p.running ? 1.25 : 1.3;
      else if (p.surface === "metal") radius *= 1.25;
      this.emitNoise(p.x, p.z, radius, PRI_STEP, false);
    }

    if (p.aim > 0.3) p.bodyYaw = approachAngle(p.bodyYaw, p.yaw, 14 * DT);
    else if (p.speed > 0.3) p.bodyYaw = approachAngle(p.bodyYaw, yawTo(p.vx, p.vz), 9 * DT);

    if (inp.fire && p.hasGun && p.aim > 0.75 && p.fireCd <= 0) this.fire();
    if (inp.interact && s.prompt) this.use(s.prompt.id);
  }

  private fire(): void {
    const s = this.s;
    const p = s.player;
    if (p.ammo <= 0) {
      p.fireCd = 0.3;
      this.events.push({ t: "dry" });
      this.emitNoise(p.x, p.z, 3, PRI_STEP, false);
      return;
    }
    p.ammo--;
    p.fireCd = TUNE.fireCooldown;
    s.stats.shots++;

    const spread = 0.004 + Math.min(p.speed, 2) * 0.011;
    const jy = (this.rand() - 0.5) * 2 * spread;
    const jp = (this.rand() - 0.5) * 2 * spread;
    const [dx, dy, dz] = camDir(p.yaw + jy, viewPitch(p.pitch, p.recoil) + jp);
    const c = s.cam;
    const tMin = c.dist * 0.85;

    // 1) what the crosshair is on (camera ray)
    let best = 70;
    for (const b of this.level.boxes) {
      if (!b.on || b.thin || !(b.solid || b.ceil)) continue;
      const t = rayBox(c.x, c.y, c.z, dx, dy, dz, b, 0);
      if (t >= tMin && t < best) best = t;
    }
    if (dy < -1e-5) {
      const tg = c.y / -dy;
      if (tg < best) best = tg;
    }
    for (const e of s.enemies) {
      if (e.mode === "dead") continue;
      const th = raySphere(c.x, c.y, c.z, dx, dy, dz, e.x, HEAD_Y, e.z, HEAD_R);
      if (th >= tMin * 0.5 && th < best) best = th;
      const tb = rayCylinder(c.x, c.y, c.z, dx, dy, dz, e.x, e.z, BODY_R, 0, BODY_TOP);
      if (tb >= tMin * 0.5 && tb < best) best = tb;
    }
    const ax = c.x + dx * best;
    const ay = c.y + dy * best;
    const az = c.z + dz * best;

    // 2) the bullet itself leaves the muzzle and flies to that point
    const mx = p.x + fwdX(p.yaw) * 0.5 + rightX(p.yaw) * 0.18;
    const my = 1.42;
    const mz = p.z + fwdZ(p.yaw) * 0.5 + rightZ(p.yaw) * 0.18;
    let bx = ax - mx;
    let by = ay - my;
    let bz = az - mz;
    const len = Math.hypot(bx, by, bz) || 1;
    bx /= len;
    by /= len;
    bz /= len;
    let hitT = len + 0.3;
    let hit: "none" | "world" | "body" | "head" = best < 70 ? "world" : "none";
    for (const b of this.level.boxes) {
      if (!b.on || b.thin || !(b.solid || b.ceil)) continue;
      const t = rayBox(mx, my, mz, bx, by, bz, b, 0);
      if (t < hitT) {
        hitT = t;
        hit = "world";
      }
    }
    let victim: EnemyState | null = null;
    for (const e of s.enemies) {
      if (e.mode === "dead") continue;
      const th = raySphere(mx, my, mz, bx, by, bz, e.x, HEAD_Y, e.z, HEAD_R);
      if (th < hitT) {
        hitT = th;
        hit = "head";
        victim = e;
      }
      const tb = rayCylinder(mx, my, mz, bx, by, bz, e.x, e.z, BODY_R, 0, BODY_TOP);
      if (tb < hitT) {
        hitT = tb;
        hit = "body";
        victim = e;
      }
    }
    if (hit === "none") hitT = len;
    p.recoil = 1;
    this.events.push({
      t: "shot",
      x: mx,
      y: my,
      z: mz,
      hx: mx + bx * hitT,
      hy: my + by * hitT,
      hz: mz + bz * hitT,
      hit,
    });
    if (victim && (hit === "head" || hit === "body")) {
      s.stats.hits++;
      victim.hp -= hit === "head" ? 2 : 1;
      if (victim.hp <= 0) {
        this.setMode(victim, "dead");
        victim.path = null;
        victim.speed = 0;
        s.stats.kills++;
        this.vocal(victim, "die");
      } else {
        this.setMode(victim, "stagger");
        victim.aware = 1;
        victim.tx = p.x;
        victim.tz = p.z;
        victim.lostT = 0;
        victim.path = null;
        // knocked back along the shot
        const [kx, kz] = this.collide(victim.x + bx * 0.35, victim.z + bz * 0.35, TUNE.enemyR, victim);
        victim.x = kx;
        victim.z = kz;
        this.vocal(victim, "hurt");
      }
    }
    this.emitNoise(p.x, p.z, TUNE.noiseShot, PRI_SHOT, true);
  }

  private use(id: string): void {
    const s = this.s;
    const p = s.player;
    const def = this.level.interactables.find((i) => i.id === id);
    if (!def) return;
    switch (def.kind) {
      case "door":
        s.doors[id] = true;
        s.used[id] = true;
        this.syncDynamic();
        this.events.push({ t: "door", id, x: def.x, z: def.z });
        this.emitNoise(def.x, def.z, TUNE.noiseDoor, PRI_STEP, false);
        break;
      case "examine":
        s.message = { text: def.note ?? "", ttl: 3.6 };
        this.events.push({ t: "locked", id, x: def.x, z: def.z });
        break;
      case "gun":
        p.hasGun = true;
        p.ammo += TUNE.gunAmmo;
        s.used[id] = true;
        this.events.push({ t: "pickup", kind: "gun", id });
        this.events.push({ t: "hint", id: "aim" });
        break;
      case "ammo":
        p.ammo += TUNE.ammoBox;
        s.used[id] = true;
        this.events.push({ t: "pickup", kind: "ammo", id });
        break;
      case "medkit":
        if (p.hp >= TUNE.maxHp) {
          s.message = { text: "体力は減っていない", ttl: 2.2 };
        } else {
          p.hp = Math.min(TUNE.maxHp, p.hp + TUNE.medkit);
          s.used[id] = true;
          this.events.push({ t: "pickup", kind: "medkit", id });
        }
        break;
      case "panel":
        if (s.bridge.state === "up") {
          s.bridge = { state: "lowering", t: 0, noiseT: 0 };
          s.used[id] = true;
          this.events.push({ t: "bridge", phase: "start" });
        }
        break;
      case "exit":
        s.phase = "clear";
        s.phaseT = 0;
        s.prompt = null;
        this.events.push({ t: "clear" });
        break;
    }
  }

  private updatePrompt(): void {
    const s = this.s;
    const p = s.player;
    let best: InteractDef | null = null;
    let bestD = Infinity;
    const fx = fwdX(p.yaw);
    const fz = fwdZ(p.yaw);
    for (const it of this.level.interactables) {
      if (s.used[it.id]) continue;
      const dx = it.x - p.x;
      const dz = it.z - p.z;
      const d = Math.hypot(dx, dz);
      if (d > it.r) continue;
      if (d > 0.9 && (dx * fx + dz * fz) / d < -0.25) continue;
      if (d < bestD) {
        bestD = d;
        best = it;
      }
    }
    s.prompt = best && s.phase === "play" ? { id: best.id, label: best.label } : null;
  }

  // ------------------------------------------------------------ world

  private updateWorld(): void {
    const s = this.s;
    const p = s.player;
    const zone = this.zoneAt(p.x, p.z);
    if (zone) s.zone = zone;

    // the figure behind the fogged glass starts walking once the player moves off
    if (!s.fired["glass"]) {
      const st = this.level.start;
      if (Math.hypot(p.x - st.x, p.z - st.z) > 3.2) {
        s.fired["glass"] = true;
        const e = this.enemy("P1");
        if (e && e.mode === "dormant") {
          this.setMode(e, "home");
          e.waitT = 0;
          e.vocalT = 0.2;
          this.events.push({ t: "cue", id: "glass", x: e.x, z: e.z });
        }
      }
    }

    for (const cp of this.level.checkpoints) {
      if (cp.id === "start" || s.fired[`cp:${cp.id}`]) continue;
      if (inRect(cp.area, p.x, p.z)) {
        s.fired[`cp:${cp.id}`] = true;
        s.checkpoint = cp.id;
        this.saved = structuredClone(s);
        this.events.push({ t: "checkpoint", id: cp.id });
        if (cp.id === "lane") this.events.push({ t: "hint", id: "run" });
      }
    }

    // final chase: a growl in the dark, then lightning shows who is standing there
    if (!s.fired["final"] && s.zone === "forecourt" && p.z < -152.5) {
      s.fired["final"] = true;
      this.events.push({ t: "cue", id: "final", x: 24, z: -164 });
      s.timers.push({ at: s.time + 1.0, id: "finalWake" });
    }

    for (let i = s.timers.length - 1; i >= 0; i--) {
      const tm = s.timers[i];
      if (!tm || tm.at > s.time) continue;
      s.timers.splice(i, 1);
      if (tm.id === "finalWake") {
        this.events.push({ t: "thunder", near: true });
        for (const id of ["F1", "F2", "F3"]) {
          const e = this.enemy(id);
          if (e && e.mode === "dormant") {
            this.alert(e, false);
            e.lostT = -4; // they know where you are for a few seconds
          }
        }
      }
    }

    const br = s.bridge;
    if (br.state === "lowering") {
      br.t += DT;
      br.noiseT -= DT;
      if (br.noiseT <= 0) {
        br.noiseT = 0.5;
        const w = this.level.winch;
        this.emitNoise(w.x, w.z, TUNE.noiseBridge, PRI_BRIDGE, false);
      }
      if (br.t >= TUNE.bridgeTime) {
        br.state = "down";
        this.syncDynamic();
        this.events.push({ t: "bridge", phase: "down" });
      }
    }
  }

  /** A sound at (x, z): enemies in earshot that are not already hunting go and look. */
  emitNoise(x: number, z: number, radius: number, pri: number, hurry: boolean): void {
    for (const e of this.s.enemies) {
      const m = e.mode;
      if (m === "dormant" || m === "dead" || m === "chase" || m === "windup" || m === "recover" || m === "stagger") {
        continue;
      }
      const d = Math.hypot(e.x - x, e.z - z);
      if (d > radius) continue;
      if (d > radius * 0.62 && !this.los(x, z, e.x, e.z)) continue;
      if (m === "search" && d < 3) {
        // already standing at the source: keep looking instead of starting over
        e.modeT = Math.min(e.modeT, 1.5);
        continue;
      }
      if (m === "investigate") {
        if (pri < e.noisePri) continue;
        if (pri === e.noisePri && Math.hypot(e.tx - x, e.tz - z) < 2.5) continue;
      }
      e.tx = x + (this.rand() - 0.5) * 1.2;
      e.tz = z + (this.rand() - 0.5) * 1.2;
      e.noisePri = pri;
      e.goSpeed = hurry ? TUNE.hurrySpeed : TUNE.investigateSpeed;
      e.path = null;
      if (m !== "investigate") {
        this.setMode(e, "investigate");
        this.vocal(e, "suspicious");
      }
    }
  }

  // ------------------------------------------------------------ enemies

  private setMode(e: EnemyState, mode: EnemyMode): void {
    e.mode = mode;
    e.modeT = 0;
  }

  private vocal(e: EnemyState, kind: VocalKind): void {
    this.events.push({ t: "vocal", id: e.id, x: e.x, z: e.z, kind });
    e.vocalT = 3 + this.rand() * 4;
  }

  private alert(e: EnemyState, cry: boolean): void {
    const p = this.s.player;
    this.setMode(e, "chase");
    e.aware = 1;
    e.lostT = 0;
    e.tx = p.x;
    e.tz = p.z;
    e.path = null;
    e.repathT = 0;
    this.s.stats.detections++;
    this.vocal(e, "alert");
    if (cry) this.emitNoise(e.x, e.z, TUNE.noiseCry, PRI_CRY, true);
  }

  private perceive(e: EnemyState): number {
    const p = this.s.player;
    const dx = p.x - e.x;
    const dz = p.z - e.z;
    const d = Math.hypot(dx, dz);
    const hunting = e.mode === "chase" || e.mode === "windup" || e.mode === "recover";
    let range = hunting ? TUNE.chaseRange : TUNE.viewRange;
    if (p.running) range *= 1.2;
    const half = hunting ? TUNE.chaseHalfFov : TUNE.viewHalfFov;
    let sees = false;
    if (d < range) {
      const ang = Math.abs(wrapAngle(yawTo(dx, dz) - e.yaw));
      if (d < TUNE.prox || ang < half) sees = this.los(e.x, e.z, p.x, p.z);
    }
    e.sees = sees;
    if (sees) {
      if (d < TUNE.instantRange) {
        e.aware = 1;
      } else {
        let rate = lerp(2.4, 0.5, (d - TUNE.instantRange) / (range - TUNE.instantRange));
        if (p.running) rate *= 1.4;
        else if (p.speed < 0.2) rate *= 0.7;
        if (e.mode !== "home") rate *= 1.35;
        e.aware = Math.min(1, e.aware + rate * DT);
      }
    } else {
      e.aware = Math.max(0, e.aware - 0.3 * DT);
    }
    return d;
  }

  /** Walk towards a point. Returns true on arrival. */
  private walk(e: EnemyState, tx: number, tz: number, speed: number, turn: number, arrive = 0.12): boolean {
    const dx = tx - e.x;
    const dz = tz - e.z;
    const d = Math.hypot(dx, dz);
    if (d < arrive) return true;
    const want = yawTo(dx, dz);
    e.yaw = approachAngle(e.yaw, want, turn * DT);
    const facing = Math.cos(wrapAngle(want - e.yaw));
    if (facing < 0.25) return false;
    const stepLen = Math.min(d, speed * facing * DT);
    const [nx, nz] = this.collide(e.x + (dx / d) * stepLen, e.z + (dz / d) * stepLen, TUNE.enemyR, e);
    e.x = nx;
    e.z = nz;
    return false;
  }

  /**
   * Follow (and when needed plan) a path to a target. Returns true when the
   * enemy has arrived or cannot get any closer.
   */
  private travel(e: EnemyState, tx: number, tz: number, speed: number, turn: number, arrive: number): boolean {
    if (Math.hypot(tx - e.x, tz - e.z) < arrive) return true;
    e.repathT -= DT;
    const old = e.path;
    const end = old && old.length > 0 ? old[old.length - 1] : undefined;
    const exhausted = !old || e.pathI >= old.length;
    const targetMoved = end ? Math.hypot(end.x - tx, end.z - tz) > 0.8 : true;
    if ((e.repathT <= 0 && (exhausted || targetMoved)) || e.repathT <= -3) {
      e.repathT = 0.35 + this.rand() * 0.1;
      e.path = this.nav.lineFree(e.x, e.z, tx, tz)
        ? [{ x: tx, z: tz }]
        : this.nav.findPath(e.x, e.z, tx, tz, null, 40000);
      e.pathI = 0;
      if (!e.path) e.repathT = 1.0; // no route: do not hammer the planner
    }
    const path = e.path;
    if (!path || e.pathI >= path.length) return true;
    let wp = path[e.pathI];
    while (wp && e.pathI < path.length - 1 && Math.hypot(wp.x - e.x, wp.z - e.z) < 0.28) {
      e.pathI++;
      wp = path[e.pathI];
    }
    if (!wp) return true;
    if (this.walk(e, wp.x, wp.z, speed, turn, 0.15)) e.pathI++;
    return false;
  }

  private updateEnemies(): void {
    const s = this.s;
    const p = s.player;
    for (let i = 0; i < s.enemies.length; i++) {
      const e = s.enemies[i] as EnemyState;
      const def = this.level.enemies[i] as EnemyDef;
      e.px = e.x;
      e.pz = e.z;
      e.modeT += DT;
      if (e.mode === "dead" || e.mode === "dormant") {
        e.speed = 0;
        continue;
      }
      const d = this.perceive(e);

      switch (e.mode) {
        case "home": {
          if (e.sees && e.aware >= 1) {
            this.alert(e, true);
            break;
          }
          if (e.sees && e.aware >= 0.35) {
            this.setMode(e, "suspicious");
            e.tx = p.x;
            e.tz = p.z;
            this.vocal(e, "suspicious");
            break;
          }
          e.noisePri = 0;
          if (def.patrol.length >= 2) {
            if (e.waitT > 0) {
              e.waitT -= DT;
            } else {
              const pt = def.patrol[e.patrolI] ?? def.patrol[0];
              if (pt && this.travel(e, pt.x, pt.z, TUNE.wanderSpeed, 2.4, 0.35)) {
                e.waitT = 1.2 + this.rand() * 2.4;
                e.path = null;
                if (def.pingPong) {
                  if (e.patrolI + e.patrolDir < 0 || e.patrolI + e.patrolDir >= def.patrol.length) e.patrolDir = -e.patrolDir;
                  e.patrolI += e.patrolDir;
                } else {
                  e.patrolI = (e.patrolI + 1) % def.patrol.length;
                }
              }
            }
          } else if (Math.hypot(def.x - e.x, def.z - e.z) > 0.5) {
            this.travel(e, def.x, def.z, TUNE.wanderSpeed, 2.4, 0.3);
          } else {
            e.yaw = approachAngle(e.yaw, def.yaw, 1.2 * DT);
          }
          break;
        }
        case "suspicious": {
          if (e.sees) {
            e.tx = p.x;
            e.tz = p.z;
          }
          e.yaw = approachAngle(e.yaw, yawTo(e.tx - e.x, e.tz - e.z), 2.6 * DT);
          if (e.aware >= 1 && e.sees) this.alert(e, true);
          else if (e.aware < 0.12) this.setMode(e, "home");
          else if (e.modeT > 2.6) {
            // it did not make you out: it comes over to look
            e.noisePri = PRI_STEP;
            e.goSpeed = TUNE.investigateSpeed;
            e.path = null;
            this.setMode(e, "investigate");
            e.modeT = 1; // skip the startled pause
          }
          break;
        }
        case "investigate": {
          if (e.sees && e.aware >= 1) {
            this.alert(e, true);
            break;
          }
          if (e.modeT < 0.55) {
            e.yaw = approachAngle(e.yaw, yawTo(e.tx - e.x, e.tz - e.z), 3.2 * DT);
          } else if (this.travel(e, e.tx, e.tz, e.goSpeed, 3.4, 0.9) || e.modeT > 40) {
            this.setMode(e, "search");
            e.searchYaw = e.yaw + (this.rand() - 0.5) * 3;
            e.path = null;
          }
          break;
        }
        case "search": {
          if (e.sees && e.aware >= 1) {
            this.alert(e, true);
            break;
          }
          if (Math.abs(wrapAngle(e.searchYaw - e.yaw)) < 0.1) {
            if (this.rand() < DT * 1.4) e.searchYaw = e.yaw + (this.rand() - 0.5) * 4.2;
          } else {
            e.yaw = approachAngle(e.yaw, e.searchYaw, 1.6 * DT);
          }
          if (e.modeT > TUNE.searchTime) {
            e.noisePri = 0;
            e.path = null;
            this.setMode(e, "home");
            e.waitT = 0.5;
          }
          break;
        }
        case "chase": {
          if (e.sees) {
            e.lostT = 0;
            e.tx = p.x;
            e.tz = p.z;
          } else {
            e.lostT += DT;
            if (e.lostT < 1.2) {
              e.tx = p.x;
              e.tz = p.z;
            }
          }
          if (e.sees && d < TUNE.attackRange) {
            this.setMode(e, "windup");
            e.struck = false;
            this.vocal(e, "attack");
            break;
          }
          const arrived = this.travel(e, e.tx, e.tz, TUNE.chaseSpeed, 5.5, 0.6);
          if ((arrived && !e.sees && e.lostT > 0.4) || e.lostT > 9) {
            this.setMode(e, "search");
            e.searchYaw = e.yaw + (this.rand() - 0.5) * 3;
            e.path = null;
            this.vocal(e, "search");
          }
          break;
        }
        case "windup": {
          e.yaw = approachAngle(e.yaw, yawTo(p.x - e.x, p.z - e.z), 6.5 * DT);
          this.walk(e, p.x, p.z, 0.6, 6.5, TUNE.playerR + TUNE.enemyR + 0.05);
          if (e.modeT >= TUNE.windup) {
            const ang = Math.abs(wrapAngle(yawTo(p.x - e.x, p.z - e.z) - e.yaw));
            const hit = d < TUNE.strikeRange && ang < 1.0 && this.los(e.x, e.z, p.x, p.z);
            this.events.push({ t: "swipe", id: e.id, x: e.x, z: e.z, hit: hit && p.hurtT <= 0 });
            if (hit) this.hurtPlayer(e);
            this.setMode(e, "recover");
          }
          break;
        }
        case "recover": {
          if (e.modeT >= TUNE.recover) {
            this.setMode(e, "chase");
            e.path = null;
            e.repathT = 0;
          }
          break;
        }
        case "stagger": {
          if (e.modeT >= TUNE.stagger) {
            this.setMode(e, "chase");
            e.lostT = 0;
            e.path = null;
            e.repathT = 0;
          }
          break;
        }
      }
      if (s.phase !== "play") return;

      // keep bodies apart
      for (let j = 0; j < s.enemies.length; j++) {
        if (j === i) continue;
        const o = s.enemies[j] as EnemyState;
        if (o.mode === "dead") continue;
        const dx = e.x - o.x;
        const dz = e.z - o.z;
        const dd = Math.hypot(dx, dz);
        if (dd < 0.68 && dd > 1e-4) {
          const push = (0.68 - dd) * 0.5;
          const [nx, nz] = this.collide(e.x + (dx / dd) * push, e.z + (dz / dd) * push, TUNE.enemyR, e);
          e.x = nx;
          e.z = nz;
        }
      }
      {
        const dx = e.x - p.x;
        const dz = e.z - p.z;
        const dd = Math.hypot(dx, dz);
        const min = TUNE.playerR + TUNE.enemyR;
        if (dd < min && dd > 1e-4) {
          const [nx, nz] = this.collide(p.x + (dx / dd) * min, p.z + (dz / dd) * min, TUNE.enemyR, e);
          e.x = nx;
          e.z = nz;
        }
      }

      const moved = Math.hypot(e.x - e.px, e.z - e.pz);
      e.speed = moved / DT;
      e.stride += moved;
      e.gait += (moved / 0.62) * Math.PI;
      if (e.stride >= 0.62) {
        e.stride -= 0.62;
        if (Math.hypot(e.x - p.x, e.z - p.z) < 45) {
          this.events.push({
            t: "estep",
            id: e.id,
            x: e.x,
            z: e.z,
            surface: this.surfaceAt(e.x, e.z),
            fast: e.speed > 1.6,
          });
        }
      }
      e.vocalT -= DT;
      if (e.vocalT <= 0) {
        const calm = e.mode === "home";
        this.vocal(e, calm ? "idle" : "search");
        e.vocalT = calm ? 5 + this.rand() * 7 : 2.6 + this.rand() * 2.6;
      }
    }
  }

  private hurtPlayer(e: EnemyState): void {
    const s = this.s;
    const p = s.player;
    if (p.hurtT > 0) return;
    p.hp -= TUNE.hitDamage;
    p.hurtT = TUNE.hurtInvuln;
    s.stats.damage += TUNE.hitDamage;
    const dx = p.x - e.x;
    const dz = p.z - e.z;
    const d = Math.hypot(dx, dz) || 1;
    p.vx += (dx / d) * 3.2;
    p.vz += (dz / d) * 3.2;
    this.events.push({ t: "hurt", hp: p.hp });
    if (p.hp <= 0) {
      p.hp = 0;
      s.phase = "dead";
      s.phaseT = 0;
      s.prompt = null;
      s.stats.deaths++;
      this.events.push({ t: "death" });
    }
  }

  // ------------------------------------------------------------ retry

  /** Start the whole night over. */
  restart(): void {
    this.s = this.initialState(this.s.seed);
    this.syncDynamic();
    this.snapCamera();
    this.saved = structuredClone(this.s);
    this.events.length = 0;
    this.events.push({ t: "retry" });
  }

  /** Back to the last checkpoint: the living return to their posts, the dead stay dead. */
  retry(): void {
    const cur = this.s;
    const st = structuredClone(this.saved);
    const cp = this.level.checkpoints.find((c) => c.id === st.checkpoint) ?? this.level.checkpoints[0];
    const p = st.player;
    if (cp) {
      p.x = p.px = cp.x;
      p.z = p.pz = cp.z;
      p.yaw = p.bodyYaw = cp.yaw;
    }
    p.pitch = -0.06;
    p.vx = p.vz = 0;
    p.hp = Math.max(p.hp, TUNE.retryMinHp);
    p.hurtT = 0;
    p.aim = 0;
    p.aiming = false;
    p.recoil = 0;
    p.fireCd = 0;
    st.enemies = st.enemies.map((e, i) =>
      e.mode === "dead" ? e : this.spawnEnemy(this.level.enemies[i] as EnemyDef, e.mode === "dormant"),
    );
    if (st.bridge.state === "lowering") {
      st.bridge = { state: "up", t: 0, noiseT: 0 };
      delete st.used["panel"];
    }
    st.timers = [];
    st.time = cur.time;
    st.seed = cur.seed;
    st.stats.deaths = cur.stats.deaths;
    st.stats.shots = cur.stats.shots;
    st.stats.distance = cur.stats.distance;
    st.stats.damage = cur.stats.damage;
    st.phase = "play";
    st.phaseT = 0;
    st.prompt = null;
    st.message = null;
    this.s = st;
    this.syncDynamic();
    this.snapCamera();
    this.events.push({ t: "retry" });
  }
}
