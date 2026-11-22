import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { camDir, updateCamera } from "../src/sim/camera";
import { fwdX, fwdZ, yawTo } from "../src/sim/geom";
import { DT, Sim, TUNE, viewPitch } from "../src/sim/sim";
import { NO_INPUT } from "../src/sim/types";
import type { EnemyState, InputFrame } from "../src/sim/types";
import { buildEnemy, poseEnemy } from "../src/view/actors";

const input = (o: Partial<InputFrame>): InputFrame => ({ ...NO_INPUT, ...o });

function run(sim: Sim, seconds: number, inp: InputFrame = NO_INPUT): void {
  const n = Math.round(seconds / DT);
  for (let i = 0; i < n; i++) sim.step(inp);
}

/** Put the player somewhere and settle the camera. */
function place(sim: Sim, x: number, z: number, yaw: number): void {
  const p = sim.s.player;
  p.x = p.px = x;
  p.z = p.pz = z;
  p.yaw = p.bodyYaw = yaw;
  p.pitch = 0;
  p.vx = p.vz = 0;
  sim.step(NO_INPUT);
}

/** Park every enemy except the listed ones far away and asleep. */
function isolate(sim: Sim, keep: string[]): void {
  for (const e of sim.s.enemies) if (!keep.includes(e.id)) e.mode = "dormant";
}

function moveEnemy(e: EnemyState, x: number, z: number, yaw: number): void {
  e.x = e.px = x;
  e.z = e.pz = z;
  e.yaw = yaw;
  e.path = null;
}

/** Point the crosshair at a world point (iterating because the camera is off-axis). */
function aimAt(sim: Sim, tx: number, ty: number, tz: number): void {
  const p = sim.s.player;
  for (let i = 0; i < 6; i++) {
    updateCamera(sim.s.cam, p.x, p.z, p.yaw, viewPitch(p.pitch, p.recoil), p.aim, sim.level.boxes, DT, true);
    const c = sim.s.cam;
    const dx = tx - c.x;
    const dy = ty - c.y;
    const dz = tz - c.z;
    p.yaw = yawTo(dx, dz);
    p.pitch = Math.atan2(dy, Math.hypot(dx, dz)) - p.recoil * 0.035;
  }
  const [fx, fy, fz] = camDir(p.yaw, viewPitch(p.pitch, p.recoil));
  expect(Number.isFinite(fx + fy + fz)).toBe(true);
}

describe("player", () => {
  it("walks and runs at the tuned speeds and stops at walls", () => {
    const sim = new Sim();
    place(sim, -8.5, -2.2, Math.PI / 2); // face west, towards the wall 5.5 m away
    const x0 = sim.s.player.x;
    run(sim, 1, input({ mz: 1 }));
    expect(x0 - sim.s.player.x).toBeGreaterThan(1.6);
    expect(x0 - sim.s.player.x).toBeLessThan(2.0);
    run(sim, 6, input({ mz: 1, run: true }));
    expect(sim.s.player.x).toBeGreaterThan(-14 + TUNE.playerR - 0.01);
    expect(sim.s.player.x).toBeLessThan(-13.5);
  });

  it("opens the staff door with the interact key", () => {
    const sim = new Sim();
    place(sim, 5.0, -5.5, -Math.PI / 2);
    expect(sim.s.prompt?.id).toBe("D1");
    expect(sim.nav.findPath(5, -5.5, 7.5, -5.5)).toBeNull();
    sim.step(input({ interact: true }));
    expect(sim.s.doors["D1"]).toBe(true);
    expect(sim.nav.findPath(5, -5.5, 7.5, -5.5)).not.toBeNull();
    run(sim, 2, input({ mz: 1 }));
    expect(sim.s.player.x).toBeGreaterThan(6.5);
  });

  it("keeps the camera inside the room when backed against a wall", () => {
    const sim = new Sim();
    // back to the south wall of the hall, looking north
    place(sim, -6, -0.4, 0);
    run(sim, 0.5);
    expect(sim.s.cam.z).toBeLessThan(-0.15);
    expect(sim.s.cam.dist).toBeLessThan(0.5);
    // out in the open the boom is at full length
    place(sim, -2, -6, 0);
    run(sim, 2);
    expect(sim.s.cam.dist).toBeGreaterThan(2.4);
  });

  it("moves the camera to the other shoulder when a wall is close on the right", () => {
    const sim = new Sim();
    const p = sim.s.player;
    // the back alley runs north between x = 14.15 and 16.65: hug its east wall
    place(sim, 16.2, -36, 0);
    run(sim, 1.5);
    expect(sim.s.cam.side).toBeLessThan(-0.3); // over the left shoulder
    expect(sim.s.cam.x).toBeLessThan(p.x);
    expect(sim.s.cam.x).toBeGreaterThan(14.15 + 0.1);
    // step across to the west wall: back to the right shoulder, still inside the alley
    place(sim, 14.6, -36, 0);
    run(sim, 1.5);
    expect(sim.s.cam.side).toBeGreaterThan(0.3);
    expect(sim.s.cam.x).toBeLessThan(16.65 - 0.1);
    // while it crosses over, the camera never enters a wall
    place(sim, 16.2, -36, 0);
    for (let i = 0; i < 90; i++) {
      sim.step(NO_INPUT);
      expect(sim.s.cam.x).toBeGreaterThan(14.15 + 0.1);
      expect(sim.s.cam.x).toBeLessThan(16.65 - 0.1);
    }
  });
});

