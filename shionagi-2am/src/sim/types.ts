// Plain-data types for the simulation. Everything in `SimState` must survive
// `structuredClone` (checkpoints are deep copies), so: no classes, no functions.

import type { Box, Rect } from "./geom";

export type Surface = "tile" | "asphalt" | "water" | "metal" | "concrete";

export type ZoneName =
  | "terminal"
  | "lane"
  | "plaza"
  | "street"
  | "alley"
  | "junction"
  | "yard"
  | "bridge"
  | "forecourt";

export interface ZoneDef extends Rect {
  name: ZoneName;
  /** indoor zones muffle the rain */
  indoor: boolean;
}

export interface SurfaceZone extends Rect {
  surface: Surface;
}

// ---------------------------------------------------------------- level data

export type LightMode = "steady" | "flicker" | "buzz" | "pulse" | "blink" | "blinkAlt" | "beacon";

export interface LightDef {
  x: number;
  y: number;
  z: number;
  color: number;
  /** relative brightness; the view scales it to candela */
  power: number;
  range: number;
  mode: LightMode;
  seed: number;
  /** size of the glow sprite in metres (0 = none) */
  glow: number;
  /** lights in a group are switched by game state (e.g. the bridge warning lamp) */
  group?: "bridgeWarn" | "guide";
  /** draw a streak reflection on the wet ground under the light */
  streak: boolean;
}

export type Facing = "n" | "s" | "e" | "w";

export type CarModel = "sedan" | "taxi" | "kei" | "boxtruck" | "patrol" | "van" | "utility";

export type SignStyle = "exit" | "evac" | "plate" | "warn" | "arch" | "notice" | "station";

export type MatName =
  | "termWall"
  | "termInner"
  | "termTrim"
  | "concrete"
  | "concreteDark"
  | "warehouse"
  | "winch"
  | "booth"
  | "metalDark"
  | "metalPaint"
  | "wood"
  | "crate"
  | "pallet"
  | "sandbag"
  | "container"
  | "dumpster"
  | "vending"
  | "locker"
  | "counter"
  | "bin"
  | "ac"
  | "planter"
  | "hedge"
  | "stone"
  | "tarp"
  | "pipe"
  | "roof"
  | "station"
  | "stationTrim";

export type Prop =
  | { k: "box"; x0: number; z0: number; x1: number; z1: number; y0: number; y1: number; mat: MatName }
  | { k: "building"; x0: number; z0: number; x1: number; z1: number; h: number; tone: number }
  | {
      k: "shop";
      face: "e" | "w";
      /** x of the shop front */
      x: number;
      /** x of the back wall */
      back: number;
      z0: number;
      z1: number;
      h: number;
      name: string;
      sub: string;
      tone: number;
      shutter: "closed" | "gap" | "half" | "glass";
      rattle: boolean;
    }
  | { k: "car"; x0: number; z0: number; x1: number; z1: number; heading: 0 | 1 | 2 | 3; model: CarModel; color: number }
  | { k: "glassWall"; x0: number; x1: number; z: number; doorX0: number; doorX1: number; h: number }
  | {
      k: "door";
      id: string;
      /** hinge position */
      hx: number;
      hz: number;
      /** unit direction from the hinge along the closed leaf */
      ax: number;
      az: number;
      len: number;
      h: number;
      /** +1 / -1: which way the leaf swings open */
      swing: number;
      style: "staff" | "steel" | "glass";
    }
  | {
      k: "sign";
      x: number;
      y: number;
      z: number;
      face: Facing;
      w: number;
      h: number;
      lines: string[];
      style: SignStyle;
      arrow?: "l" | "r" | "u";
      lit: boolean;
    }
  | { k: "lamp"; light: number; fixture: "ceiling" | "wall" | "pole" | "flasher" | "beacon" | "bare" | "none"; face?: Facing }
  | { k: "bench"; x0: number; z0: number; x1: number; z1: number; back: Facing }
  | { k: "rail"; x0: number; z0: number; x1: number; z1: number; h: number; style: "rail" | "barricade" | "hedge" | "chain" }
  | { k: "pole"; x: number; z: number; h: number; kind: "lamp" | "clock" | "flag" | "utility" | "speaker" }
  | { k: "ground"; x0: number; z0: number; x1: number; z1: number; y: number; mat: "asphalt" | "tile" | "concrete" | "grate" | "paving" | "lino" }
  | { k: "water"; x0: number; z0: number; x1: number; z1: number; y: number; kind: "flood" | "canal" | "sea" }
  | { k: "ceiling"; x0: number; z0: number; x1: number; z1: number; y: number }
  | { k: "bridge"; x0: number; x1: number; z0: number; z1: number }
  | { k: "item"; id: string; kind: "gun" | "ammo" | "medkit"; x: number; y: number; z: number }
  | { k: "panel"; x: number; z: number }
  | { k: "sluice"; x: number; z: number }
  | { k: "monument"; x0: number; z0: number; x1: number; z1: number }
  | { k: "canopy"; x0: number; z0: number; x1: number; z1: number; y: number }
  | { k: "arch"; x0: number; x1: number; z: number }
  | { k: "bike"; x: number; z: number; rot: number; fallen: boolean }
  | { k: "aframe"; x: number; z: number; rot: number }
  | { k: "heap"; x0: number; z0: number; x1: number; z1: number; h: number }
  | { k: "washout"; x0: number; z0: number; x1: number; z1: number };

export type InteractKind = "door" | "examine" | "gun" | "ammo" | "medkit" | "panel" | "exit";

