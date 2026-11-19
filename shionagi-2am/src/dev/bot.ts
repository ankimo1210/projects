// A scripted test player, used to prove that the night can be survived.
//
// It plays through the same door as a person: one InputFrame per simulation
// step (keys are on or off, never analogue) plus mouse-look at a limited turn
// rate. It knows the way, as someone on a second attempt would, but about the
// drowned it knows only what a player standing there could: the ones in line of
// sight and the ones close enough to hear.

import { updateCamera } from "../sim/camera";
import { clamp, fwdX, fwdZ, rayBox, rightX, rightZ, wrapAngle, yawTo } from "../sim/geom";
import type { Pt } from "../sim/nav";
import { DT, TUNE, viewPitch } from "../sim/sim";
import type { Sim } from "../sim/sim";
import type { CamState, EnemyState, InputFrame, SimEvent } from "../sim/types";
import type { Driver } from "./driver";

export type RouteName = "normal" | "pacifist";

interface Leg {
  name: string;
  kind: "go" | "use" | "wait";
  /** where to stand */
  x: number;
  z: number;
  arrive: number;
  run: boolean;
  /** interactable to operate ("use") */
  id?: string;
  /** hold here until this is true ("wait") */
  until?: (sim: Sim) => boolean;
  /** skip the leg unless this holds when it comes up */
  when?: (sim: Sim) => boolean;
  /** first leg after this checkpoint: where a retry resumes */
  cp?: string;
  /** do not stop for watchers on this leg */
  bold?: boolean;
  /** open ground to run rings on if something comes for us while we wait here */
  ring?: Pt[];
}

const go = (name: string, x: number, z: number, o: Partial<Leg> = {}): Leg => ({
  name,
  kind: "go",
  x,
  z,
  arrive: 0.7,
  run: false,
  ...o,
});
const use = (name: string, id: string, x: number, z: number, o: Partial<Leg> = {}): Leg => ({
  name,
  kind: "use",
  id,
  x,
  z,
  arrive: 0.3,
  run: false,
  ...o,
});
const wait = (name: string, x: number, z: number, until: (sim: Sim) => boolean, o: Partial<Leg> = {}): Leg => ({
  name,
  kind: "wait",
  x,
  z,
  arrive: 0.4,
  run: false,
  until,
  ...o,
});

/** The sluice yard: points around the winch house, with room to see what is coming. */
const YARD_RING: Pt[] = [
  { x: 11.4, z: -115.6 },
  { x: 16.5, z: -115.5 },
  { x: 21.8, z: -115.8 },
  { x: 26.6, z: -119.0 },
  { x: 22.0, z: -121.5 },
  { x: 26.4, z: -125.2 },
  { x: 21.8, z: -126.6 },
  { x: 16.5, z: -126.7 },
  { x: 11.4, z: -126.6 },
  { x: 9.9, z: -121.2 },
  { x: 12.0, z: -129.9 },
  { x: 20.4, z: -129.9 },
];

const hurt = (sim: Sim): boolean => sim.s.player.hp <= 50;
const bridgeDown = (sim: Sim): boolean => sim.s.bridge.state === "down";

function terminal(): Leg[] {
  return [
    go("待合ホールを横切る", 4.3, -5.5),
    use("職員通路の扉を開ける", "D1", 5.05, -5.5),
    go("職員通路を奥へ", 7.6, -12.2),
    use("裏口を開ける", "D2", 13.25, -12.0),
    go("搬入路に出る", 16.2, -12.0),
  ];
}

/** The three ways through the twelve seconds while the footbridge comes down. */
export type BridgePlan = "hide" | "lure" | "shoot";