describe("enemies", () => {
  it("notice a player in front of them but not one behind a wall or behind their back", () => {
    const sim = new Sim();
    isolate(sim, ["E4"]);
    const e = sim.enemy("E4") as EnemyState;
    // E4 stands at (-3.2, -66.5) facing north. Stand 4.5 m in front of it.
    place(sim, -3.2, -71.0, Math.PI);
    run(sim, 1.5);
    expect(["chase", "windup", "recover"]).toContain(e.mode);

    const b = new Sim();
    isolate(b, ["E4"]);
    const e2 = b.enemy("E4") as EnemyState;
    place(b, -3.2, -61.5, 0); // 5 m behind its back, standing still
    run(b, 4);
    expect(e2.mode).toBe("home");

    const c = new Sim();
    isolate(c, ["E4"]);
    const e3 = c.enemy("E4") as EnemyState;
    place(c, 3.0, -61.5, 0); // other side of the box truck
    moveEnemy(e3, -3.2, -61.5, -Math.PI / 2); // looking straight at the truck
    run(c, 4);
    expect(e3.mode).toBe("home");
  });

  it("hear running but not walking", () => {
    const walk = new Sim();
    isolate(walk, ["E4"]);
    place(walk, 3.6, -60.5, 0); // walk north past its back, 6.8 m to the side
    run(walk, 4, input({ mz: 1 }));
    expect((walk.enemy("E4") as EnemyState).mode).toBe("home");

    const sprint = new Sim();
    isolate(sprint, ["E4"]);
    place(sprint, 3.6, -60.5, 0);
    run(sprint, 1.5, input({ mz: 1, run: true }));
    expect((sprint.enemy("E4") as EnemyState).mode).not.toBe("home");
  });

  it("hit for a quarter of the health bar and the run restarts from the checkpoint", () => {
    const sim = new Sim();
    isolate(sim, ["E4"]);
    place(sim, -3.2, -68.5, Math.PI);
    let hurt = 0;
    for (let i = 0; i < 60 * 30 && sim.s.phase === "play"; i++) {
      sim.step(NO_INPUT);
      for (const ev of sim.events) if (ev.t === "hurt") hurt++;
      sim.events.length = 0;
    }
    expect(hurt).toBe(4);
    expect(sim.s.phase).toBe("dead");
    sim.retry();
    expect(sim.s.phase).toBe("play");
    expect(sim.s.player.hp).toBe(TUNE.maxHp);
    expect(sim.s.player.x).toBeCloseTo(sim.level.start.x);
    expect(sim.s.stats.deaths).toBe(1);
    expect((sim.enemy("E4") as EnemyState).mode).toBe("home");
  });
});

