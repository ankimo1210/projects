// The two kinds of people in Shionagi: the ferry terminal's night-shift
// maintenance worker, and the drowned who came back up with the tide. Both are
// assembled from capsules and posed procedurally.

import * as THREE from "three";
import type { EnemyState } from "../sim/types";
import { makeRevolver } from "./town";
import { jacketTexture } from "./textures";

export interface Rig {
  root: THREE.Group;
  body: THREE.Group;
  torso: THREE.Group;
  head: THREE.Group;
  armL: THREE.Group;
  armR: THREE.Group;
  foreL: THREE.Group;
  foreR: THREE.Group;
  legL: THREE.Group;
  legR: THREE.Group;
  shinL: THREE.Group;
  shinR: THREE.Group;
  gun: THREE.Object3D | null;
  /** sea-sparkle clinging to the drowned */
  glimmer: THREE.Points | null;
  mats: THREE.MeshStandardMaterial[];
}

const HIP_Y = 0.93;

interface Palette {
  skin: number;
  top: number;
  bottom: number;
  shoe: number;
  hair: number;
}

function capsule(r: number, len: number, mat: THREE.Material, sx = 1, sz = 1): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(0.01, len - r * 2), 3, 8), mat);
  m.scale.set(sx, 1, sz);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function limb(
  parent: THREE.Object3D,
  x: number,
  y: number,
  upperLen: number,
  lowerLen: number,
  r: number,
  upperMat: THREE.Material,
  lowerMat: THREE.Material,
  endMat: THREE.Material,
  foot: boolean,
): [THREE.Group, THREE.Group] {
  const upper = new THREE.Group();
  upper.position.set(x, y, 0);
  upper.rotation.order = "YXZ";
  const u = capsule(r, upperLen, upperMat);
  u.position.y = -upperLen / 2;
  upper.add(u);
  const lower = new THREE.Group();
  lower.position.y = -upperLen;
  const l = capsule(r * 0.88, lowerLen, lowerMat);
  l.position.y = -lowerLen / 2;
  lower.add(l);
  if (foot) {
    const f = new THREE.Mesh(new THREE.BoxGeometry(r * 1.9, 0.08, 0.26), endMat);
    f.position.set(0, -lowerLen + 0.02, -0.06);
    f.castShadow = true;
    lower.add(f);
  } else {
    const h = new THREE.Mesh(new THREE.SphereGeometry(r * 0.95, 8, 6), endMat);
    h.position.y = -lowerLen - 0.02;
    h.castShadow = true;
    lower.add(h);
  }
  upper.add(lower);
  parent.add(upper);
  return [upper, lower];
}