function sluice(armed: boolean, plan: BridgePlan): Leg[] {
  const legs: Leg[] = [go("水門管理所の門へ", 11.5, -108.8, { cp: "junction" }), go("構内に入る", 11.6, -112.6)];
  if (armed) legs.push(use("詰所の弾を拾う", "ammo", 12.45, -111.9));
  legs.push(go("巻上機小屋の西を抜ける", 11.0, -126.2), use("操作盤で橋を下ろす", "panel", 9.0, -129.95));
  if (plan === "hide") {
    // out of sight behind the winch house until they have come, looked and gone
    legs.push(wait("小屋の陰で橋が降りるのを待つ", 10.6, -129.4, bridgeDown, { ring: YARD_RING }));
  } else if (plan === "lure") {
    // stand where the ones drawn by the noise will see us, then lead them round the house
    legs.push(wait("わざと姿を見せて小屋を回り込む", 24.6, -118.4, bridgeDown, { ring: YARD_RING, bold: true }));
  } else {
    // hold the bridge head and shoot whatever comes
    legs.push(wait("橋のたもとで迎え撃つ", 21.9, -129.4, bridgeDown, { ring: YARD_RING, bold: true }));
  }
  legs.push(
    go("岸壁を東へ", 21.6, -130.2),
    go("橋のたもとへ", 24.25, -131.2),
    go("水門管理橋を渡る", 24.25, -146.6),
    go("警察署の前庭に入る", 24.25, -151.2, { cp: "forecourt", bold: true }),
    go("植え込みの東を回る", 28.9, -155.6, { bold: true }),
    go("植え込みの東を回る", 28.9, -163.2, { bold: true }),
    go("土のうの切れ目を抜ける", 24.25, -168.4, { bold: true }),
    use("警察署の玄関に手をかける", "exit", 24.25, -172.5, { bold: true }),
  );
  return legs;
}

/** Main street: pick up the revolver on the patrol car and shoot what blocks the way. */
function normalRoute(plan: BridgePlan): Leg[] {
  return [
    ...terminal(),
    go("搬入路の北端へ", 16.0, -20.2, { cp: "lane" }),
    go("駅前広場へ出る", 12.4, -22.9),
    go("商店街のアーチへ", 3.4, -25.6),
    go("パトカーの脇へ", 4.15, -32.6),
    use("拳銃を拾う", "gun", 4.15, -34.4),
    go("なぎさ通りを北へ", 3.6, -41.0),
    use("救急箱を使う", "medkitB", -2.3, -45.7, { when: hurt }),
    go("なぎさ通りを北へ", 3.7, -46.5),
    go("なぎさ通りを北へ", 3.9, -58.0),
    go("箱トラックの東を抜ける", 3.6, -66.0),
    go("がれきの東を抜ける", 1.6, -73.5),
    go("タクシーの西を抜ける", 0.6, -80.0),
    go("土のうの切れ目へ", 3.4, -90.0),
    go("土のうの切れ目を抜ける", 3.4, -95.2),
    go("通行止めの交差点へ", 3.2, -102.6),
    go("交差点を東へ", 7.0, -106.9),
    ...sluice(true, plan),
  ];
}

/** Back alley: never touches the revolver, relies on walls, patience and timing. */
function pacifistRoute(plan: BridgePlan): Leg[] {
  return [
    ...terminal(),
    go("搬入路の北端で広場をうかがう", 16.1, -20.0, { cp: "lane" }),
    go("裏路地へ入る", 15.3, -26.6),
    go("裏路地を北へ", 15.3, -40.0),
    go("裏路地を北へ", 15.6, -54.2),
    use("救急箱を使う", "medkitA", 18.2, -56.6, { when: hurt }),
    go("くの字を抜ける", 18.4, -60.4),
    go("くぼみの前を静かに通る", 17.75, -72.5),
    go("裏路地を北へ", 18.3, -90.0),
    go("裏路地の出口へ", 18.4, -102.6),
    go("交差点に出る", 17.2, -106.8),
    ...sluice(false, plan),
  ];
}

const isHunting = (e: EnemyState): boolean =>
  e.mode === "chase" || e.mode === "windup" || e.mode === "recover" || e.mode === "stagger";

/** How far away the dragging steps and voices carry to the player's ears. */
const HEAR = 14;
/** How far a figure can be made out in the dark. */
const SEE = 30;
const TURN = 6.0; // rad/s, a quick but human flick of the mouse
const TURN_PITCH = 3.0;
const LEVEL = -0.06;
const HEAD_Y = 1.58;
const CHEST_Y = 1.12;
const ENGAGE = 7.5;

export interface BotOptions {
  /** "head" is one shot per kill; "body" is the cautious centre-of-mass shot (two per kill) */
  aim?: "head" | "body";
  /** what to do while the footbridge comes down (default: hide) */
  bridge?: BridgePlan;
}

