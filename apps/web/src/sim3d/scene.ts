import {
  ArcRotateCamera,
  Color3,
  Color4,
  DirectionalLight,
  DynamicTexture,
  Engine,
  HemisphericLight,
  Mesh,
  MeshBuilder,
  Scene,
  StandardMaterial,
  TransformNode,
  UniversalCamera,
  Vector3,
} from '@babylonjs/core';
import {
  FT_TO_M,
  KSFO_28R,
  clamp,
  degToRad,
  toLocalEnuM,
  type AircraftState,
} from '@b737/shared';

/**
 * Temporary-geometry 3D world (spec §3/§7): captain-seat view, runway with
 * markings, PAPI, approach lights. ENU frame: x = east, z = north, y = up,
 * origin at the runway threshold at field elevation. Real cockpit assets
 * replace the shell in Phase 2 (ASSET_PIPELINE.md).
 */

export interface SimWorld {
  engine: Engine;
  scene: Scene;
  /** Apply an interpolated aircraft state (called per render frame). */
  update(state: AircraftState, yokeInputs: { pitch: number; roll: number }): void;
  centerView(): void;
  dispose(): void;
}

const RWY = KSFO_28R;
const FIELD_ELEV_M = RWY.elevationFtMsl * FT_TO_M;

export function createSimWorld(canvas: HTMLCanvasElement): SimWorld {
  const engine = new Engine(canvas, true, { stencil: false }, true);
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.53, 0.72, 0.92, 1);
  scene.fogMode = Scene.FOGMODE_EXP2;
  scene.fogDensity = 0.000045;
  scene.fogColor = new Color3(0.65, 0.78, 0.9);

  new HemisphericLight('hemi', new Vector3(0.2, 1, 0.1), scene).intensity = 0.75;
  const sun = new DirectionalLight('sun', new Vector3(-0.4, -0.75, 0.3), scene);
  sun.intensity = 0.9;

  // ---------- terrain ----------
  const ground = MeshBuilder.CreateGround('ground', { width: 40000, height: 40000 }, scene);
  const groundMat = new StandardMaterial('groundMat', scene);
  groundMat.diffuseColor = new Color3(0.32, 0.42, 0.3);
  groundMat.specularColor = Color3.Black();
  ground.material = groundMat;
  ground.position.y = -0.02;

  // ---------- runway (aligned to true heading) ----------
  const runwayRoot = new TransformNode('runwayRoot', scene);
  runwayRoot.rotation.y = degToRad(RWY.headingDegTrue);
  const lengthM = RWY.lengthFt * FT_TO_M;
  const widthM = RWY.widthFt * FT_TO_M;
  const runway = MeshBuilder.CreateGround('runway', { width: widthM, height: lengthM }, scene);
  runway.parent = runwayRoot;
  runway.position.z = lengthM / 2;
  runway.position.y = 0.02;
  const rwyMat = new StandardMaterial('rwyMat', scene);
  rwyMat.diffuseTexture = paintRunwayTexture(scene, lengthM, widthM);
  rwyMat.specularColor = Color3.Black();
  runway.material = rwyMat;

  // parallel taxiway (holding point side, +x = right of course)
  const taxiway = MeshBuilder.CreateGround('taxiway', { width: 25, height: lengthM }, scene);
  taxiway.parent = runwayRoot;
  taxiway.position.set(90, 0.015, lengthM / 2);
  const taxiMat = new StandardMaterial('taxiMat', scene);
  taxiMat.diffuseColor = new Color3(0.35, 0.35, 0.36);
  taxiMat.specularColor = Color3.Black();
  taxiway.material = taxiMat;
  const connector = MeshBuilder.CreateGround('connector', { width: 100, height: 23 }, scene);
  connector.parent = runwayRoot;
  connector.position.set(45, 0.015, 40);
  connector.material = taxiMat;

  // approach lights: simple centerline bars before the threshold
  const lightMatWhite = new StandardMaterial('appLight', scene);
  lightMatWhite.emissiveColor = new Color3(1, 1, 0.9);
  for (let d = 60; d <= 900; d += 60) {
    const bar = MeshBuilder.CreateBox('appl', { width: 4, height: 0.4, depth: 0.6 }, scene);
    bar.parent = runwayRoot;
    bar.position.set(0, 0.6, -d);
    bar.material = lightMatWhite;
  }

  // PAPI (left side, ~300 m past threshold)
  const papiLights: Mesh[] = [];
  const papiMats: StandardMaterial[] = [];
  for (let i = 0; i < 4; i++) {
    const box = MeshBuilder.CreateBox(`papi${i}`, { size: 1.2 }, scene);
    box.parent = runwayRoot;
    box.position.set(-widthM / 2 - 12 - i * 3.5, 0.8, 300);
    const mat = new StandardMaterial(`papiMat${i}`, scene);
    mat.emissiveColor = Color3.White();
    box.material = mat;
    papiLights.push(box);
    papiMats.push(mat);
  }

  // ---------- aircraft + captain camera ----------
  const aircraft = new TransformNode('aircraft', scene);
  const camera = new UniversalCamera('captain', new Vector3(-0.51, 3.7, 0.8), scene);
  camera.parent = aircraft;
  camera.minZ = 0.1;
  camera.maxZ = 45000;
  camera.fov = 1.15;
  camera.rotation.set(0, 0, 0);
  camera.inputs.clear(); // we drive the view ourselves (mouse look below)
  scene.activeCamera = camera;

  // simple cockpit shell fixed to the aircraft (temporary geometry)
  const shellMat = new StandardMaterial('shellMat', scene);
  shellMat.diffuseColor = new Color3(0.13, 0.14, 0.16);
  shellMat.specularColor = Color3.Black();
  const dash = MeshBuilder.CreateBox('dash', { width: 3.4, height: 0.85, depth: 0.7 }, scene);
  dash.parent = aircraft;
  dash.position.set(0, 3.25, 2.15);
  dash.material = shellMat;
  const glareshield = MeshBuilder.CreateBox('glare', { width: 3.4, height: 0.08, depth: 0.9 }, scene);
  glareshield.parent = aircraft;
  glareshield.position.set(0, 3.72, 2.1);
  glareshield.material = shellMat;
  const pillarL = MeshBuilder.CreateBox('pillarL', { width: 0.14, height: 1.6, depth: 0.14 }, scene);
  pillarL.parent = aircraft;
  pillarL.position.set(-1.55, 4.15, 2.3);
  pillarL.material = shellMat;
  const pillarC = pillarL.clone('pillarC');
  pillarC.position.set(0, 4.15, 2.45);
  const pillarR = pillarL.clone('pillarR');
  pillarR.position.set(1.55, 4.15, 2.3);
  const roof = MeshBuilder.CreateBox('roof', { width: 3.4, height: 0.12, depth: 1.6 }, scene);
  roof.parent = aircraft;
  roof.position.set(0, 4.95, 1.7);
  roof.material = shellMat;
  const sideL = MeshBuilder.CreateBox('sideL', { width: 0.1, height: 1.7, depth: 1.7 }, scene);
  sideL.parent = aircraft;
  sideL.position.set(-1.72, 4.1, 1.3);
  sideL.material = shellMat;
  const sideR = sideL.clone('sideR');
  sideR.position.set(1.72, 4.1, 1.3);

  // yoke (visual position follows the pilot's input device)
  const yokeRoot = new TransformNode('yokeRoot', scene);
  yokeRoot.parent = aircraft;
  yokeRoot.position.set(-0.51, 2.75, 1.5);
  const column = MeshBuilder.CreateCylinder('column', { height: 0.55, diameter: 0.07 }, scene);
  column.parent = yokeRoot;
  column.position.y = 0.25;
  column.material = shellMat;
  const wheel = MeshBuilder.CreateTorus('yoke', { diameter: 0.42, thickness: 0.05 }, scene);
  wheel.parent = yokeRoot;
  wheel.position.y = 0.55;
  wheel.rotation.x = Math.PI / 2.4;
  const yokeMat = new StandardMaterial('yokeMat', scene);
  yokeMat.diffuseColor = new Color3(0.08, 0.08, 0.09);
  wheel.material = yokeMat;

  // ---------- mouse look ----------
  let lookYaw = 0;
  let lookPitch = 0;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  canvas.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
  });
  window.addEventListener('pointerup', () => (dragging = false));
  window.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    lookYaw = clamp(lookYaw + (e.clientX - lastX) * 0.003, -2.4, 2.4);
    lookPitch = clamp(lookPitch + (e.clientY - lastY) * 0.003, -0.5, 0.7);
    lastX = e.clientX;
    lastY = e.clientY;
  });
  canvas.addEventListener('dblclick', () => {
    lookYaw = 0;
    lookPitch = 0;
  });

  const resize = (): void => engine.resize();
  window.addEventListener('resize', resize);

  return {
    engine,
    scene,
    update(state, yoke) {
      const { eastM, northM } = toLocalEnuM(
        RWY.thresholdLatDeg,
        RWY.thresholdLonDeg,
        state.position.latDeg,
        state.position.lonDeg,
      );
      const altAglOfFieldM = state.position.altitudeFtMsl * FT_TO_M - FIELD_ELEV_M;
      aircraft.position.set(eastM, altAglOfFieldM, northM);
      // heading true = mag + variation
      const headingTrue = state.attitude.headingDegMag + RWY.magneticVariationDeg;
      aircraft.rotation.y = degToRad(headingTrue);
      aircraft.rotation.x = degToRad(-state.attitude.pitchDeg);
      aircraft.rotation.z = degToRad(-state.attitude.rollDeg);
      camera.rotation.y = lookYaw;
      camera.rotation.x = lookPitch;
      // yoke visual from input (explicitly a pending-command display, spec §7)
      yokeRoot.rotation.z = -yoke.roll * 1.1;
      yokeRoot.rotation.x = yoke.pitch * 0.25;

      // PAPI: light i is white above its threshold angle
      const distToPapiM = Math.hypot(eastM, northM - 300);
      const angleDeg =
        distToPapiM > 50 ? (Math.atan2(altAglOfFieldM, distToPapiM) * 180) / Math.PI : 3;
      const thresholds = [3.5, 3.2, 2.8, 2.5];
      thresholds.forEach((th, i) => {
        papiMats[i]!.emissiveColor =
          angleDeg > th ? new Color3(1, 1, 0.95) : new Color3(1, 0.15, 0.1);
      });
    },
    centerView() {
      lookYaw = 0;
      lookPitch = 0;
    },
    dispose() {
      window.removeEventListener('resize', resize);
      scene.dispose();
      engine.dispose();
    },
  };
}

