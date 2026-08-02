import {
  AbstractMesh,
  Matrix,
  Quaternion,
  SceneLoader,
  TransformNode,
  Vector3,
  type Scene,
} from '@babylonjs/core';
import '@babylonjs/loaders/glTF';
import {
  clamp,
  degToRad,
  flapDetentToNorm,
  type AircraftState,
  type AutobrakeSetting,
  type FLAP_DETENTS,
} from '@b737/shared';
import { COCKPIT_CONTROLS } from '@b737/cockpit-model';

/**
 * Loads the converted 737-800YV cockpit (Phase 2 asset pipeline) and binds:
 *  - assembly: instance offset chains from the FG model XMLs
 *  - animation: lever/handle meshes rotate about the FG-declared pivots,
 *    driven from BACKEND state (never local UI state, spec §7)
 *  - picking: registry meshNames → control interactions
 *
 * All coordinates below the wrapper are in the FG model frame
 * (+x aft, +y right, +z up); the wrapper maps that into the Babylon world
 * (x right, y up, z forward).
 */

interface BindingsFile {
  version: number;
  instances: { id: string; ac: string; gltf: string; chain: { t: number[]; rDeg: number[] }[] }[];
  animations: {
    objects: string[];
    type: 'rotate' | 'translate';
    fgProperty: string;
    axis: number[];
    center: number[];
    factor: number;
    offsetDeg: number;
    table: [number, number][] | null;
  }[];
}

export interface CockpitInteraction {
  controlId: string;
  interaction: 'lever' | 'toggle' | 'click' | 'drag' | 'rotary';
  label: string;
  trainingHint?: string;
}

export interface LoadedCockpit {
  root: TransformNode;
  /** Update animated meshes from a state sample (called per frame). */
  update(state: AircraftState, yoke: { pitch: number; roll: number }): void;
  /** Interaction metadata for a picked mesh, if it is interactive. */
  interactionFor(mesh: AbstractMesh): CockpitInteraction | null;
  meshCount: number;
}

/**
 * FG (aft,right,up) point → Babylon aircraft-space. This is the *desired*
 * mapping D; the wrapper compensates whatever transform the glTF loader
 * applies so that content ends up exactly here (computed at load time).
 */
export function fgToAircraft(p: { x: number; y: number; z: number }): Vector3 {
  return new Vector3(p.y, p.z + CABIN_FLOOR_HEIGHT_M, -p.x);
}

/** Desired FG→aircraft linear map D as a Babylon matrix (row-vector form). */
function desiredMapMatrix(): Matrix {
  // rows are images of the FG basis vectors: aft→-z, right→+x, up→+y
  return Matrix.FromValues(
    0, 0, -1, 0,
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 0, 1,
  );
}

/** Cockpit floor height above ground (gear datum) — visual approximation. */
const CABIN_FLOOR_HEIGHT_M = 2.55;

const AUTOBRAKE_FG_VALUE: Record<AutobrakeSetting, number> = {
  RTO: 0,
  OFF: 1,
  '1': 2,
  '2': 3,
  '3': 4,
  MAX: 5,
};

interface AnimatedTarget {
  pivot: TransformNode;
  axis: Vector3;
  spec: BindingsFile['animations'][number];
  baseQuaternion: Quaternion;
  basePosition: Vector3;
}

