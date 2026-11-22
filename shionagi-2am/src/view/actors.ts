// The two kinds of people in Shionagi: the ferry terminal's night-shift
// maintenance worker, and the drowned who came back up with the tide. Both are
// use a shared articulated rig with their own clothing, equipment and poses.

import * as THREE from "three";
import { dressDrowned } from "./drowned";
import { makeRevolver } from "./town";
import { dressWorker } from "./worker-gear";

export { poseDrowned as poseEnemy } from "./drowned";

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
  dressWorker(rig);
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
  dressDrowned(rig, look);
  return rig;
}