/** Painted runway texture: centerline, threshold bars, aim point, edges. */
function paintRunwayTexture(scene: Scene, lengthM: number, widthM: number): DynamicTexture {
  const texW = 256;
  const texH = 4096;
  const tex = new DynamicTexture('rwyTex', { width: texW, height: texH }, scene, true);
  const ctx = tex.getContext() as unknown as CanvasRenderingContext2D;
  const mY = texH / lengthM; // meters → px along runway (v axis, 0 = threshold end)
  const mX = texW / widthM;

  ctx.fillStyle = '#3c3c40';
  ctx.fillRect(0, 0, texW, texH);
  ctx.fillStyle = '#ffffff';
  // threshold piano keys (8 bars)
  const barW = 8 * mX;
  for (let i = 0; i < 8; i++) {
    const x = texW / 2 + (i - 4) * barW * 1.5 + barW * 0.25;
    ctx.fillRect(x, texH - 45 * mY, barW, 30 * mY);
  }
  // centerline dashes: 30 m dash / 20 m gap
  const dashW = 1 * mX * 2;
  for (let d = 75; d < lengthM - 60; d += 50) {
    ctx.fillRect(texW / 2 - dashW / 2, texH - (d + 30) * mY, dashW, 30 * mY);
  }
  // aim point blocks at 300 m
  ctx.fillRect(texW / 2 - 14 * mX, texH - 345 * mY, 6 * mX, 45 * mY);
  ctx.fillRect(texW / 2 + 8 * mX, texH - 345 * mY, 6 * mX, 45 * mY);
  // edge lines
  ctx.fillRect(2, 0, 2 * mX, texH);
  ctx.fillRect(texW - 2 - 2 * mX, 0, 2 * mX, texH);
  tex.update();
  return tex;
}

/** Free spectator camera helper (diagnostics use). */
export function addDebugCamera(scene: Scene): ArcRotateCamera {
  return new ArcRotateCamera('debug', -Math.PI / 2, 1.1, 120, Vector3.Zero(), scene);
}