export async function loadCockpit(
  scene: Scene,
  aircraft: TransformNode,
): Promise<LoadedCockpit | null> {
  let bindings: BindingsFile;
  try {
    const res = await fetch('/cockpit/cockpit-bindings.json');
    if (!res.ok) return null;
    bindings = (await res.json()) as BindingsFile;
  } catch {
    return null;
  }

  const wrapper = new TransformNode('cockpitRoot', scene);
  wrapper.parent = aircraft;
  wrapper.position = new Vector3(0, CABIN_FLOOR_HEIGHT_M, 0);

  // glTF nodes with multiple primitives surface as TransformNodes with
  // child meshes — index both kinds by name for animation + picking.
  const meshByName = new Map<string, TransformNode[]>();
  const chainLinks: { node: TransformNode; t: Vector3 }[] = [];
  let loaderRootSample: TransformNode | null = null;
  let meshCount = 0;

  for (const instance of bindings.instances) {
    if (scene.isDisposed) return null;
    const instanceNode = new TransformNode(`inst:${instance.id}`, scene);
    instanceNode.parent = wrapper;
    // FG offset chain: translations stored in FG coords; converted to the
    // loader's content frame once L is known (below)
    let node = instanceNode;
    instance.chain.forEach((link, i) => {
      const child = new TransformNode(`inst:${instance.id}:chain${i}`, scene);
      child.parent = node;
      const [pitchDeg = 0, rollDeg = 0, headingDeg = 0] = link.rDeg;
      if (pitchDeg || rollDeg || headingDeg) {
        console.warn(
          `[cockpit] non-zero offset rotation on ${instance.id} chain${i} — not yet supported, ignoring`,
        );
      }
      chainLinks.push({
        node: child,
        t: new Vector3(link.t[0] ?? 0, link.t[1] ?? 0, link.t[2] ?? 0),
      });
      node = child;
    });

    try {
      const result = await SceneLoader.ImportMeshAsync('', '/cockpit/', instance.gltf, scene);
      if (scene.isDisposed) return null;
      const index = (n: TransformNode): void => {
        if (!n.name || n.name === '__root__') return;
        const list = meshByName.get(n.name) ?? [];
        list.push(n);
        meshByName.set(n.name, list);
      };
      for (const mesh of result.meshes) {
        if (mesh.name === '__root__') {
          mesh.parent = node;
          if (!loaderRootSample) loaderRootSample = mesh as unknown as TransformNode;
          continue;
        }
        meshCount += 1;
        index(mesh);
      }
      for (const tn of result.transformNodes) index(tn);
    } catch (err) {
      if (!scene.isDisposed) console.warn(`[cockpit] failed to load ${instance.gltf}:`, err);
    }
  }
  if (meshCount === 0 || !loaderRootSample) {
    wrapper.dispose();
    return null;
  }

  // ---- compensate the loader's content transform ----
  // The glTF importer applies its own handedness transform L on each __root__.
  // We need content-FG-coords → aircraft frame to be exactly D (fgToAircraft),
  // so the wrapper gets W = L⁻¹·D, and chain translations become t·L.
  const L = composeLocalLinear(loaderRootSample);
  const W = L.clone().invert().multiply(desiredMapMatrix());
  const wRotation = new Quaternion();
  const wScale = new Vector3();
  W.decompose(wScale, wRotation, undefined);
  wrapper.rotationQuaternion = wRotation;
  wrapper.scaling = wScale;
  for (const link of chainLinks) {
    link.node.position = Vector3.TransformNormal(link.t, L);
  }

  // ---------- animation bindings ----------
  const animated: AnimatedTarget[] = [];
  for (const spec of bindings.animations) {
    for (const objName of spec.objects) {
      for (const mesh of meshByName.get(objName) ?? []) {
        const pivot = insertPivot(scene, mesh, spec.center);
        if (!pivot) continue;
        animated.push({
          pivot,
          axis: new Vector3(spec.axis[0] ?? 0, spec.axis[1] ?? 0, spec.axis[2] ?? 0).normalize(),
          spec,
          baseQuaternion: pivot.rotationQuaternion?.clone() ?? Quaternion.Identity(),
          basePosition: pivot.position.clone(),
        });
      }
    }
  }

  // ---------- interactive mesh registry ----------
  const interactive = new Map<TransformNode, CockpitInteraction>();
  for (const control of COCKPIT_CONTROLS) {
    for (const name of control.meshNames) {
      for (const node of meshByName.get(name) ?? []) {
        const info: CockpitInteraction = {
          controlId: control.id,
          interaction: control.interaction,
          label: control.label,
          trainingHint: control.trainingHint,
        };
        interactive.set(node, info);
        // make the node and any child primitives pickable
        if (node instanceof AbstractMesh) node.isPickable = true;
        for (const child of node.getChildMeshes(false)) child.isPickable = true;
      }
    }
  }

  return {
    root: wrapper,
    meshCount,
    interactionFor: (mesh) => {
      // primitives sit below the named node — walk up until a match
      let current: TransformNode | null = mesh;
      while (current) {
        const hit = interactive.get(current);
        if (hit) return hit;
        current = (current.parent as TransformNode | null) ?? null;
      }
      return null;
    },
    update: (state, yoke) => {
      for (const target of animated) {
        const value = resolveFgProperty(target.spec.fgProperty, state, yoke);
        if (value === null) continue;
        const out = evaluate(target.spec, value);
        if (target.spec.type === 'rotate') {
          const q = Quaternion.RotationAxis(target.axis, degToRad(out));
          target.pivot.rotationQuaternion = q.multiply(target.baseQuaternion);
        } else {
          target.pivot.position = target.basePosition.add(target.axis.scale(out));
        }
      }
    },
  };
}