function buildRig(p: Palette, bulk: number): Rig {
  const mk = (color: number, roughness: number): THREE.MeshStandardMaterial =>
    new THREE.MeshStandardMaterial({ color, roughness, metalness: 0 });
  const skin = mk(p.skin, 0.7);
  const top = mk(p.top, 0.8);
  const bottom = mk(p.bottom, 0.85);
  const shoe = mk(p.shoe, 0.6);
  const hair = mk(p.hair, 0.9);
  const mats = [skin, top, bottom, shoe, hair];

  const root = new THREE.Group();
  root.rotation.order = "YXZ";
  const body = new THREE.Group();
  body.position.y = HIP_Y;
  root.add(body);

  const pelvis = capsule(0.13, 0.34, bottom, 1.25 * bulk, 0.9);
  pelvis.rotation.z = Math.PI / 2;
  pelvis.position.y = 0.02;
  body.add(pelvis);

  const torso = new THREE.Group();
  torso.position.y = 0.08;
  body.add(torso);
  const chest = capsule(0.17, 0.56, top, 1.2 * bulk, 0.82);
  chest.position.y = 0.3;
  torso.add(chest);
  const shoulders = capsule(0.1, 0.5, top, 1, 1);
  shoulders.rotation.z = Math.PI / 2;
  shoulders.position.y = 0.5;
  torso.add(shoulders);

  const head = new THREE.Group();
  head.position.y = 0.62;
  torso.add(head);
  const neck = capsule(0.055, 0.14, skin);
  neck.position.y = 0.03;
  head.add(neck);
  const skull = new THREE.Mesh(new THREE.SphereGeometry(0.118, 14, 10), hair);
  skull.scale.set(0.92, 1.1, 1.0);
  skull.position.y = 0.17;
  skull.castShadow = true;
  head.add(skull);
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 10), skin);
  face.scale.set(0.86, 1.08, 0.8);
  face.position.set(0, 0.155, -0.048);
  head.add(face);
  for (const sx of [-1, 1]) {
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.082, 10, 8), top);
    cap.position.set(sx * 0.235 * bulk, 0.5, 0);
    cap.castShadow = true;
    torso.add(cap);
  }

  const [armL, foreL] = limb(torso, -0.25 * bulk, 0.5, 0.3, 0.29, 0.06, top, top, skin, false);
  const [armR, foreR] = limb(torso, 0.25 * bulk, 0.5, 0.3, 0.29, 0.06, top, top, skin, false);
  const [legL, shinL] = limb(body, -0.105, 0, 0.45, 0.44, 0.088, bottom, bottom, shoe, true);
  const [legR, shinR] = limb(body, 0.105, 0, 0.45, 0.44, 0.088, bottom, bottom, shoe, true);

  return { root, body, torso, head, armL, armR, foreL, foreR, legL, legR, shinL, shinR, gun: null, glimmer: null, mats };
}

// -------------------------------------------------------------------- player

export function buildPlayer(): Rig {
  const rig = buildRig({ skin: 0xc79a7a, top: 0x1c2b45, bottom: 0x232a33, shoe: 0x15171a, hair: 0x16130f }, 1.0);
  // hard hat
  const hatMat = new THREE.MeshStandardMaterial({ color: 0xd9b21a, roughness: 0.45 });
  const hat = new THREE.Mesh(new THREE.SphereGeometry(0.135, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.5), hatMat);
  hat.scale.set(1, 0.95, 1.08);
  hat.position.set(0, 0.2, 0);
  hat.castShadow = true;
  rig.head.add(hat);
  const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.155, 0.018, 14), hatMat);
  brim.position.set(0, 0.205, -0.02);
  brim.scale.set(1, 1, 1.12);
  rig.head.add(brim);
  // reflective bands and the company name across the back
  const band = new THREE.MeshStandardMaterial({ color: 0xc9d2d6, roughness: 0.35, emissive: 0x0d1012 });
  for (const y of [0.2, 0.42]) {
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.212, 0.212, 0.035, 14), band);
    b.scale.set(1, 1, 0.7);
    b.position.y = y;
    rig.torso.add(b);
  }
  const back = new THREE.Mesh(
    new THREE.PlaneGeometry(0.32, 0.16),
    new THREE.MeshStandardMaterial({ map: jacketTexture(), roughness: 0.8, emissive: 0x05070a }),
  );
  back.position.set(0, 0.36, 0.146);
  rig.torso.add(back);
  // chest lamp
  const lamp = new THREE.Mesh(
    new THREE.BoxGeometry(0.07, 0.05, 0.04),
    new THREE.MeshBasicMaterial({ color: 0xfff2d8, toneMapped: false }),
  );
  lamp.position.set(-0.09, 0.44, -0.15);
  rig.torso.add(lamp);
  rig.mats.push(hatMat, band);
  // sidearm (hidden until it is picked up)
  const steel = new THREE.MeshStandardMaterial({ color: 0x23262b, roughness: 0.35, metalness: 0.85 });
  const wood = new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.6 });
  const gun = makeRevolver(steel, wood);
  gun.position.set(0, -0.33, -0.03);
  gun.rotation.x = -Math.PI / 2;
  gun.visible = false;
  rig.foreR.add(gun);
  rig.gun = gun;
  return rig;
}

