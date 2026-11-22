import * as T from 'three';
import { Builder, softMap } from './materials';
import { buildTerminal, terminalDoor } from './terminal';
import { bridgeObject, buildTown, pickupObject } from './town';
import { type Emitter } from './fixtures';
import { createCharacter } from './characters';
import { harborSky, rain, shoppingFlood, terminalFloor, water } from './weather';
import { isWall, PLAYER_START, WALKABLE } from './layout';
import type { GameState } from './simulation';

function paving() {
  const xs = [...new Set(WALKABLE.flatMap((a) => [a.x1, a.x2]))].sort((a, b) => a - b);
  const zs = [...new Set(WALKABLE.flatMap((a) => [a.z1, a.z2]))].sort((a, b) => a - b);
  const v: number[] = [];
  for (let i = 0; i < xs.length - 1; i++)
    for (let j = 0; j < zs.length - 1; j++) {
      const x = xs[i],
        xx = xs[i + 1],
        z = zs[j],
        zz = zs[j + 1],
        cx = (x + xx) / 2,
        cz = (z + zz) / 2;
      if (WALKABLE.some((a) => cx > a.x1 && cx < a.x2 && cz > a.z1 && cz < a.z2))
        v.push(x, -zz, 0, xx, -zz, 0, xx, -z, 0, x, -zz, 0, xx, -z, 0, x, -z, 0);
    }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(v, 3));
  g.computeVertexNormals();
  g.computeBoundingSphere();
  return g;
}

function actorShadow() {
  const o = new T.Mesh(
    new T.PlaneGeometry(1.2, 1.42),
    new T.MeshBasicMaterial({
      color: '#07171c',
      map: softMap(),
      transparent: true,
      opacity: 0.81,
      depthWrite: false,
    }),
  );
  o.rotation.x = -Math.PI / 2;
  return o;
}
const smooth = (a: number, b: number, dt: number, rate: number) =>
  T.MathUtils.lerp(a, b, 1 - Math.exp(-dt * rate));
const yawLerp = (a: number, b: number, dt: number) =>
  a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * (1 - Math.exp(-dt * 11));