/**
 * Insert a pivot node at the FG-declared center so the mesh rotates about the
 * lever hinge. Assumes ancestor transforms inside the model are translations
 * (true for these AC3D exports — 'rot' matrices are absent on animated parts).
 */
function insertPivot(scene: Scene, mesh: TransformNode, center: number[]): TransformNode | null {
  const parent = mesh.parent;
  if (!parent) return null;
  // accumulated translation from model root (the __root__ child) to parent
  let acc = new Vector3(0, 0, 0);
  let walker: TransformNode | null = parent as TransformNode;
  while (walker && walker.name !== '__root__' && !walker.name.startsWith('inst:')) {
    acc = acc.add(walker.position);
    walker = walker.parent as TransformNode | null;
  }
  const pivotPos = new Vector3(center[0] ?? 0, center[1] ?? 0, center[2] ?? 0).subtract(acc);
  const pivot = new TransformNode(`pivot:${mesh.name}`, scene);
  pivot.parent = parent;
  pivot.position = pivotPos;
  mesh.parent = pivot;
  mesh.position = mesh.position.subtract(pivotPos);
  return pivot;
}

/** Piecewise-linear interpolation table or factor/offset evaluation. */
function evaluate(spec: BindingsFile['animations'][number], value: number): number {
  if (spec.table && spec.table.length >= 2) {
    const t = spec.table;
    if (value <= t[0]![0]) return t[0]![1];
    for (let i = 0; i + 1 < t.length; i++) {
      const [x0, y0] = t[i]!;
      const [x1, y1] = t[i + 1]!;
      if (value <= x1) {
        const f = x1 === x0 ? 0 : (value - x0) / (x1 - x0);
        return y0 + (y1 - y0) * f;
      }
    }
    return t[t.length - 1]![1];
  }
  return spec.offsetDeg + value * spec.factor;
}

/** FG animation property → current value from state / input (spec §7). */
function resolveFgProperty(
  prop: string,
  state: AircraftState,
  yoke: { pitch: number; roll: number },
): number | null {
  switch (prop) {
    case 'controls/engines/engine[0]/throttle':
      return state.engines.left.throttleLeverNorm;
    case 'controls/engines/engine[1]/throttle':
      return state.engines.right.throttleLeverNorm;
    case 'engines/engine[0]/reverser-pos-norm':
      return state.engines.left.reverserNorm;
    case 'engines/engine[1]/reverser-pos-norm':
      return state.engines.right.reverserNorm;
    case 'controls/flight/flaps':
      return flapDetentToNorm(state.controls.flapHandleDetent as (typeof FLAP_DETENTS)[number]);
    case 'b737/controls/flight/spoilers-lever-pos':
      // FG lever detents 0..5: 0 down, 1 armed, 5 full up
      return state.controls.speedbrakeArmed
        ? 1
        : state.controls.speedbrakeLeverNorm <= 0.02
          ? 0
          : 1 + state.controls.speedbrakeLeverNorm * 4;
    case 'controls/gear/brake-parking':
      return state.controls.parkingBrakeSet ? 1 : 0;
    case 'b737/controls/gear/lever':
      // 0 = up, 1 = off, 2 = down (interpolation table domain)
      return state.controls.gearLeverDown ? 2 : 0;
    case 'controls/gear/autobrakes':
      // NON_CERTIFIED_APPROXIMATION: knob index mapping for the visual only
      return AUTOBRAKE_FG_VALUE[state.controls.autobrake];
    case 'controls/flight/elevator':
      // FG elevator: -1 = nose up; our pitch axis +1 = nose up (pending display)
      return clamp(-yoke.pitch, -1, 1);
    case 'controls/flight/aileron':
      return clamp(yoke.roll, -1, 1);
    default:
      return null;
  }
}

/** Linear part (scale·rotation) of a node's LOCAL transform, row-vector form. */
function composeLocalLinear(node: TransformNode): Matrix {
  const rotation = node.rotationQuaternion ?? Quaternion.Identity();
  const m = Matrix.Identity();
  Matrix.ComposeToRef(node.scaling, rotation, Vector3.Zero(), m);
  return m;
}