export interface PlayerPose {
  gait: number;
  speed: number;
  running: boolean;
  aim: number;
  pitch: number;
  hurt: number;
  hasGun: boolean;
  dead: number;
  recoil: number;
}

const damp = (cur: number, target: number, k: number): number => cur + (target - cur) * k;

export function posePlayer(r: Rig, s: PlayerPose, dt: number): void {
  const k = Math.min(1, dt * 14);
  const move = Math.min(1, s.speed / 1.6);
  const amp = (s.running ? 0.95 : 0.52) * move;
  const sn = Math.sin(s.gait);
  const a = s.aim;

  r.legL.rotation.x = damp(r.legL.rotation.x, sn * amp, k);
  r.legR.rotation.x = damp(r.legR.rotation.x, -sn * amp, k);
  r.shinL.rotation.x = damp(r.shinL.rotation.x, -Math.max(0, Math.sin(s.gait + 1.1)) * amp * 1.25, k);
  r.shinR.rotation.x = damp(r.shinR.rotation.x, -Math.max(0, Math.sin(s.gait + 1.1 + Math.PI)) * amp * 1.25, k);

  const swing = sn * amp * 0.75;
  const bend = s.running ? 1.1 : 0.18;
  const armRx = THREE.MathUtils.lerp(swing, Math.PI / 2 + s.pitch * 0.9 + s.recoil * 0.25, a);
  const armLx = THREE.MathUtils.lerp(-swing, Math.PI / 2 - 0.12 + s.pitch * 0.9, a);
  r.armR.rotation.x = damp(r.armR.rotation.x, armRx, k);
  r.armL.rotation.x = damp(r.armL.rotation.x, armLx, k);
  r.armR.rotation.y = damp(r.armR.rotation.y, 0.16 * a, k);
  r.armL.rotation.y = damp(r.armL.rotation.y, -0.62 * a, k);
  r.armR.rotation.z = damp(r.armR.rotation.z, 0.06 * (1 - a), k);
  r.armL.rotation.z = damp(r.armL.rotation.z, -0.06 * (1 - a), k);
  r.foreR.rotation.x = damp(r.foreR.rotation.x, bend * move * (1 - a) + 0.12 * (1 - a), k);
  r.foreL.rotation.x = damp(r.foreL.rotation.x, bend * move * (1 - a) + 0.12 * (1 - a) + 0.2 * a, k);

  const lean = (s.running ? -0.24 : -0.05) * move - s.hurt * 0.3;
  r.body.rotation.x = damp(r.body.rotation.x, lean, k);
  r.body.position.y = HIP_Y - Math.abs(Math.cos(s.gait)) * 0.035 * move - a * 0.03;
  r.torso.rotation.y = damp(r.torso.rotation.y, -sn * 0.12 * move * (1 - a) - 0.22 * a, k);
  r.head.rotation.x = damp(r.head.rotation.x, s.pitch * 0.5, k);
  r.head.rotation.y = damp(r.head.rotation.y, 0.22 * a, k);
  if (r.gun) r.gun.visible = s.hasGun;

  // collapse on death
  const d = Math.min(1, s.dead / 0.8);
  const e = d * d * (3 - 2 * d);
  r.root.rotation.x = -e * 1.45;
  r.root.position.y = e * 0.12;
}

// -------------------------------------------------------------------- the drowned

