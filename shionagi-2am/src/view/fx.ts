// Weather and light effects: rain streaks, standing water, lamp glows, the
// smeared reflections lamps leave on a wet road, and the pooled point lights.

import * as THREE from "three";
import type { LightDef } from "../sim/types";
import type { FixtureHandle, TownHandles } from "./town";
import { glowTexture, rippleNormal, streakTexture } from "./textures";

// ------------------------------------------------------------------ rain

export class Rain {
  readonly mesh: THREE.LineSegments;
  private mat: THREE.ShaderMaterial;

  constructor(count = 3600) {
    const pos = new Float32Array(count * 2 * 3);
    const end = new Float32Array(count * 2);
    const speed = new Float32Array(count * 2);
    for (let i = 0; i < count; i++) {
      const x = Math.random();
      const y = Math.random();
      const z = Math.random();
      const sp = 0.85 + Math.random() * 0.4;
      for (let k = 0; k < 2; k++) {
        pos.set([x, y, z], (i * 2 + k) * 3);
        end[i * 2 + k] = k;
        speed[i * 2 + k] = sp;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aEnd", new THREE.BufferAttribute(end, 1));
    geo.setAttribute("aSpeed", new THREE.BufferAttribute(speed, 1));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e6);
    this.mat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uCam: { value: new THREE.Vector3() },
        uBox: { value: new THREE.Vector3(26, 16, 26) },
        uWind: { value: new THREE.Vector2(1.6, 0.7) },
        uOpacity: { value: 1 },
        uFlash: { value: 0 },
        uLightPos: { value: new THREE.Vector3() },
        uLightDir: { value: new THREE.Vector3(0, 0, -1) },
      },
      vertexShader: /* glsl */ `
        uniform float uTime;
        uniform vec3 uCam;
        uniform vec3 uBox;
        uniform vec2 uWind;
        uniform vec3 uLightPos;
        uniform vec3 uLightDir;
        attribute float aEnd;
        attribute float aSpeed;
        varying float vAlpha;
        varying float vLit;
        void main() {
          vec3 p = position * uBox;
          float fall = 15.0 * aSpeed;
          p.y -= uTime * fall;
          p.xz += uWind * uTime;
          vec3 rel = mod(p - uCam + uBox * 0.5, uBox) - uBox * 0.5;
          vec3 world = uCam + rel;
          float len = 0.55 * aSpeed;
          world.y += aEnd * len;
          world.xz -= aEnd * uWind * (len / fall);
          vec4 mv = viewMatrix * vec4(world, 1.0);
          gl_Position = projectionMatrix * mv;
          float d = length(rel.xz);
          vAlpha = (1.0 - smoothstep(uBox.x * 0.3, uBox.x * 0.5, d)) * mix(1.0, 0.25, aEnd);
          vec3 toP = world - uLightPos;
          float dl = length(toP);
          float c = dot(toP / max(dl, 0.001), uLightDir);
          vLit = smoothstep(0.86, 0.97, c) / (1.0 + dl * dl * 0.035);
        }
      `,
      fragmentShader: /* glsl */ `
        uniform float uOpacity;
        uniform float uFlash;
        varying float vAlpha;
        varying float vLit;
        void main() {
          vec3 col = vec3(0.5, 0.58, 0.68) * (0.12 + uFlash * 0.9) + vec3(1.0, 0.94, 0.82) * vLit * 1.5;
          gl_FragColor = vec4(col, vAlpha * uOpacity);
        }
      `,
    });
    this.mesh = new THREE.LineSegments(geo, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 5;
  }

  update(time: number, cam: THREE.Vector3, opacity: number, flash: number, lightPos: THREE.Vector3, lightDir: THREE.Vector3): void {
    const u = this.mat.uniforms;
    (u["uTime"] as THREE.IUniform<number>).value = time;
    (u["uCam"] as THREE.IUniform<THREE.Vector3>).value.copy(cam);
    (u["uOpacity"] as THREE.IUniform<number>).value = opacity;
    (u["uFlash"] as THREE.IUniform<number>).value = flash;
    (u["uLightPos"] as THREE.IUniform<THREE.Vector3>).value.copy(lightPos);
    (u["uLightDir"] as THREE.IUniform<THREE.Vector3>).value.copy(lightDir);
  }
}

// ------------------------------------------------------------------ water

export class Waters {
  readonly group = new THREE.Group();
  private normal: THREE.Texture;
  private normal2: THREE.Texture;