export interface InteractDef {
  id: string;
  kind: InteractKind;
  x: number;
  z: number;
  r: number;
  label: string;
  /** line shown after an `examine` */
  note?: string;
}

export interface EnemyDef {
  id: string;
  x: number;
  z: number;
  yaw: number;
  /** patrol loop; a single-point (or empty) patrol means "stand at home" */
  patrol: { x: number; z: number }[];
  /** ping-pong along the patrol instead of looping */
  pingPong: boolean;
  dormant: boolean;
  /** visual variant */
  look: number;
}

export interface Checkpoint {
  id: string;
  /** entering this rectangle activates the checkpoint */
  area: Rect;
  x: number;
  z: number;
  yaw: number;
}

export interface Level {
  boxes: Box[];
  dyn: Record<string, Box>;
  props: Prop[];
  lights: LightDef[];
  zones: ZoneDef[];
  surfaces: SurfaceZone[];
  interactables: InteractDef[];
  enemies: EnemyDef[];
  checkpoints: Checkpoint[];
  start: { x: number; z: number; yaw: number };
  bounds: Rect;
  /** where the bridge machinery makes its noise */
  winch: { x: number; z: number };
  /** shutters that rattle (view/audio only) */
  rattles: { x: number; y: number; z: number }[];
}

// ---------------------------------------------------------------- sim state

export interface PlayerState {
  x: number;
  z: number;
  /** previous step position (render interpolation) */
  px: number;
  pz: number;
  vx: number;
  vz: number;
  yaw: number;
  pitch: number;
  bodyYaw: number;
  hp: number;
  hurtT: number;
  hasGun: boolean;
  ammo: number;
  aiming: boolean;
  /** 0..1 aim blend */
  aim: number;
  fireCd: number;
  /** distance accumulator for footsteps */
  stride: number;
  /** walk-cycle phase in radians, advances with distance */
  gait: number;
  speed: number;
  running: boolean;
  recoil: number;
  surface: Surface;
}

export type EnemyMode =
  | "dormant"
  | "home"
  | "suspicious"
  | "investigate"
  | "search"
  | "chase"
  | "windup"
  | "recover"
  | "stagger"
  | "dead";

export interface EnemyState {
  id: string;
  x: number;
  z: number;
  px: number;
  pz: number;
  yaw: number;
  hp: number;
  mode: EnemyMode;
  /** seconds spent in the current mode */
  modeT: number;
  aware: number;
  sees: boolean;
  /** investigate / last-known target */
  tx: number;
  tz: number;
  /** investigate priority of the noise being followed */
  noisePri: number;
  goSpeed: number;
  /** seconds since the player was last seen while chasing */
  lostT: number;
  path: { x: number; z: number }[] | null;
  pathI: number;
  repathT: number;
  patrolI: number;
  patrolDir: number;
  waitT: number;
  gait: number;
  stride: number;
  speed: number;
  vocalT: number;
  searchYaw: number;
  struck: boolean;
}

export type Phase = "play" | "dead" | "clear";

export interface Stats {
  shots: number;
  hits: number;
  kills: number;
  damage: number;
  deaths: number;
  distance: number;
  detections: number;
}

export interface CamState {
  x: number;
  y: number;
  z: number;
  dist: number;
  side: number;
}

export interface SimState {
  time: number;
  phase: Phase;
  /** seconds since death / clear */
  phaseT: number;
  seed: number;
  player: PlayerState;
  enemies: EnemyState[];
  used: Record<string, boolean>;
  doors: Record<string, boolean>;
  fired: Record<string, boolean>;
  bridge: { state: "up" | "lowering" | "down"; t: number; noiseT: number };
  cam: CamState;
  prompt: { id: string; label: string } | null;
  message: { text: string; ttl: number } | null;
  zone: ZoneName;
  checkpoint: string;
  /** pending scripted events: [fire time, id] */
  timers: { at: number; id: string }[];
  stats: Stats;
}

export interface InputFrame {
  /** strafe: +1 right */
  mx: number;
  /** forward: +1 forward */
  mz: number;
  run: boolean;
  aim: boolean;
  /** edge-triggered */
  fire: boolean;
  /** edge-triggered */
  interact: boolean;
}

export const NO_INPUT: InputFrame = { mx: 0, mz: 0, run: false, aim: false, fire: false, interact: false };

export type VocalKind = "idle" | "suspicious" | "alert" | "attack" | "hurt" | "die" | "search";

export type SimEvent =
  | { t: "step"; x: number; z: number; surface: Surface; run: boolean }
  | { t: "estep"; id: string; x: number; z: number; surface: Surface; fast: boolean }
  | { t: "vocal"; id: string; x: number; z: number; kind: VocalKind }
  | {
      t: "shot";
      x: number;
      y: number;
      z: number;
      hx: number;
      hy: number;
      hz: number;
      hit: "none" | "world" | "body" | "head";
    }
  | { t: "dry" }
  | { t: "swipe"; id: string; x: number; z: number; hit: boolean }
  | { t: "hurt"; hp: number }
  | { t: "death" }
  | { t: "pickup"; kind: "gun" | "ammo" | "medkit"; id: string }
  | { t: "door"; id: string; x: number; z: number }
  | { t: "locked"; id: string; x: number; z: number }
  | { t: "bridge"; phase: "start" | "down" }
  | { t: "thunder"; near: boolean }
  | { t: "cue"; id: string; x: number; z: number }
  | { t: "checkpoint"; id: string }
  | { t: "hint"; id: string }
  | { t: "retry" }
  | { t: "clear" };