const LOOKS: Palette[] = [
  { skin: 0x6e807c, top: 0x2c3524, bottom: 0x191c1f, shoe: 0x0c0d0e, hair: 0x0b0c0d }, // oilskin jacket
  { skin: 0x6a7b79, top: 0x55595a, bottom: 0x20242b, shoe: 0x101010, hair: 0x120f0b }, // office shirt
  { skin: 0x6f7f79, top: 0x4a2a1c, bottom: 0x181c1f, shoe: 0x0c0c0d, hair: 0x09090a }, // faded raincoat
  { skin: 0x667876, top: 0x1c2b3c, bottom: 0x1f1f21, shoe: 0x0d0d0d, hair: 0x1a140e }, // work shirt
  { skin: 0x74847c, top: 0x3a363e, bottom: 0x26292c, shoe: 0x0a0a0b, hair: 0x0c0c0c }, // cardigan
  { skin: 0x6b7c78, top: 0x141618, bottom: 0x131517, shoe: 0x090909, hair: 0x100e0b }, // dark suit
];

export function buildEnemy(look: number): Rig {
  const pal = LOOKS[look % LOOKS.length] as Palette;
  const rig = buildRig(pal, 0.94 + (look % 3) * 0.06);
  for (const m of rig.mats) m.roughness = 0.66; // soaked through
  // weed and rope hanging off the shoulders
  const weed = new THREE.MeshStandardMaterial({ color: 0x131f15, roughness: 0.4 });
  const n = 4 + (look % 3);
  for (let i = 0; i < n; i++) {
    const len = 0.28 + ((look * 7 + i * 13) % 10) / 20;
    const s = new THREE.Mesh(new THREE.BoxGeometry(0.03, len, 0.014), weed);
    const side = i % 2 === 0 ? -1 : 1;
    s.position.set(side * (0.08 + ((i * 37) % 10) / 60), 0.52 - len / 2, i % 3 === 0 ? 0.135 : -0.125);
    s.rotation.z = side * 0.14;
    s.castShadow = true;
    rig.torso.add(s);
  }
  // wet hair plastered over the face
  const hair = rig.mats[4] as THREE.MeshStandardMaterial;
  const strands = 3 + (look % 2) * 2;
  for (let i = 0; i < strands; i++) {
    const len = 0.13 + ((look * 5 + i * 11) % 7) / 50;
    const s = new THREE.Mesh(new THREE.BoxGeometry(0.03, len, 0.012), hair);
    s.position.set(-0.06 + (i / (strands - 1)) * 0.12, 0.26 - len / 2, -0.125);
    s.rotation.x = 0.12;
    rig.head.add(s);
  }
  // sea sparkle: a faint cold glimmer that gives them away in the dark
  const count = 46;
  const pos = new Float32Array(count * 3);
  let seed = look * 97 + 13;
  const rnd = (): number => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 0; i < count; i++) {
    const a = rnd() * Math.PI * 2;
    const y = rnd();
    // shoulders, chest and back of the head carry most of it
    const r = y > 0.78 ? 0.12 : 0.2 - Math.abs(y - 0.45) * 0.12;
    pos[i * 3] = Math.sin(a) * r * 1.15;
    pos[i * 3 + 1] = 0.05 + y * 0.9;
    pos[i * 3 + 2] = Math.cos(a) * r * 0.8;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const glimMat = new THREE.PointsMaterial({
    color: 0x86f2df,
    size: 0.028,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.6,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    fog: false,
  });
  // points grow without bound as they near the lens: keep them specks
  glimMat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader.replace(
      "#include <logdepthbuf_vertex>",
      "gl_PointSize = clamp(gl_PointSize, 1.0, 4.0);\n#include <logdepthbuf_vertex>",
    );
  };
  const glim = new THREE.Points(geo, glimMat);
  rig.torso.add(glim);
  rig.glimmer = glim;
  rig.mats.push(weed);
  return rig;
}