export class Bot implements Driver {
  readonly route: RouteName;
  readonly armed: boolean;
  readonly events: string[] = [];
  private legs: Leg[];
  private i = 0;
  private legT = 0;
  private path: Pt[] | null = null;
  private pathI = 0;
  private replanT = 0;
  private goalX = NaN;
  private goalZ = NaN;
  private field: Float32Array | null = null;
  private stamped: number[] = [];
  private known: EnemyState[] = [];
  private hunters: EnemyState[] = [];
  private holdT = 0;
  private commitT = 0;
  private steady = 0;
  private engageT = 0;
  private pressT = 0;
  private stuckT = 0;
  private stuckX = 0;
  private stuckZ = 0;
  private nudgeT = 0;
  private nudgeDir = 1;
  private wasPlay = true;
  private scratch: CamState = { x: 0, y: 0, z: 0, dist: 0, side: 0 };
  private note = "";
  private holding: string | null = null;
  private holdMin = 0;
  private fleeTo: Pt | null = null;
  private fleeT = 0;
  private readonly aimY: number;
  private readonly aimR: number;
  /** how the view is turned; replaced when the bot is wired through real DOM events */
  look: (sim: Sim, dYaw: number, dPitch: number) => void = (sim, dYaw, dPitch) => sim.applyLook(dYaw, dPitch);
  /** seconds spent standing still waiting for a watcher to turn away */
  heldTotal = 0;
  /** closest any hunting enemy came, per zone */
  closest: Record<string, number> = {};

  constructor(route: RouteName, opts: BotOptions = {}) {
    this.route = route;
    this.armed = route === "normal";
    const plan = opts.bridge ?? "hide";
    this.legs = route === "normal" ? normalRoute(plan) : pacifistRoute(plan);
    const head = (opts.aim ?? "body") === "head";
    this.aimY = head ? HEAD_Y : CHEST_Y;
    this.aimR = head ? 0.1 : 0.2;
  }

  status(): string {
    const leg = this.legs[this.i];
    return `bot:${this.route} [${Math.min(this.i + 1, this.legs.length)}/${this.legs.length}] ${leg ? leg.name : "done"}${this.note ? " — " + this.note : ""}`;
  }

  get legIndex(): number {
    return this.i;
  }

  get legName(): string {
    return this.legs[this.i]?.name ?? "done";
  }

  observe(ev: SimEvent, sim: Sim): void {
    const t = sim.s.time.toFixed(1);
    switch (ev.t) {
      case "checkpoint":
        this.events.push(`${t} checkpoint ${ev.id}`);
        break;
      case "pickup":
        this.events.push(`${t} pickup ${ev.kind}`);
        break;
      case "door":
        this.events.push(`${t} door ${ev.id}`);
        break;
      case "shot":
        this.events.push(`${t} shot → ${ev.hit}`);
        break;
      case "hurt":
        this.events.push(`${t} HURT hp=${ev.hp} (${this.legName})`);
        break;
      case "death":
        this.events.push(`${t} DEATH (${this.legName})`);
        break;
      case "retry":
        this.events.push(`${t} retry from ${sim.s.checkpoint}`);
        break;
      case "bridge":
        this.events.push(`${t} bridge ${ev.phase}`);
        break;
      case "cue":
        this.events.push(`${t} cue ${ev.id}`);
        break;
      case "vocal":
        if (ev.kind === "alert") this.events.push(`${t} spotted by ${ev.id} (${this.legName})`);
        break;
      case "clear":
        this.events.push(`${t} CLEAR`);
        break;
      default:
        break;
    }
  }

  // ------------------------------------------------------------ senses

  private sense(sim: Sim): void {
    const p = sim.s.player;
    this.known.length = 0;
    this.hunters.length = 0;
    for (const e of sim.s.enemies) {
      if (e.mode === "dead") continue;
      const d = Math.hypot(e.x - p.x, e.z - p.z);
      if (d < HEAR || (d < SEE && sim.los(p.x, p.z, e.x, e.z))) {
        this.known.push(e);
        if (isHunting(e)) {
          this.hunters.push(e);
          const zone = sim.s.zone;
          if (d < (this.closest[zone] ?? Infinity)) this.closest[zone] = Math.round(d * 100) / 100;
        }
      }
    }
  }

  /** Would something that has not noticed us yet see a person standing at (x, z)? */
  private watcher(sim: Sim, x: number, z: number): EnemyState | null {
    for (const e of this.known) {
      if (isHunting(e) || e.mode === "dormant") continue;
      const dx = x - e.x;
      const dz = z - e.z;
      const d = Math.hypot(dx, dz);
      if (d > TUNE.viewRange + 0.5) continue;
      if (e.mode === "home" && d > TUNE.prox + 0.4) {
        // calm ones only see ahead; the ones already looking for something turn all the time
        const ang = Math.abs(wrapAngle(yawTo(dx, dz) - e.yaw));
        if (ang > TUNE.viewHalfFov + 0.25) continue;
      }
      if (sim.los(e.x, e.z, x, z)) return e;
    }
    return null;
  }