describe("pistol", () => {
  function armed(): { sim: Sim; e: EnemyState } {
    const sim = new Sim();
    isolate(sim, ["E4"]);
    const p = sim.s.player;
    p.hasGun = true;
    p.ammo = 5;
    const e = sim.enemy("E4") as EnemyState;
    moveEnemy(e, -3.2, -66.5, 0); // back turned
    place(sim, -3.2, -59.5, Math.PI); // 7 m behind it, facing it
    return { sim, e };
  }

  it("needs to be raised before it fires", () => {
    const { sim } = armed();
    sim.step(input({ fire: true }));
    expect(sim.s.stats.shots).toBe(0);
    run(sim, 0.4, input({ aim: true }));
    sim.step(input({ aim: true, fire: true }));
    expect(sim.s.stats.shots).toBe(1);
    expect(sim.s.player.ammo).toBe(4);
  });

  it("drops an enemy with two body shots or one head shot", () => {
    const body = armed();
    run(body.sim, 0.4, input({ aim: true }));
    aimAt(body.sim, body.e.x, 1.1, body.e.z);
    body.sim.step(input({ aim: true, fire: true }));
    expect(body.e.hp).toBe(1);
    expect(body.e.mode).toBe("stagger");
    run(body.sim, 0.7, input({ aim: true }));
    aimAt(body.sim, body.e.x, 1.1, body.e.z);
    body.sim.step(input({ aim: true, fire: true }));
    expect(body.e.mode).toBe("dead");
    expect(body.sim.s.stats.kills).toBe(1);

    const head = armed();
    run(head.sim, 0.4, input({ aim: true }));
    aimAt(head.sim, head.e.x, 1.58, head.e.z);
    head.sim.step(input({ aim: true, fire: true }));
    expect(head.e.mode).toBe("dead");
    expect(head.sim.s.player.ammo).toBe(4);
  });

  it("registers a shot aimed at the temple of a slumped enemy seen in profile", () => {
    const { sim, e } = armed();
    run(sim, 0.4, input({ aim: true }));
    e.mode = "dormant";
    e.yaw = Math.PI / 2;
    const rig = buildEnemy(5); // E4's suit
    rig.root.position.set(e.x, 0, e.z);
    rig.root.rotation.y = e.yaw;
    for (let frame = 0; frame < 60; frame++) poseEnemy(rig, e, frame * DT, DT, 0);

    const temple = rig.head.localToWorld(new Vector3(-0.10, 0.17, -0.035));
    aimAt(sim, temple.x, temple.y, temple.z);
    sim.step(input({ aim: true, fire: true }));
    expect(sim.events).toContainEqual(expect.objectContaining({ t: "shot", hit: "head" }));
  });

  it("clicks when empty and the shot brings others", () => {
    const { sim } = armed();
    const other = sim.enemy("E5") as EnemyState;
    other.mode = "home";
    run(sim, 0.4, input({ aim: true }));
    aimAt(sim, 3, 3, -40); // fire at nothing
    sim.step(input({ aim: true, fire: true }));
    expect(other.mode).toBe("investigate");
    sim.s.player.ammo = 0;
    run(sim, 0.7, input({ aim: true }));
    sim.events.length = 0;
    sim.step(input({ aim: true, fire: true }));
    expect(sim.events.some((e) => e.t === "dry")).toBe(true);
    expect(sim.s.stats.shots).toBe(1);
  });

  it("is blocked by cover between the muzzle and the target", () => {
    const sim = new Sim();
    isolate(sim, ["E4"]);
    const p = sim.s.player;
    p.hasGun = true;
    p.ammo = 5;
    const e = sim.enemy("E4") as EnemyState;
    moveEnemy(e, -3.2, -61.5, 0);
    place(sim, 3.0, -61.5, Math.PI / 2); // the box truck stands between them
    run(sim, 0.4, input({ aim: true }));
    aimAt(sim, e.x, 1.1, e.z);
    sim.step(input({ aim: true, fire: true }));
    expect(e.hp).toBe(TUNE.enemyHp);
    expect(fwdX(p.yaw)).toBeLessThan(0);
    expect(Math.abs(fwdZ(p.yaw))).toBeLessThan(0.5);
  });
});