export function poseEnemy(r: Rig, e: EnemyState, t: number, dt: number, seed: number): void {
  const k = Math.min(1, dt * 10);
  const sn = Math.sin(e.gait);
  const move = Math.min(1, e.speed / 0.6);
  const fast = e.speed > 1.6 ? 1 : 0;
  const sway = Math.sin(t * 0.9 + seed) * 0.03;
  const twitch = Math.sin(t * 7.3 + seed * 3.1) > 0.97 ? 0.25 : 0;

  let lean = -0.26;
  let roll = sn * 0.08 * move + 0.05 + sway;
  let armL = 0.08 + sn * 0.1 * move;
  let armR = 0.05 - sn * 0.12 * move;
  let fore = 0.15;
  let headX = -0.22;
  let headY = twitch;
  let stepR = sn * (0.42 + fast * 0.25) * move;
  let dragL = -0.16 + sn * (0.08 + fast * 0.22) * move;
  let fall = 0;

  switch (e.mode) {
    case "dormant":
      lean = -0.42;
      headX = -0.55;
      roll = 0.03 + sway;
      break;
    case "suspicious":
    case "search":
    case "investigate":
      headY = Math.sin(t * 1.5 + seed) * 0.55;
      headX = -0.05;
      lean = -0.18;
      break;
    case "chase":
      armL = 1.15 + Math.sin(t * 9 + seed) * 0.06;
      armR = 1.3 + Math.sin(t * 8.3 + seed) * 0.06;
      fore = 0.35;
      lean = -0.36;
      headX = 0.12;
      break;
    case "windup":
      armL = 2.35;
      armR = 2.55;
      fore = 0.5;
      lean = 0.12;
      headX = 0.2;
      break;
    case "recover":
      armL = 0.55;
      armR = 0.45;
      fore = 0.2;
      lean = -0.62;
      headX = -0.1;
      break;
    case "stagger":
      lean = 0.4;
      armL = -0.5;
      armR = -0.7;
      headX = 0.4;
      roll = 0.2;
      break;
    case "dead":
      fall = Math.min(1, e.modeT / 0.75);
      armL = -0.6;
      armR = -0.9;
      lean = 0.1;
      stepR = 0.15;
      dragL = -0.1;
      break;
    default:
      break;
  }

  r.legR.rotation.x = damp(r.legR.rotation.x, stepR, k);
  r.shinR.rotation.x = damp(r.shinR.rotation.x, -Math.max(0, Math.sin(e.gait + 1.1)) * 0.55 * move, k);
  r.legL.rotation.x = damp(r.legL.rotation.x, dragL, k);
  r.legL.rotation.z = -0.1;
  r.shinL.rotation.x = damp(r.shinL.rotation.x, -0.12, k);
  r.armL.rotation.x = damp(r.armL.rotation.x, armL, k);
  r.armR.rotation.x = damp(r.armR.rotation.x, armR, k);
  r.armL.rotation.z = -0.1;
  r.armR.rotation.z = 0.14;
  r.foreL.rotation.x = damp(r.foreL.rotation.x, fore, k);
  r.foreR.rotation.x = damp(r.foreR.rotation.x, fore * 1.3, k);
  r.body.rotation.x = damp(r.body.rotation.x, lean, k);
  r.body.rotation.z = damp(r.body.rotation.z, roll, k);
  r.body.position.y = HIP_Y - 0.03 - Math.abs(sn) * 0.03 * move;
  r.head.rotation.x = damp(r.head.rotation.x, headX, k);
  r.head.rotation.y = damp(r.head.rotation.y, headY, k * 0.6);
  r.head.rotation.z = 0.36;

  const f = fall * fall * (3 - 2 * fall);
  r.root.rotation.x = f * 1.5;
  r.root.position.y = f * 0.1;
  if (r.glimmer) {
    const alive = e.mode === "dead" ? Math.max(0, 1 - e.modeT / 4) : 1;
    const stir = e.mode === "chase" || e.mode === "windup" ? 1 : 0.62;
    (r.glimmer.material as THREE.PointsMaterial).opacity =
      alive * stir * (0.5 + 0.3 * Math.sin(t * 2.1 + seed) + 0.2 * Math.sin(t * 5.3 + seed * 2));
  }
}