  /** Extra path cost around everything we know about, so routes keep their distance. */
  private danger(sim: Sim): Float32Array {
    const nav = sim.nav;
    const f = (this.field ??= new Float32Array(nav.w * nav.h));
    for (const idx of this.stamped) f[idx] = 0;
    this.stamped.length = 0;
    const c = nav.cell;
    for (const e of this.known) {
      const hunting = isHunting(e);
      const R = e.mode === "dormant" ? 1.3 : hunting ? 2.8 : 3.6;
      const peak = hunting ? 10 : 7;
      const i0 = Math.max(1, Math.floor((e.x - R - nav.ox) / c));
      const i1 = Math.min(nav.w - 2, Math.ceil((e.x + R - nav.ox) / c));
      const j0 = Math.max(1, Math.floor((e.z - R - nav.oz) / c));
      const j1 = Math.min(nav.h - 2, Math.ceil((e.z + R - nav.oz) / c));
      for (let j = j0; j <= j1; j++) {
        for (let i = i0; i <= i1; i++) {
          const d = Math.hypot(nav.ox + (i + 0.5) * c - e.x, nav.oz + (j + 0.5) * c - e.z);
          if (d >= R) continue;
          const idx = j * nav.w + i;
          const v = peak * (1 - d / R);
          const cur = f[idx] as number;
          if (v > cur) {
            if (cur === 0) this.stamped.push(idx);
            f[idx] = v;
          }
        }
      }
    }
    return f;
  }

  // ------------------------------------------------------------ hands

  /** Turn the view towards a yaw / pitch at mouse speed. Returns the remaining yaw error. */
  private turn(sim: Sim, yaw: number, pitch: number): number {
    const p = sim.s.player;
    const ey = wrapAngle(yaw - p.yaw);
    const ep = pitch - viewPitch(p.pitch, p.recoil);
    this.look(sim, clamp(ey, -TURN * DT, TURN * DT), clamp(ep, -TURN_PITCH * DT, TURN_PITCH * DT));
    return ey;
  }

  /** Keys that move the body towards a point while the view swings round to it. */
  private moveTo(sim: Sim, tx: number, tz: number, run: boolean, out: InputFrame): void {
    const p = sim.s.player;
    const want = yawTo(tx - p.x, tz - p.z);
    const err = this.turn(sim, want, LEVEL);
    const a = Math.abs(err);
    const side = err > 0 ? -1 : 1; // positive yaw is to the left
    if (a < 0.45) out.mz = 1;
    else if (a < 1.2) {
      out.mz = 1;
      out.mx = side;
    } else if (a < 2.2) out.mx = side;
    else out.mz = -1;
    out.run = run;
  }

  private plan(sim: Sim, gx: number, gz: number): void {
    const p = sim.s.player;
    const field = this.known.length > 0 ? this.danger(sim) : null;
    this.path = sim.nav.findPath(p.x, p.z, gx, gz, field, 120000);
    this.pathI = 0;
    this.replanT = 0.4;
  }

  /** Is any point on the next few metres of the planned path in view of a watcher? */
  private aheadWatcher(sim: Sim, reach: number): EnemyState | null {
    const path = this.path;
    if (!path) return null;
    const p = sim.s.player;
    let ax = p.x;
    let az = p.z;
    let left = reach;
    for (let k = this.pathI; k < path.length && left > 0; k++) {
      const b = path[k] as Pt;
      const len = Math.hypot(b.x - ax, b.z - az);
      const n = Math.max(1, Math.ceil(Math.min(len, left) / 0.5));
      for (let s = 1; s <= n; s++) {
        const t = Math.min(1, (s * 0.5) / Math.max(len, 1e-6));
        const w = this.watcher(sim, ax + (b.x - ax) * t, az + (b.z - az) * t);
        if (w) return w;
      }
      left -= len;
      ax = b.x;
      az = b.z;
    }
    return null;
  }

