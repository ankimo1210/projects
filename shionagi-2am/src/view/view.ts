// Renders the simulation: owns the three.js scene, the camera, the lights and
// the post-processing chain. It only ever reads `sim`.

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { CAM, camDir, updateCamera } from "../sim/camera";
import { fwdX, fwdZ, inRect, lerp, rayBox, wrapAngle } from "../sim/geom";
import { FLOOD_Y } from "../sim/level";
import { viewPitch } from "../sim/sim";
import type { Sim } from "../sim/sim";
import type { CamState, EnemyState, LightDef, SimEvent } from "../sim/types";
import { buildEnemy, buildPlayer, poseEnemy, posePlayer } from "./actors";
import type { Rig } from "./actors";
import { lampLevel, Lamps, Rain, Waters } from "./fx";
import { makeMaterials } from "./materials";
import { glowTexture } from "./textures";
import { buildTown } from "./town";
import type { TownHandles } from "./town";

const FOG = 0x0a111a;
const HEMI = 5.5;
const TORCH = 72;

const GradeShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uTime: { value: 0 },
    uVignette: { value: 0.9 },
    uGrain: { value: 0.5 },
    uHurt: { value: 0 },
    uFade: { value: 1 },
    uSat: { value: 0.86 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uVignette;
    uniform float uGrain;
    uniform float uHurt;
    uniform float uFade;
    uniform float uSat;
    uniform vec3 uTint;
    varying vec2 vUv;
    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
    }
    void main() {
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 q = (vUv - 0.5) * vec2(1.0, 0.92);
      float edge = smoothstep(0.28, 0.82, length(q));
      float l = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
      c.rgb = mix(vec3(l), c.rgb, uSat) * uTint;
      c.rgb *= 1.0 - edge * uVignette;
      c.rgb = mix(c.rgb, vec3(0.55, 0.015, 0.01) * (0.25 + l * 2.5), clamp(uHurt * (0.25 + edge * 1.6), 0.0, 0.9));
      float n = hash(vUv * vec2(1733.0, 977.0) + fract(uTime * 7.31) * 113.0) - 0.5;
      c.rgb += n * uGrain * (0.012 + l * 0.16);
      gl_FragColor = vec4(max(c.rgb, 0.0) * uFade, 1.0);
    }
  `,
};

export interface ViewHooks {
  thunder?: (delay: number, near: boolean) => void;
  rattle?: (x: number, y: number, z: number) => void;
}

export class View {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera: THREE.PerspectiveCamera;
  hooks: ViewHooks = {};
  /** free camera for screenshots: position + look-at target */
  debugCam: { pos: THREE.Vector3; target: THREE.Vector3 } | null = null;
  readonly lamps: Lamps;

  private composer: EffectComposer;
  private bloom: UnrealBloomPass;
  private grade: ShaderPass;
  private town: TownHandles;
  private frost!: THREE.MeshStandardMaterial;
  private shades: THREE.Mesh[] = [];
  private glassZ = -14.15;
  private glassX0 = -12.5;
  private glassX1 = 4.5;
  private plazaLamp: LightDef | null = null;
  private rain: Rain;
  private waters: Waters;
  private player: Rig;
  private playerMats: THREE.Material[] = [];
  private enemies: Rig[] = [];
  private flashlight: THREE.SpotLight;
  private fill: THREE.PointLight;
  private spill: THREE.PointLight;
  private hemi: THREE.HemisphereLight;
  private bolt: THREE.DirectionalLight;
  private muzzle: THREE.PointLight;
  private muzzleSprite: THREE.Sprite;
  private tipSprite: THREE.Sprite;
  private glints: { sprite: THREE.Sprite; id: string }[] = [];
  private puffs: { sprite: THREE.Sprite; life: number }[] = [];
  private cam: CamState = { x: 0, y: 2, z: 0, dist: CAM.distance, side: CAM.side };
  private snap = true;
  private time = 0;
  private shake = 0;
  private kick = 0;
  private indoor = 1;

  /** 0 in the open .. 1 under a roof (smoothed), for the audio mix */
  get indoorAmount(): number {
    return this.indoor;
  }
  private flash = 0;
  private boltT = 0;
  private boltPlan: { at: number; level: number }[] = [];
  private nextBolt = 7;
  private fade = 1;
  private iris = 1;
  private rattleT: number[];
  private rattleOn: number[];
  private pixelRatio: number;
  private frameAvg = 16;
  private stats = { calls: 0, triangles: 0 };
  private readonly lightPos = new THREE.Vector3();
  private readonly lightDir = new THREE.Vector3();
  private readonly tmp = new THREE.Vector3();

  constructor(
    canvas: HTMLCanvasElement,
    private sim: Sim,
  ) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance" });
    this.pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
    this.renderer.setPixelRatio(this.pixelRatio);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.info.autoReset = false;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.35;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene.background = new THREE.Color(FOG);
    this.scene.fog = new THREE.FogExp2(FOG, 0.024);
    this.camera = new THREE.PerspectiveCamera(CAM.fov, 16 / 9, 0.07, 260);
    this.camera.rotation.order = "YXZ";

    const mats = makeMaterials();
    // Fogged glass: nothing behind it is drawn through it. It glows faintly with
    // the plaza lamp, and whoever walks close outside throws a shadow on it.
    this.frost = new THREE.MeshStandardMaterial({
      color: 0x8fa0a8,
      roughness: 0.42,
      metalness: 0,
      map: frostTexture(),
      emissive: 0x9db4cc,
      emissiveMap: frostTexture(),
      emissiveIntensity: 0.1,
      side: THREE.DoubleSide,
    });
    mats["frost"] = this.frost;
    mats["chain"] = new THREE.MeshStandardMaterial({
      color: 0x8a9096,
      roughness: 0.5,
      metalness: 0.6,
      alphaMap: chainAlpha(),
      alphaTest: 0.5,
      side: THREE.DoubleSide,
    });
    this.town = buildTown(sim.level, mats);
    this.scene.add(this.town.group);

    // shadows of the figures outside, on the inner face of the glass
    const shade = shadeTexture();
    const glassDef = sim.level.props.find((q) => q.k === "glassWall");
    this.glassZ = glassDef && glassDef.k === "glassWall" ? glassDef.z : -14.15;
    this.glassX0 = glassDef && glassDef.k === "glassWall" ? glassDef.x0 : -12.5;
    this.glassX1 = glassDef && glassDef.k === "glassWall" ? glassDef.x1 : 4.5;
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(
        new THREE.PlaneGeometry(1.5, 2.3),
        new THREE.MeshBasicMaterial({ map: shade, color: 0x020304, transparent: true, opacity: 0, depthWrite: false, fog: false }),
      );
      m.visible = false;
      m.renderOrder = 3;
      this.scene.add(m);
      this.shades.push(m);
    }
    this.plazaLamp = sim.level.lights.find((l) => l.y > 5 && l.z > -18 && l.z < -17) ?? null;

    this.waters = new Waters(this.town.waters);
    this.scene.add(this.waters.group);
    this.rain = new Rain();
    this.scene.add(this.rain.mesh);
    this.lamps = new Lamps(sim.level.lights, this.town.fixtures, 6);
    this.scene.add(this.lamps.group);

    this.hemi = new THREE.HemisphereLight(0x35455f, 0x10141a, HEMI);
    this.scene.add(this.hemi);
    this.bolt = new THREE.DirectionalLight(0xc4d4ff, 0);
    this.scene.add(this.bolt);
    this.scene.add(this.bolt.target);

    this.flashlight = new THREE.SpotLight(0xfff0d8, TORCH, 36, 0.52, 0.7, 1.35);
    this.flashlight.castShadow = true;
    this.flashlight.shadow.mapSize.set(1024, 1024);
    this.flashlight.shadow.bias = -0.0007;
    this.flashlight.shadow.normalBias = 0.03;
    this.flashlight.shadow.camera.near = 0.25;
    this.flashlight.shadow.camera.far = 36;
    this.scene.add(this.flashlight);
    this.scene.add(this.flashlight.target);

    this.fill = new THREE.PointLight(0x93a6c4, 1.1, 5.5, 2);
    this.scene.add(this.fill);
    // the lamp's spill: a soft pool of light on the ground around the wearer
    this.spill = new THREE.PointLight(0xffe9c8, 5, 9, 1.5);
    this.scene.add(this.spill);
    this.muzzle = new THREE.PointLight(0xffc27a, 0, 14, 2);
    this.scene.add(this.muzzle);

    const glow = glowTexture();
    const sprite = (color: number, size: number): THREE.Sprite => {
      const s = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: glow,
          color,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          transparent: true,
          fog: false,
        }),
      );
      s.scale.setScalar(size);
      s.renderOrder = 6;
      this.scene.add(s);
      return s;
    };
    this.muzzleSprite = sprite(0xffd9a0, 0.9);
    this.muzzleSprite.visible = false;
    this.tipSprite = sprite(0xff2a18, 1.4);
    for (const id of Object.keys(this.town.items)) {
      const obj = this.town.items[id] as THREE.Object3D;
      const g = sprite(0xdfe8ff, 0.42);
      g.position.copy(obj.position);
      g.position.y += 0.1;
      this.glints.push({ sprite: g, id });
    }

    this.player = buildPlayer();
    this.player.root.rotation.order = "YXZ";
    this.player.root.traverse((o) => {
      // the lamp sits on the chest: the wearer must not shadow his own beam
      o.castShadow = false;
      const m = (o as THREE.Mesh).material as THREE.Material | undefined;
      if (m && !this.playerMats.includes(m)) this.playerMats.push(m);
    });
    this.scene.add(this.player.root);
    for (const def of sim.level.enemies) {
      const rig = buildEnemy(def.look);
      rig.root.rotation.order = "YXZ";
      this.enemies.push(rig);
      this.scene.add(rig.root);
    }

    this.rattleT = sim.level.rattles.map((_, i) => 3 + i * 2.3);
    this.rattleOn = sim.level.rattles.map(() => 0);

    const rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(this.renderer, rt);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.34, 0.5, 0.95);
    this.composer.addPass(this.bloom);
    this.grade = new ShaderPass(GradeShader);
    this.composer.addPass(this.grade);
    this.composer.addPass(new OutputPass());
    this.resize();
  }

  resize(): void {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.renderer.setPixelRatio(this.pixelRatio);
    this.renderer.setSize(w, h, false);
    this.composer.setPixelRatio(this.pixelRatio);
    this.composer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  /** Call after a retry so nothing eases across the map. */
  reset(): void {
    this.snap = true;
    this.shake = 0;
    this.fade = 0;
    for (const id of Object.keys(this.town.doors)) {
      const d = this.town.doors[id];
      if (d) d.open = this.sim.s.doors[id] ? 1 : 0;
    }
  }

  onEvent(ev: SimEvent): void {
    switch (ev.t) {
      case "shot": {
        this.muzzle.position.set(ev.x, ev.y, ev.z);
        this.muzzle.intensity = 420;
        this.muzzleSprite.position.set(ev.x, ev.y, ev.z);
        this.muzzleSprite.visible = true;
        (this.muzzleSprite.material as THREE.SpriteMaterial).opacity = 1;
        this.kick = 1;
        this.shake = Math.max(this.shake, 0.25);
        if (ev.hit !== "none") this.puff(ev.hx, ev.hy, ev.hz, ev.hit === "world" ? 0xb8b0a0 : 0x6a1a14);
        break;
      }
      case "hurt":
        this.shake = 1;
        break;
      case "thunder":
        this.strike(true);
        break;
      case "cue":
        // The figure outside is heard first; its shadow reaches the panes about 2.7 s
        // later. Sheet lightning once it is a couple of metres along lights the whole
        // glass front behind it.
        if (ev.id === "glass") this.nextBolt = 5.4;
        break;
      case "bridge":
        if (ev.phase === "down") this.shake = Math.max(this.shake, 0.5);
        break;
      case "clear":
        this.fade = 0;
        break;
      case "retry":
        this.reset();
        break;
      default:
        break;
    }
  }

  private puff(x: number, y: number, z: number, color: number): void {
    const s = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: (this.muzzleSprite.material as THREE.SpriteMaterial).map,
        color,
        transparent: true,
        depthWrite: false,
        opacity: 0.8,
      }),
    );
    s.position.set(x, y, z);
    s.scale.setScalar(0.25);
    this.scene.add(s);
    this.puffs.push({ sprite: s, life: 0.45 });
  }

  /** Start a lightning strike: a few stuttering pulses. */
  private strike(near: boolean): void {
    this.boltT = 0;
    this.boltPlan = near
      ? [
          { at: 0, level: 1 },
          { at: 0.09, level: 0.2 },
          { at: 0.16, level: 0.9 },
          { at: 0.34, level: 0.35 },
          { at: 0.5, level: 0.7 },
        ]
      : [
          { at: 0, level: 0.5 + Math.random() * 0.3 },
          { at: 0.1, level: 0.15 },
          { at: 0.2, level: 0.35 + Math.random() * 0.3 },
        ];
    this.hooks.thunder?.(near ? 0.25 : 0.6 + Math.random() * 2.2, near);
  }

  frame(alpha: number, dt: number): void {
    const t0 = performance.now();
    const sim = this.sim;
    const s = sim.s;
    const p = s.player;
    this.time += dt;
    const time = this.time;
    const px = lerp(p.px, p.x, alpha);
    const pz = lerp(p.pz, p.z, alpha);
    const pitch = viewPitch(p.pitch, p.recoil);

    // ------------------------------------------------ camera
    updateCamera(this.cam, px, pz, p.yaw, pitch, p.aim, sim.level.boxes, dt, this.snap);
    this.snap = false;
    this.shake = Math.max(0, this.shake - dt * 2.6);
    this.kick = Math.max(0, this.kick - dt * 9);
    const sh = this.shake * this.shake;
    const cam = this.camera;
    if (this.debugCam) {
      cam.position.copy(this.debugCam.pos);
      cam.lookAt(this.debugCam.target);
    } else {
      cam.position.set(
        this.cam.x + Math.sin(time * 61) * 0.035 * sh,
        this.cam.y + Math.sin(time * 47 + 1.3) * 0.03 * sh,
        this.cam.z + Math.sin(time * 53 + 2.1) * 0.035 * sh,
      );
      cam.rotation.set(pitch + this.kick * 0.012, p.yaw, Math.sin(time * 39) * 0.012 * sh);
    }
    const fov = lerp(CAM.fov, CAM.aimFov, p.aim) + (p.running ? 2.5 : 0);
    if (Math.abs(cam.fov - fov) > 0.01) {
      cam.fov += (fov - cam.fov) * Math.min(1, dt * 8);
      cam.updateProjectionMatrix();
    }
    const camZone = sim.level.zones.find((z) => inRect(z, cam.position.x, cam.position.z));
    const inside = camZone?.indoor && cam.position.y < 4.6 ? 1 : 0;
    this.indoor += (inside - this.indoor) * Math.min(1, dt * 3);

    // ------------------------------------------------ actors
    const pr = this.player;
    pr.root.position.x = px;
    pr.root.position.z = pz;
    pr.root.rotation.y = p.bodyYaw;
    posePlayer(
      pr,
      {
        gait: p.gait,
        speed: p.speed,
        running: p.running,
        aim: p.aim,
        pitch,
        hurt: p.hurtT / 0.8,
        hasGun: p.hasGun,
        dead: s.phase === "dead" ? s.phaseT : 0,
        recoil: p.recoil,
      },
      dt,
    );
    // the player thins out when the lens is nearly on top of him, and while
    // aiming with no room over either shoulder (the head would hide the sights)
    const closeUp = THREE.MathUtils.smoothstep(this.cam.dist, 0.3, 0.95);
    const shoulder = lerp(1, THREE.MathUtils.smoothstep(Math.abs(this.cam.side), 0.1, 0.3), p.aim);
    const near = this.debugCam ? 1 : Math.min(closeUp, shoulder);
    for (const m of this.playerMats) {
      m.transparent = near < 0.98;
      m.opacity = 0.12 + 0.88 * near;
    }
    for (let i = 0; i < this.enemies.length; i++) {
      const e = s.enemies[i] as EnemyState;
      const rig = this.enemies[i] as Rig;
      rig.root.position.x = lerp(e.px, e.x, alpha);
      rig.root.position.z = lerp(e.pz, e.z, alpha);
      rig.root.rotation.y += wrapAngle(e.yaw - rig.root.rotation.y) * Math.min(1, dt * 14);
      poseEnemy(rig, e, time, dt, i * 2.7);
    }

    // ------------------------------------------------ lights on the player
    const [fx, fy, fz] = camDir(p.yaw, pitch - 0.06);
    this.lightPos.set(px + fwdX(p.bodyYaw) * 0.22, 1.36, pz + fwdZ(p.bodyYaw) * 0.22);
    this.lightDir.set(fx, fy, fz);
    this.flashlight.position.copy(this.lightPos);
    this.flashlight.target.position.set(px + fx * 8, 1.36 + fy * 8, pz + fz * 8);
    // crude iris: ease the lamp down when it is shining on something close
    // (the middle of the beam, its two edges, and anybody standing in it)
    let reach = 9;
    const edge = 0.38;
    const ex1 = fx * Math.cos(edge) - fz * Math.sin(edge);
    const ez1 = fx * Math.sin(edge) + fz * Math.cos(edge);
    const ex2 = fx * Math.cos(edge) + fz * Math.sin(edge);
    const ez2 = -fx * Math.sin(edge) + fz * Math.cos(edge);
    for (const b of sim.level.boxes) {
      if (!b.on || b.thin || !(b.solid || b.ceil)) continue;
      const lx = this.lightPos.x;
      const ly = this.lightPos.y;
      const lz = this.lightPos.z;
      const t = Math.min(
        rayBox(lx, ly, lz, fx, fy, fz, b, 0),
        rayBox(lx, ly, lz, ex1, fy, ez1, b, 0) * 1.7,
        rayBox(lx, ly, lz, ex2, fy, ez2, b, 0) * 1.7,
      );
      if (t < reach) reach = t;
    }
    for (const e of s.enemies) {
      const dx = e.x - px;
      const dz = e.z - pz;
      const d = Math.hypot(dx, dz);
      if (d < reach * 0.8 && d > 0.3 && (dx * fx + dz * fz) / d > 0.86) reach = d / 0.8;
    }
    const iris = Math.min(1, Math.max(0.05, Math.pow(reach / 6.5, 1.35)));
    this.iris += (iris - this.iris) * Math.min(1, dt * 6);
    const dying = s.phase === "dead" ? Math.max(0, 1 - s.phaseT * 0.7) : 1;
    this.flashlight.intensity = TORCH * this.iris * dying;
    this.fill.position.copy(cam.position);
    this.spill.position.set(px + fx * 1.3, 1.5, pz + fz * 1.3);
    this.spill.intensity = 5 * dying * (0.4 + 0.6 * this.iris);
    this.muzzle.intensity *= Math.max(0, 1 - dt * 28);
    if (this.muzzleSprite.visible) {
      const m = this.muzzleSprite.material as THREE.SpriteMaterial;
      m.opacity -= dt * 16;
      if (m.opacity <= 0) this.muzzleSprite.visible = false;
    }
    for (let i = this.puffs.length - 1; i >= 0; i--) {
      const pf = this.puffs[i] as { sprite: THREE.Sprite; life: number };
      pf.life -= dt;
      pf.sprite.scale.multiplyScalar(1 + dt * 3.5);
      (pf.sprite.material as THREE.SpriteMaterial).opacity = Math.max(0, pf.life * 1.6);
      if (pf.life <= 0) {
        this.scene.remove(pf.sprite);
        pf.sprite.material.dispose();
        this.puffs.splice(i, 1);
      }
    }

    // ------------------------------------------------ world state
    for (const id of Object.keys(this.town.doors)) {
      const d = this.town.doors[id];
      if (!d) continue;
      const target = s.doors[id] ? 1 : 0;
      d.open += (target - d.open) * Math.min(1, dt * 4.5);
      d.group.rotation.y = d.base + d.swing * d.open * 1.75;
    }
    for (const g of this.glints) {
      const obj = this.town.items[g.id];
      const there = !s.used[g.id];
      if (obj) obj.visible = there;
      g.sprite.visible = there;
      (g.sprite.material as THREE.SpriteMaterial).opacity = 0.2 + 0.16 * Math.sin(time * 2.4 + g.sprite.position.x);
    }
    const br = this.town.bridge;
    if (br) {
      const raise = sim.bridgeRaise();
      const eased = raise * raise * (3 - 2 * raise);
      const judder = s.bridge.state === "lowering" ? Math.sin(time * 37) * 0.004 : 0;
      br.pivot.rotation.x = eased * 1.32 + judder;
      br.pivot.updateMatrixWorld();
      this.tmp.copy(br.tip).applyMatrix4(br.pivot.matrixWorld);
      this.tipSprite.position.copy(this.tmp);
      const blink = s.bridge.state === "lowering" ? (time * 2.4) % 1 < 0.5 : (time * 0.8) % 1 < 0.5;
      (this.tipSprite.material as THREE.SpriteMaterial).opacity = blink ? 0.9 : 0.12;
    }
    if (this.town.lever) {
      const target = s.used["panel"] ? 0.75 : -0.75;
      this.town.lever.rotation.x += (target - this.town.lever.rotation.x) * Math.min(1, dt * 7);
    }
    this.updateRattles(dt, px, pz);

    // ------------------------------------------------ weather
    this.updateLightning(dt, px, pz);
    const flash = this.flash;
    this.hemi.intensity = HEMI * (1 - this.indoor * 0.45) + flash * 14 * (1 - this.indoor * 0.6);
    this.bolt.intensity = flash * 3.2 * (1 - this.indoor * 0.75);
    const fog = this.scene.fog as THREE.FogExp2;
    fog.density = lerp(0.024, 0.01, this.indoor);
    fog.color.setHex(FOG).lerp(this.tmpColor.setHex(0x30405c), flash * 0.5);
    (this.scene.background as THREE.Color).copy(fog.color);

    // the glass front: lit from outside by the plaza lamp (and the sky, when it flashes)
    const lampNow = this.plazaLamp ? lampLevel(this.plazaLamp, time) : 1;
    this.frost.emissiveIntensity = 0.09 + 0.2 * lampNow + flash * 1.3;
    let used = 0;
    for (let i = 0; i < s.enemies.length && used < this.shades.length; i++) {
      const e = s.enemies[i] as EnemyState;
      if (e.mode === "dead") continue;
      const gap = this.glassZ - lerp(e.pz, e.z, alpha); // metres outside the glass
      const ex = lerp(e.px, e.x, alpha);
      if (gap < 0.2 || gap > 3.4 || ex < this.glassX0 - 0.4 || ex > this.glassX1 + 0.4) continue;
      const m = this.shades[used++] as THREE.Mesh;
      // further from the glass the shadow is larger, softer and fainter
      const grow = 1 + Math.max(0, gap - 0.6) * 0.3;
      m.visible = true;
      m.position.set(ex, 1.15 * grow - 0.02, this.glassZ + 0.16);
      m.scale.set(grow, grow, 1);
      m.rotation.z = Math.sin(e.gait) * 0.05;
      (m.material as THREE.MeshBasicMaterial).opacity = Math.min(0.92, Math.max(0, 1.25 - gap / 2.7)) * (0.55 + 0.45 * lampNow);
    }
    for (; used < this.shades.length; used++) (this.shades[used] as THREE.Mesh).visible = false;

    const groundY = (x: number, z: number): number => (sim.surfaceAt(x, z) === "water" ? FLOOD_Y : 0);
    this.lamps.update(
      time,
      dt,
      cam.position,
      (g) => (g === "bridgeWarn" ? s.bridge.state === "lowering" : true),
      groundY,
      1,
    );
    this.rain.update(time, cam.position, 1 - this.indoor, flash, this.lightPos, this.lightDir);
    this.waters.update(time);

    // ------------------------------------------------ grade
    const u = this.grade.uniforms;
    const lowHp = p.hp <= 25 && s.phase === "play" ? 0.16 + 0.1 * Math.sin(time * 5) : 0;
    const dead = s.phase === "dead" ? Math.min(1, s.phaseT / 1.6) : 0;
    (u["uHurt"] as THREE.IUniform<number>).value = Math.max(p.hurtT / 0.8, lowHp, dead * 0.9);
    (u["uTime"] as THREE.IUniform<number>).value = time;
    const targetFade = s.phase === "clear" ? 0 : s.phase === "dead" ? 1 - dead * 0.85 : 1;
    if (s.phase === "clear") this.fade = 0;
    else this.fade += (targetFade - this.fade) * Math.min(1, dt * 2.2);
    (u["uFade"] as THREE.IUniform<number>).value = this.fade;

    this.renderer.info.reset();
    this.composer.render(dt);
    this.stats.calls = this.renderer.info.render.calls;
    this.stats.triangles = this.renderer.info.render.triangles;

    // crude dynamic resolution: back off when frames get slow
    this.frameAvg += (performance.now() - t0 - this.frameAvg) * 0.05;
  }

  private readonly tmpColor = new THREE.Color();

  private updateRattles(dt: number, px: number, pz: number): void {
    const list = this.sim.level.rattles;
    for (let i = 0; i < list.length; i++) {
      const r = list[i];
      if (!r) continue;
      const d = Math.hypot(r.x - px, r.z - pz);
      if (d < 11) this.rattleT[i] = (this.rattleT[i] as number) - dt;
      if ((this.rattleT[i] as number) <= 0) {
        this.rattleT[i] = 6 + Math.random() * 9;
        this.rattleOn[i] = 0.7 + Math.random() * 0.5;
        this.hooks.rattle?.(r.x, r.y, r.z);
      }
      const on = (this.rattleOn[i] = Math.max(0, (this.rattleOn[i] as number) - dt));
      const h = this.town.rattlers.find((q) => Math.abs(q.z - r.z) < 0.5 && Math.abs(q.x - r.x) < 0.6);
      if (h) {
        const a = on > 0 ? Math.sin(this.time * 71 + i) * 0.014 * Math.min(1, on * 3) : 0;
        h.mesh.position.x = h.x + a * h.nx;
        h.mesh.rotation.z = a * 0.35;
      }
    }
  }

  private updateLightning(dt: number, px: number, pz: number): void {
    this.nextBolt -= dt;
    if (this.nextBolt <= 0 && this.sim.s.phase === "play") {
      this.nextBolt = 16 + Math.random() * 22;
      this.strike(false);
    }
    let level = 0;
    if (this.boltPlan.length > 0) {
      this.boltT += dt;
      for (const b of this.boltPlan) {
        const a = this.boltT - b.at;
        if (a >= 0) level = Math.max(level, b.level * Math.exp(-a * 11));
      }
      if (this.boltT > 1.6) this.boltPlan = [];
    }
    this.flash = level;
    this.bolt.position.set(px - 40, 70, pz - 60);
    this.bolt.target.position.set(px, 0, pz);
  }

  /** Renderer facts for the debug overlay and the tests. */
  info(): { calls: number; triangles: number; frameMs: number; pixelRatio: number } {
    return { calls: this.stats.calls, triangles: this.stats.triangles, frameMs: this.frameAvg, pixelRatio: this.pixelRatio };
  }
}

/** Condensation on the glass: mottled, with runs where drops have gone down. */
function frostTexture(): THREE.Texture {
  const w = 256;
  const h = 256;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");
  if (!ctx) throw new Error("2d canvas unavailable");
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#9aa9b3");
  g.addColorStop(0.55, "#b9c6cd");
  g.addColorStop(1, "#7e8c95");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
  let seed = 77;
  const rnd = (): number => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 0; i < 900; i++) {
    const v = 120 + rnd() * 110;
    ctx.fillStyle = `rgba(${v},${v + 6},${v + 12},${0.05 + rnd() * 0.08})`;
    const r = 2 + rnd() * 9;
    ctx.beginPath();
    ctx.arc(rnd() * w, rnd() * h, r, 0, Math.PI * 2);
    ctx.fill();
  }
  for (let i = 0; i < 46; i++) {
    const x = rnd() * w;
    const y = rnd() * h * 0.7;
    ctx.strokeStyle = `rgba(40,52,62,${0.12 + rnd() * 0.2})`;
    ctx.lineWidth = 0.8 + rnd() * 1.4;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + (rnd() - 0.5) * 5, y + 30 + rnd() * 150);
    ctx.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

/** The blurred shape a standing person throws on fogged glass. */
function shadeTexture(): THREE.Texture {
  const w = 192;
  const h = 288;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");
  if (!ctx) throw new Error("2d canvas unavailable");
  ctx.clearRect(0, 0, w, h);
  ctx.filter = "blur(7px)";
  ctx.fillStyle = "#fff";
  const cx = w / 2;
  // head, hung forward and to one side
  ctx.beginPath();
  ctx.ellipse(cx + 5, 62, 15, 19, 0.2, 0, Math.PI * 2);
  ctx.fill();
  // shoulders and trunk
  ctx.beginPath();
  ctx.moveTo(cx - 34, 96);
  ctx.quadraticCurveTo(cx, 78, cx + 32, 92);
  ctx.lineTo(cx + 26, 176);
  ctx.lineTo(cx - 24, 178);
  ctx.closePath();
  ctx.fill();
  // arms: one hanging, one half raised towards the glass
  ctx.lineCap = "round";
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 14;
  ctx.beginPath();
  ctx.moveTo(cx - 32, 100);
  ctx.lineTo(cx - 40, 182);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 30, 98);
  ctx.lineTo(cx + 46, 140);
  ctx.lineTo(cx + 40, 104);
  ctx.stroke();
  // legs, one trailing
  ctx.lineWidth = 19;
  ctx.beginPath();
  ctx.moveTo(cx - 12, 174);
  ctx.lineTo(cx - 20, 280);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(cx + 12, 174);
  ctx.lineTo(cx + 26, 280);
  ctx.stroke();
  ctx.filter = "none";
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function chainAlpha(): THREE.Texture {
  const s = 64;
  const c = document.createElement("canvas");
  c.width = s;
  c.height = s;
  const ctx = c.getContext("2d");
  if (!ctx) throw new Error("2d canvas unavailable");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, s, s);
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 5;
  for (let i = -s; i <= s * 2; i += s / 2) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i + s, s);
    ctx.moveTo(i, 0);
    ctx.lineTo(i - s, s);
    ctx.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping;
  t.wrapT = THREE.RepeatWrapping;
  return t;
}