  constructor(defs: TownHandles["waters"]) {
    this.normal = rippleNormal();
    this.normal2 = this.normal.clone();
    this.normal2.needsUpdate = true;
    const flood = new THREE.MeshStandardMaterial({
      color: 0x0b1318,
      roughness: 0.06,
      metalness: 0.25,
      transparent: true,
      opacity: 0.88,
      normalMap: this.normal,
      normalScale: new THREE.Vector2(0.55, 0.55),
    });
    const deep = new THREE.MeshStandardMaterial({
      color: 0x060b0f,
      roughness: 0.12,
      metalness: 0.3,
      normalMap: this.normal2,
      normalScale: new THREE.Vector2(1.4, 1.4),
    });
    for (const d of defs) {
      const w = d.x1 - d.x0;
      const h = d.z1 - d.z0;
      const geo = new THREE.PlaneGeometry(w, h);
      const uv = geo.getAttribute("uv");
      const s = d.kind === "flood" ? 0.22 : 0.08;
      for (let i = 0; i < uv.count; i++) uv.setXY(i, (d.x0 + uv.getX(i) * w) * s, (d.z0 + uv.getY(i) * h) * s);
      const mesh = new THREE.Mesh(geo, d.kind === "flood" ? flood : deep);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set((d.x0 + d.x1) / 2, d.y, (d.z0 + d.z1) / 2);
      mesh.receiveShadow = true;
      mesh.renderOrder = 1;
      this.group.add(mesh);
    }
  }

  update(time: number): void {
    this.normal.offset.set(time * 0.035, time * 0.05);
    this.normal2.offset.set(-time * 0.02, time * 0.03);
  }
}

// ------------------------------------------------------------------ lamps

function hash(n: number): number {
  const s = Math.sin(n * 127.1) * 43758.5453;
  return s - Math.floor(s);
}

/** Brightness of a lamp at time t (0..~1.2). */
export function lampLevel(def: LightDef, t: number): number {
  const s = def.seed;
  switch (def.mode) {
    case "steady":
      return 1;
    case "flicker": {
      const slot = Math.floor(t * 11 + s);
      let v = 0.82 + 0.18 * Math.sin(t * 17 + s);
      if (hash(slot) > 0.83) v *= 0.12;
      if (hash(Math.floor(t * 0.45 + s) * 3.7) > 0.8) v *= 0.3 + 0.7 * hash(slot * 1.7);
      return v;
    }
    case "buzz": {
      let v = 0.86 + 0.14 * Math.sin(t * 61 + s);
      if (hash(Math.floor(t * 6 + s) + 0.5) > 0.93) v *= 0.35;
      return v;
    }
    case "pulse":
      return 0.5 + 0.5 * Math.sin(t * 1.7 + s);
    case "blink":
      return (t + s * 0.01) % 1.0 < 0.22 ? 1.2 : 0.02;
    case "blinkAlt":
      return (t + 0.5 + s * 0.01) % 1.0 < 0.22 ? 1.2 : 0.02;
    case "beacon": {
      const c = Math.max(0, Math.sin(t * 8.2 + s));
      return 0.12 + 1.1 * c * c * c;
    }
  }
}

interface Slot {
  light: THREE.PointLight;
  idx: number;
  fade: number;
}

export class Lamps {
  readonly group = new THREE.Group();
  private sprites: THREE.Sprite[] = [];
  private streaks: (THREE.Mesh | null)[] = [];
  private slots: Slot[] = [];
  private levels: number[];
  private readonly lensByLight = new Map<number, THREE.Mesh>();
  /** candela per unit of `power` */
  gain = 15;