  /** Follow the path to a goal. */
  private follow(sim: Sim, gx: number, gz: number, run: boolean, out: InputFrame): void {
    const p = sim.s.player;
    this.replanT -= DT;
    if (!this.path || this.replanT <= 0 || Math.hypot(gx - this.goalX, gz - this.goalZ) > 0.3) {
      this.goalX = gx;
      this.goalZ = gz;
      this.plan(sim, gx, gz);
    }
    const path = this.path;
    if (!path || path.length === 0) {
      this.moveTo(sim, gx, gz, run, out);
      return;
    }
    while (this.pathI < path.length - 1) {
      const w = path[this.pathI] as Pt;
      if (Math.hypot(w.x - p.x, w.z - p.z) >= 0.4) break;
      this.pathI++;
    }
    const wp = path[this.pathI] as Pt;

    // wedged on a corner or against a body: sidestep
    this.stuckT += DT;
    if (this.stuckT >= 0.8) {
      if (Math.hypot(p.x - this.stuckX, p.z - this.stuckZ) < 0.15) {
        this.nudgeT = 0.35;
        this.nudgeDir = -this.nudgeDir;
        this.path = null;
      }
      this.stuckT = 0;
      this.stuckX = p.x;
      this.stuckZ = p.z;
    }
    this.moveTo(sim, wp.x, wp.z, run, out);
    if (this.nudgeT > 0) {
      this.nudgeT -= DT;
      out.mx = this.nudgeDir;
    }
  }

  // ------------------------------------------------------------ the revolver

  private solveAim(sim: Sim, tx: number, ty: number, tz: number): { yaw: number; pitch: number } {
    const p = sim.s.player;
    const cam = this.scratch;
    Object.assign(cam, sim.s.cam);
    let yaw = p.yaw;
    let pitch = viewPitch(p.pitch, p.recoil);
    for (let k = 0; k < 4; k++) {
      updateCamera(cam, p.x, p.z, yaw, pitch, p.aim, sim.level.boxes, DT, true);
      const dx = tx - cam.x;
      const dy = ty - cam.y;
      const dz = tz - cam.z;
      yaw = yawTo(dx, dz);
      pitch = Math.atan2(dy, Math.hypot(dx, dz));
    }
    return { yaw, pitch };
  }

  /** Nothing solid between the muzzle and the target. */
  private clearShot(sim: Sim, tx: number, ty: number, tz: number, yaw: number): boolean {
    const p = sim.s.player;
    const mx = p.x + fwdX(yaw) * 0.5 + rightX(yaw) * 0.18;
    const my = 1.42;
    const mz = p.z + fwdZ(yaw) * 0.5 + rightZ(yaw) * 0.18;
    let dx = tx - mx;
    let dy = ty - my;
    let dz = tz - mz;
    const len = Math.hypot(dx, dy, dz) || 1;
    dx /= len;
    dy /= len;
    dz /= len;
    for (const b of sim.level.boxes) {
      if (!b.on || b.thin || !(b.solid || b.ceil)) continue;
      if (rayBox(mx, my, mz, dx, dy, dz, b, 0.06) < len) return false;
    }
    return true;
  }

  private pickTarget(sim: Sim): EnemyState | null {
    const p = sim.s.player;
    if (!this.armed || !p.hasGun || p.ammo <= 0) return null;
    let best: EnemyState | null = null;
    let bestD = ENGAGE;
    for (const e of this.hunters) {
      const d = Math.hypot(e.x - p.x, e.z - p.z);
      if (d >= bestD) continue;
      if (!this.clearShot(sim, e.x, this.aimY, e.z, yawTo(e.x - p.x, e.z - p.z))) continue;
      best = e;
      bestD = d;
    }
    return best;
  }

  private fight(sim: Sim, e: EnemyState, out: InputFrame): void {
    const p = sim.s.player;
    const d = Math.hypot(e.x - p.x, e.z - p.z);
    const sol = this.solveAim(sim, e.x, this.aimY, e.z);
    const ey = wrapAngle(sol.yaw - p.yaw);
    const ep = sol.pitch - viewPitch(p.pitch, p.recoil);
    this.look(sim, clamp(ey, -TURN * DT, TURN * DT), clamp(ep, -TURN_PITCH * DT, TURN_PITCH * DT));
    const tol = Math.min(0.04, this.aimR / Math.max(d, 0.5));
    this.steady = Math.abs(ey) < tol && Math.abs(ep) < tol ? this.steady + 1 : 0;
    this.engageT += DT;
    out.aim = true;
    if (this.steady >= 3 && this.engageT > 0.25 && p.aim > 0.9 && p.fireCd <= 0 && p.recoil < 0.02) {
      out.fire = true;
      this.steady = 0;
    }
    this.note = `撃つ: ${e.id} ${d.toFixed(1)}m`;
  }