describe("bridge and ending", () => {
  it("takes the tuned time to come down, calls the yard and then lets the player across", () => {
    const sim = new Sim();
    sim.s.doors["D1"] = sim.s.doors["D2"] = true;
    sim.syncDynamic();
    place(sim, 9, -130.0, Math.PI);
    expect(sim.s.prompt?.id).toBe("panel");
    sim.step(input({ interact: true }));
    expect(sim.s.bridge.state).toBe("lowering");
    run(sim, 3);
    expect((sim.enemy("Y1") as EnemyState).mode).toBe("investigate");
    expect(sim.nav.findPath(22, -130, 24.25, -140)).toBeNull();
    run(sim, TUNE.bridgeTime - 2.9);
    expect(sim.s.bridge.state).toBe("down");
    expect(sim.nav.findPath(22, -130, 24.25, -140)).not.toBeNull();
  });

  it("clears the moment the station door is touched", () => {
    const sim = new Sim();
    isolate(sim, []);
    place(sim, 24.25, -172.6, 0);
    expect(sim.s.prompt?.id).toBe("exit");
    sim.step(input({ interact: true }));
    expect(sim.s.phase).toBe("clear");
    expect(sim.events.some((e) => e.t === "clear")).toBe(true);
  });
});

describe("heard before seen", () => {
  it("the figure outside the glass is audible seconds before its shadow reaches the panes", () => {
    const sim = new Sim();
    const glass = sim.level.props.find((q) => q.k === "glassWall");
    expect(glass && glass.k === "glassWall").toBe(true);
    const x1 = glass && glass.k === "glassWall" ? glass.x1 : 0;
    const p1 = sim.enemy("P1") as EnemyState;
    expect(p1.mode).toBe("dormant");
    expect(p1.x).toBeGreaterThan(x1 + 1.5); // it waits out of sight beyond the end of the glass
    let cueAt = -1;
    let stepAt = -1;
    let shadowAt = -1;
    for (let i = 0; i < 60 * 30 && shadowAt < 0; i++) {
      sim.step(input({ mz: 1 }));
      for (const ev of sim.events) {
        if (ev.t === "cue" && ev.id === "glass") cueAt = sim.s.time;
        if (ev.t === "estep" && ev.id === "P1" && stepAt < 0) stepAt = sim.s.time;
      }
      sim.events.length = 0;
      if (cueAt >= 0 && p1.x < x1 + 0.4) shadowAt = sim.s.time;
    }
    expect(cueAt).toBeGreaterThan(0);
    expect(stepAt).toBeGreaterThan(0);
    expect(shadowAt - cueAt).toBeGreaterThan(1.5);
    expect(shadowAt - stepAt).toBeGreaterThan(1.0);
    // and it then stays close enough to the glass to throw a shadow on it
    expect(Math.abs(p1.z - (glass && glass.k === "glassWall" ? glass.z : 0))).toBeLessThan(1.5);
  });

  it("in the forecourt a voice comes out of the dark a second before anything moves", () => {
    const sim = new Sim();
    isolate(sim, []);
    sim.s.bridge.state = "down";
    sim.syncDynamic();
    place(sim, 24.25, -150.5, 0);
    let cueAt = -1;
    let wakeAt = -1;
    for (let i = 0; i < 60 * 12 && wakeAt < 0; i++) {
      sim.step(input({ mz: 1 }));
      for (const ev of sim.events) {
        if (ev.t === "cue" && ev.id === "final") cueAt = sim.s.time;
        if (ev.t === "thunder" && ev.near) wakeAt = sim.s.time;
      }
      sim.events.length = 0;
      if (wakeAt < 0) expect(sim.s.enemies.filter((e) => e.mode === "chase").length).toBe(0);
    }
    expect(cueAt).toBeGreaterThan(0);
    expect(wakeAt - cueAt).toBeGreaterThan(0.9);
    expect(["F1", "F2", "F3"].every((id) => sim.enemy(id)?.mode === "chase")).toBe(true);
  });
});