  constructor(
    private defs: LightDef[],
    fixtures: FixtureHandle[],
    poolSize: number,
  ) {
    this.levels = defs.map(() => 1);
    const glow = glowTexture();
    const streak = streakTexture();
    const streakGeo = new THREE.BufferGeometry();
    streakGeo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute([-0.5, 0, 0, 0.5, 0, 0, 0.5, 0, 1, -0.5, 0, 1], 3),
    );
    streakGeo.setAttribute("uv", new THREE.Float32BufferAttribute([0, 1, 1, 1, 1, 0, 0, 0], 2));
    streakGeo.setIndex([0, 2, 1, 0, 3, 2]);
    for (const d of defs) {
      const sm = new THREE.SpriteMaterial({
        map: glow,
        color: d.color,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        transparent: true,
        fog: false,
      });
      const sp = new THREE.Sprite(sm);
      sp.position.set(d.x, d.y, d.z);
      sp.scale.setScalar(d.glow > 0 ? d.glow : 0.001);
      sp.visible = d.glow > 0;
      sp.renderOrder = 6;
      this.group.add(sp);
      this.sprites.push(sp);
      if (d.streak && d.y > 0.3) {
        const mm = new THREE.MeshBasicMaterial({
          map: streak,
          color: d.color,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          transparent: true,
          fog: false,
          polygonOffset: true,
          polygonOffsetFactor: -4,
        });
        const mesh = new THREE.Mesh(streakGeo, mm);
        mesh.renderOrder = 3;
        mesh.frustumCulled = false;
        this.group.add(mesh);
        this.streaks.push(mesh);
      } else {
        this.streaks.push(null);
      }
    }
    for (const f of fixtures) if (f.lens) this.lensByLight.set(f.light, f.lens);
    for (let i = 0; i < poolSize; i++) {
      const light = new THREE.PointLight(0xffffff, 0, 10, 2);
      this.group.add(light);
      this.slots.push({ light, idx: -1, fade: 0 });
    }
  }

  /**
   * `groupOn` says whether a switched group is lit; `floodY` lifts streaks onto
   * the flood water where there is some.
   */
  update(
    t: number,
    dt: number,
    cam: THREE.Vector3,
    groupOn: (g: NonNullable<LightDef["group"]>) => boolean,
    groundY: (x: number, z: number) => number,
    streakGain: number,
  ): void {
    const defs = this.defs;
    const scored: { i: number; score: number }[] = [];
    for (let i = 0; i < defs.length; i++) {
      const d = defs[i] as LightDef;
      let lv = lampLevel(d, t);
      if (d.group && !groupOn(d.group)) lv = 0;
      this.levels[i] = lv;
      const dx = d.x - cam.x;
      const dy = d.y - cam.y;
      const dz = d.z - cam.z;
      const dist = Math.hypot(dx, dy, dz);
      const sp = this.sprites[i] as THREE.Sprite;
      if (sp.visible || d.glow > 0) {
        sp.visible = d.glow > 0 && lv > 0.01;
        // glows stay faintly visible through the rain far beyond the fog, and
        // shrink out of the way when the camera is right on top of them
        const far = Math.exp(-dist / 70);
        const nearFade = Math.min(1, Math.max(0.1, (dist - 0.5) / 5.5));
        (sp.material as THREE.SpriteMaterial).opacity = Math.min(1, lv) * (0.2 + 0.6 * far) * nearFade;
        sp.scale.setScalar(d.glow * 0.72 * (0.9 + 0.1 * lv) * (1 + Math.min(1.3, dist / 45)));
      }
      const lens = this.lensByLight.get(i);
      if (lens) (lens.material as THREE.MeshBasicMaterial).color.set(d.color).multiplyScalar(0.15 + 1.6 * Math.min(1.2, lv));
      const st = this.streaks[i];
      if (st) {
        const gx = dx;
        const gz = dz;
        const gd = Math.hypot(gx, gz);
        const op = lv * streakGain * Math.exp(-gd / 45) * Math.min(1, gd / 2.5);
        st.visible = op > 0.01;
        if (st.visible) {
          const len = Math.min(10, 1.2 + d.y * 1.7) * (0.6 + Math.min(1, gd / 12) * 0.6);
          st.position.set(d.x, groundY(d.x, d.z) + 0.012, d.z);
          st.rotation.y = Math.atan2(-gx, -gz);
          st.scale.set(0.35 + d.glow * 0.38, 1, len);
          (st.material as THREE.MeshBasicMaterial).opacity = Math.min(0.85, op * 0.55);
        }
      }
      if (d.range > 0 && lv > 0.001 && dist < d.range * 2.6) {
        scored.push({ i, score: (d.power * (0.4 + 0.6 * Math.min(1, lv + 0.5))) / (1 + (dist * dist) / (d.range * d.range)) });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    const wanted = scored.slice(0, this.slots.length).map((s) => s.i);
    const k = Math.min(1, dt * 6);
    for (const s of this.slots) {
      if (s.idx >= 0 && !wanted.includes(s.idx)) {
        s.fade -= k;
        if (s.fade <= 0) {
          s.fade = 0;
          s.idx = -1;
        }
      }
    }
    for (const w of wanted) {
      if (this.slots.some((s) => s.idx === w)) continue;
      const free = this.slots.find((s) => s.idx < 0);
      if (!free) break;
      free.idx = w;
      free.fade = 0;
    }
    for (const s of this.slots) {
      if (s.idx < 0) {
        s.light.intensity = 0;
        continue;
      }
      const d = defs[s.idx] as LightDef;
      if (wanted.includes(s.idx)) s.fade = Math.min(1, s.fade + k);
      s.light.position.set(d.x, d.y - 0.3, d.z);
      s.light.color.set(d.color);
      s.light.distance = d.range;
      s.light.intensity = d.power * this.gain * (this.levels[s.idx] as number) * s.fade;
    }
  }
}