  // ------------------------------------------------------------ being chased

  /**
   * Nowhere to go yet (the bridge is still coming down) and something is after
   * us: keep moving to whichever piece of open ground we can reach longest
   * before they can, which in practice leads them round the winch house.
   */
  private evade(sim: Sim, ring: Pt[], out: InputFrame): void {
    const p = sim.s.player;
    this.fleeT -= DT;
    if (this.fleeT <= 0 || !this.fleeTo) {
      this.fleeT = 0.5;
      const field = this.danger(sim);
      let best: Pt | null = null;
      let bestScore = -Infinity;
      for (const c of ring) {
        const path = sim.nav.findPath(p.x, p.z, c.x, c.z, field, 30000);
        if (!path) continue;
        let len = 0;
        let squeeze = Infinity;
        let ax = p.x;
        let az = p.z;
        for (const q of path) {
          const seg = Math.hypot(q.x - ax, q.z - az);
          const n = Math.max(1, Math.ceil(seg));
          for (let k = 1; k <= n; k++) {
            const x = ax + ((q.x - ax) * k) / n;
            const z = az + ((q.z - az) * k) / n;
            for (const h of this.hunters) squeeze = Math.min(squeeze, Math.hypot(h.x - x, h.z - z));
          }
          len += seg;
          ax = q.x;
          az = q.z;
        }
        let their = Infinity;
        for (const h of this.hunters) their = Math.min(their, Math.hypot(h.x - c.x, h.z - c.z));
        // seconds in hand on arrival, how tight the way there is, and a little loyalty to the current choice
        const score = their / TUNE.chaseSpeed - len / TUNE.run + Math.min(squeeze, 4) * 0.9 + (c === this.fleeTo ? 0.8 : 0);
        if (score > bestScore) {
          bestScore = score;
          best = c;
        }
      }
      this.fleeTo = best;
    }
    const goal = this.fleeTo;
    if (!goal) return;
    if (Math.hypot(goal.x - p.x, goal.z - p.z) > 0.6) this.follow(sim, goal.x, goal.z, true, out);
    else {
      // stand and watch the nearest one come
      let near: EnemyState | null = null;
      let nd = Infinity;
      for (const h of this.hunters) {
        const d = Math.hypot(h.x - p.x, h.z - p.z);
        if (d < nd) {
          nd = d;
          near = h;
        }
      }
      if (near) this.turn(sim, yawTo(near.x - p.x, near.z - p.z), LEVEL);
    }
    this.note = `回り込む: ${this.hunters.map((e) => e.id).join(" ")}`;
  }

  // ------------------------------------------------------------ the loop

  private resync(sim: Sim): void {
    const cp = sim.s.checkpoint;
    const k = cp === "start" ? 0 : this.legs.findIndex((l) => l.cp === cp);
    this.i = Math.max(0, k);
    this.legT = 0;
    this.path = null;
    this.holdT = 0;
    this.commitT = 0;
  }

  private nextLeg(): void {
    this.i++;
    this.legT = 0;
    this.path = null;
    this.holdT = 0;
    this.pressT = 0;
  }