export class HarborWorld {
  readonly scene = new T.Scene();
  readonly camera = new T.PerspectiveCamera(58, 1, 0.055, 186);
  readonly renderer: T.WebGLRenderer;
  readonly worker = createCharacter('worker');
  private characters = new Map<
    string,
    { figure: ReturnType<typeof createCharacter>; shadow: T.Mesh; fall: number }
  >();
  private sky: T.Mesh;
  private updateRain: ReturnType<typeof rain>;
  private updateWater: ReturnType<typeof water>;
  private updateFlood: ReturnType<typeof shoppingFlood>;
  private floor: ReturnType<typeof terminalFloor>;
  private fixtures: Emitter[] = [];
  private lights: T.PointLight[] = [];
  private torch = new T.SpotLight(0xffe8bb, 22, 17, 0.54, 0.78, 1.6);
  private flash = new T.PointLight(0xffbd76, 0, 11, 1.6);
  private fill = new T.PointLight(0xc5dfd4, 3.55, 4, 1.7);
  private door: T.Group;
  private bridge: T.Group;
  private pickup: T.Group;
  private silhouette = createCharacter('wanderer', 3);
  private shadow = actorShadow();
  private bodyYaw = 0;
  private doorAngle = 0;
  private boom = 1.94;
  private focus = new T.Vector3();
  private offset = new T.Vector3();
  private look = new T.Vector3();
  private direction = new T.Vector3();
  private side = new T.Vector3();
  private axis = new T.Vector3();
  private life = 0;
  private clock = 0;
  private lastX = PLAYER_START.x;
  private lastZ = PLAYER_START.z;
  private worldMeshes: { object: T.Object3D; z: number; radius: number }[] = [];
  constructor(canvas: HTMLCanvasElement) {
    this.renderer = new T.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    this.renderer.setClearColor(0x253b41);
    this.renderer.outputColorSpace = T.SRGBColorSpace;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    this.scene.fog = new T.FogExp2(0x294247, 0.021);
    this.sky = harborSky(this.scene);
    this.updateWater = water(this.scene);
    this.updateFlood = shoppingFlood(this.scene);
    const root = new T.Group(),
      b = new Builder(root),
      kit = { root, b, lights: this.fixtures };
    this.scene.add(root);
    buildTerminal(kit);
    buildTown(kit);
    b.finish();
    for (const object of root.children) {
      if (object instanceof T.Mesh && object.geometry.boundingSphere) {
        const { center, radius } = object.geometry.boundingSphere;
        this.worldMeshes.push({ object, z: center.z, radius: radius + 7 });
      } else if (object instanceof T.Sprite)
        this.worldMeshes.push({ object, z: object.position.z, radius: 3 });
    }
    this.door = terminalDoor(this.scene);
    this.bridge = bridgeObject(this.scene);
    this.pickup = pickupObject(this.scene);
    this.floor = terminalFloor();
    this.floor.object.geometry.dispose();
    this.floor.object.geometry = paving();
    this.floor.object.position.set(0, 0.014, 0);
    this.scene.add(this.floor.object);
    this.updateRain = rain(this.scene);
    this.scene.add(new T.HemisphereLight(0xb8d4d3, 0x535348, 1.25));
    const moon = new T.DirectionalLight(0xc2dede, 1.01);
    moon.position.set(-33, 39, -9);
    this.scene.add(moon);
    for (let i = 0; i < 5; i++) {
      const light = new T.PointLight(0xffffff, 1, 16, 1.78);
      this.lights.push(light);
      this.scene.add(light);
    }
    this.scene.add(this.torch, this.torch.target, this.flash, this.fill);
    this.scene.add(this.worker.root, this.silhouette.root, this.shadow);
    this.resize();
    new ResizeObserver(() => this.resize()).observe(canvas);
  }
  resize() {
    const canvas = this.renderer.domElement,
      w = Math.max(2, canvas.clientWidth),
      h = Math.max(2, canvas.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.4, 1440 / w));
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }
  reset(yaw: number) {
    this.lastX = PLAYER_START.x;
    this.lastZ = PLAYER_START.z;
    this.bodyYaw = yaw;
    this.doorAngle = 0;
    this.life = 0;
    this.boom = 1.94;
    this.clock = 0;
    for (const a of this.characters.values()) a.fall = 0;
  }
  shotRay() {
    const d = this.camera.getWorldDirection(this.axis),
      o = this.camera.position;
    return { x: o.x, y: o.y, z: o.z, dx: d.x, dy: d.y, dz: d.z };
  }
  frame(gs: GameState, yaw: number, pitch: number, dt: number) {
    const { player: q } = gs;
    this.clock += dt;
    const t = this.clock;
    const sx = Math.sin(yaw),
      cz = Math.cos(yaw);
    this.direction.set(sx, 0, -cz);
    this.side.set(cz, 0, sx);
    this.doorAngle = smooth(this.doorAngle, gs.doorOpen ? -1.5 : 0, dt, 4.5);
    this.door.rotation.y = this.doorAngle;
    this.bridge.rotation.x = (1 - gs.bridgeProgress) * 1.17;
    this.pickup.visible = !q.hasGun;
    this.life = smooth(this.life, gs.status === 'dead' ? 1 : 0, dt, 3);
    this.worker.root.position.set(q.x, 0, q.z);
    const dx = q.x - this.lastX,
      dz = q.z - this.lastZ;
    const travelYaw = dx * dx + dz * dz > 0.0000001 ? Math.atan2(dx, -dz) : this.bodyYaw;
    this.bodyYaw = yawLerp(this.bodyYaw, q.aiming || gs.shotFlash > 0 ? yaw : travelYaw, dt);
    this.lastX = q.x;
    this.lastZ = q.z;
    this.worker.root.rotation.y = -this.bodyYaw;
    const speed = q.moving && dt > 0 ? Math.min(3, Math.hypot(dx, dz) / dt) : 0;
    this.worker.pose(dt, speed, q.aiming, q.hasGun, this.life, t);
    this.shadow.position.set(q.x, 0.044, q.z + 0.05);
    let index = 0;
    for (const e of gs.enemies) {
      let a = this.characters.get(e.id);
      if (!a) {
        a = { figure: createCharacter('wanderer', index + 1), shadow: actorShadow(), fall: 0 };
        this.characters.set(e.id, a);
        this.scene.add(a.figure.root, a.shadow);
      }
      index++;
      a.figure.root.visible = e.active && Math.hypot(q.x - e.x, q.z - e.z) < 56;
      a.shadow.visible = a.figure.root.visible;
      if (!a.figure.root.visible) continue;
      a.fall = smooth(a.fall, e.mode === 'down' ? 1 : 0, dt, 5.5);
      a.figure.root.position.set(e.x, 0, e.z);
      a.figure.root.rotation.y = -e.yaw;
      a.figure.pose(
        dt,
        e.moving ? (e.mode === 'chase' ? 2 : 0.88) : 0,
        false,
        false,
        a.fall,
        t + index * 1.77,
      );
      a.shadow.position.set(e.x, 0.043, e.z);
    }
    this.silhouette.root.visible = q.z > -32;
    if (this.silhouette.root.visible) {
      const u = t * 0.088 + 0.76;
      this.silhouette.root.position.set(-11.6, 0, -6.35 - 5.3 * Math.sin(u));
      this.silhouette.root.rotation.y = Math.cos(u) >= 0 ? -0.1 : Math.PI + 0.14;
      this.silhouette.pose(dt, 0.68, false, false, 0, t + 3);
    }
    const aiming = q.aiming;
    const aimDist = aiming ? 1.4 : 1.87;
    this.focus.set(q.x, 1.48 - this.life * 0.56, q.z);
    // Sweep the entire shoulder offset against the same walls and cover as the player.
    this.offset
      .copy(this.direction)
      .multiplyScalar(-Math.cos(pitch) * aimDist)
      .addScaledVector(this.side, aiming ? 0.62 : 0.77);
    this.offset.y = 0.19 - Math.sin(pitch) * aimDist;
    const span = this.offset.length();
    let allowed = span;
    for (let d = 0.14; d <= span + 0.039; d += 0.065) {
      const s = Math.min(1, d / span),
        x = this.focus.x + this.offset.x * s,
        y = this.focus.y + this.offset.y * s,
        z = this.focus.z + this.offset.z * s;
      if (y < 0.27 || isWall(x, z, y, gs.bridgeProgress === 1, gs.doorOpen, 0.13)) {
        allowed = Math.max(0.21, d - 0.16);
        break;
      }
    }
    this.boom = allowed < this.boom ? allowed : smooth(this.boom, allowed, dt, 9);
    this.camera.position.copy(this.focus).addScaledVector(this.offset, this.boom / span);
    // In a tight corner, look down past the shoulder while keeping both the coat and the exit in view.
    const close = 1 - T.MathUtils.smoothstep(this.boom, 0.25, 1.1);
    this.camera.position.y += close * 0.43;
    const sightDistance = T.MathUtils.lerp(10, 1.85, close);
    const aimY = Math.tan(pitch) * 10;
    this.look
      .copy(this.focus)
      .addScaledVector(this.direction, sightDistance)
      .addScaledVector(this.side, T.MathUtils.lerp(aiming ? 0.25 : 0.69, 0.19, close));
    this.look.y += Math.tan(pitch) * sightDistance - (aiming ? 0.21 : 0.4) - close * 0.09;
    this.camera.lookAt(this.look);
    this.camera.fov = smooth(this.camera.fov, aiming ? 43 : 53, dt, 9);
    this.camera.updateProjectionMatrix();
    this.sky.position.set(this.camera.position.x, 9.9, this.camera.position.z);
    this.torch.position.set(q.x + cz * 0.29, 1.4, q.z + sx * 0.29);
    this.torch.target.position.copy(this.torch.position).addScaledVector(this.direction, 10);
    this.torch.target.position.y = 1.22 + aimY;
    this.torch.intensity = aiming ? 33 : 20;
    this.fill.position.copy(this.focus).addScaledVector(this.direction, -1.4).addScaledVector(this.side, 0.8);
    this.fill.position.y = 2.27;
    this.flash.position.copy(this.torch.position).addScaledVector(this.direction, 0.69);
    this.flash.intensity = gs.shotFlash * 78;
    this.fixtures.sort((a, b) => {
      const da = (a.x - q.x) ** 2 + (a.z - q.z) ** 2,
        db = (b.x - q.x) ** 2 + (b.z - q.z) ** 2;
      return da - db;
    });
    for (let i = 0; i < this.lights.length; i++) {
      const l = this.lights[i],
        f = this.fixtures[i];
      l.position.set(f.x, f.y, f.z);
      l.color.set(f.color);
      l.distance = f.range;
      l.intensity = f.energy * (0.97 + 0.03 * Math.sin(3.9 * t + f.z));
    }
    for (const item of this.worldMeshes) item.object.visible = Math.abs(q.z - item.z) < 56 + item.radius;
    this.floor.update(t);
    this.updateWater(t);
    this.updateFlood(t, q.x, q.z, q.moving);
    this.updateRain(t, this.camera.position);
    this.renderer.render(this.scene, this.camera);
  }
}