  step(sim: Sim): InputFrame {
    const out: InputFrame = { mx: 0, mz: 0, run: false, aim: false, fire: false, interact: false };
    const s = sim.s;
    const p = s.player;
    if (s.phase !== "play") {
      this.wasPlay = false;
      return out;
    }
    if (!this.wasPlay) {
      this.wasPlay = true;
      this.resync(sim);
    }
    this.note = "";
    this.sense(sim);

    let leg = this.legs[this.i];
    while (leg && this.legT === 0 && leg.when && !leg.when(sim)) {
      this.nextLeg();
      leg = this.legs[this.i];
    }
    if (!leg) return out;
    this.legT += DT;

    // someone is coming for us: shoot if that opens the way, otherwise run
    const hunted = this.hunters.length > 0;
    const target = hunted ? this.pickTarget(sim) : null;
    if (target) {
      this.fight(sim, target, out);
      return out;
    }
    this.engageT = 0;
    this.steady = 0;

    const dGoal = Math.hypot(leg.x - p.x, leg.z - p.z);
    if (leg.kind === "go" && dGoal < leg.arrive) {
      this.nextLeg();
      return out;
    }
    if (leg.kind === "use" && leg.id) {
      if (s.used[leg.id]) {
        this.nextLeg();
        return out;
      }
      this.pressT -= DT;
      if (s.prompt?.id === leg.id && this.pressT <= 0 && dGoal < 1.0) {
        out.interact = true;
        this.pressT = 0.35;
      }
      if (dGoal < leg.arrive) {
        const it = sim.level.interactables.find((q) => q.id === leg.id);
        if (it) this.turn(sim, yawTo(it.x - p.x, it.z - p.z), LEVEL);
        this.note = "調べる";
        return out;
      }
    }
    if (leg.kind === "wait" && leg.until) {
      if (leg.until(sim)) {
        this.nextLeg();
        return out;
      }
      if (hunted && leg.ring) {
        this.evade(sim, leg.ring, out);
        return out;
      }
      this.fleeTo = null;
      if (dGoal < leg.arrive) {
        this.note = "待機";
        return out;
      }
    }

    let run = leg.run || hunted;
    this.follow(sim, leg.x, leg.z, run, out);

    // unnoticed so far: do not walk into view of something that is looking this way
    if (!hunted && !leg.bold) {
      this.commitT -= DT;
      const here = this.watcher(sim, p.x, p.z);
      let ahead = this.commitT > 0 ? null : this.aheadWatcher(sim, 3.0);
      // having stopped, stay put for a breath rather than twitching forward
      this.holdMin -= DT;
      if (!ahead && !here && this.holdMin > 0 && this.holding) ahead = sim.enemy(this.holding) ?? null;
      if (!here && ahead) {
        this.holdT += DT;
        this.heldTotal += DT;
        if (this.holdT > 16) {
          // it is not going away: go while it is as far off as it will get
          this.commitT = 7;
          this.holdT = 0;
          this.holdMin = 0;
        } else {
          out.mx = 0;
          out.mz = 0;
          out.run = false;
          this.note = `立ち止まる: ${ahead.id} がこちらを向いている`;
          if (this.holding !== ahead.id) {
            this.holding = ahead.id;
            this.holdMin = 1.5;
            this.events.push(`${s.time.toFixed(1)} hold for ${ahead.id} at (${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);
          }
          return out;
        }
      } else {
        if (this.holding) {
          this.events.push(`${s.time.toFixed(1)} move on`);
          this.holding = null;
        }
        this.holdT = Math.max(0, this.holdT - DT * 2);
        if (here) {
          // already in the open: cross quickly unless that would be heard
          let near = Infinity;
          for (const e of this.known) {
            if (e.mode === "dormant") continue;
            near = Math.min(near, Math.hypot(e.x - p.x, e.z - p.z));
          }
          run = near > TUNE.noiseRun * 1.3 + 1.5;
          out.run = run;
          this.note = `見られている: ${here.id}`;
        }
      }
    }
    if (hunted) this.note = `追われている: ${this.hunters.map((e) => e.id).join(" ")}`;
    return out;
  }
}

export interface RunResult {
  cleared: boolean;
  time: number;
  hp: number;
  ammo: number;
  hasGun: boolean;
  stats: Sim["s"]["stats"];
  held: number;
  closest: Record<string, number>;
  events: string[];
  lastLeg: string;
  x: number;
  z: number;
}

/** Play a route to the end (or until time runs out) without any rendering. */
export function runBot(sim: Sim, bot: Bot, maxSeconds: number): RunResult {
  const maxSteps = Math.round(maxSeconds / DT);
  for (let n = 0; n < maxSteps; n++) {
    const inp = bot.step(sim);
    sim.step(inp);
    if (sim.events.length > 0) {
      for (const ev of sim.events) bot.observe(ev, sim);
      sim.events.length = 0;
    }
    if (sim.s.phase === "clear") break;
    if (sim.s.phase === "dead" && sim.s.phaseT > 1.6) {
      sim.retry();
      for (const ev of sim.events) bot.observe(ev, sim);
      sim.events.length = 0;
    }
  }
  const p = sim.s.player;
  return {
    cleared: sim.s.phase === "clear",
    time: sim.s.time,
    hp: p.hp,
    ammo: p.ammo,
    hasGun: p.hasGun,
    stats: { ...sim.s.stats },
    held: bot.heldTotal,
    closest: bot.closest,
    events: bot.events,
    lastLeg: bot.legName,
    x: p.x,
    z: p.z,
  };
}
