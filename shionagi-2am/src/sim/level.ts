// The whole of Shionagi as data: colliders for the simulation and prop
// descriptors for the view come from the same calls, so they cannot drift apart.
//
// Map (north is up, the player travels north = -z):
//
//   z=-188 ┌──────── police station ────────┐
//   z=-174 ├──────────[entrance]────────────┤
//          │            forecourt           │
//   z=-146 ├────────────[bridge]────────────┤
//          │   canal  (footbridge x 23..25.5)
//   z=-132 ├── quay walkway ── panel ── bridge entry
//          │   sluice yard (winch house in the middle)
//   z=-110 ├──[barricade]──[yard gate]──────┤
//          │   junction
//   z=-104 ├─ main street (x -5..5) ─ lane B ─ back alley (x 17..19.6)
//          │        flooded          lane A ─ back alley (x 14..16.6)
//   z=-24  ├─ arch ─ plaza ──────────────┬ T ┤
//   z=-14  ├─ ferry terminal ────────────┤lane
//   z=0    └──────────────────────────────┴───┘

import type { Box } from "./geom";
import type {
  CarModel,
  Checkpoint,
  EnemyDef,
  Facing,
  InteractDef,
  Level,
  LightDef,
  LightMode,
  MatName,
  Prop,
  SignStyle,
  SurfaceZone,
  ZoneDef,
} from "./types";

const N = 0;
const W = Math.PI / 2;
const S = Math.PI;
const E = -Math.PI / 2;

const C_AMBER = 0xffc98a;
const C_GREEN = 0x58ffa6;
const C_COLD = 0xb9d2ff;
const C_RED = 0xff2a18;
const C_FLASH = 0xff9a1c;
const C_HEAD = 0xfff1d6;
const C_GUIDE = 0xcfffe4;
const C_WHITE = 0xf2f6ff;

const CAR_DIMS: Record<CarModel, { len: number; wid: number; h: number; opaque: boolean }> = {
  sedan: { len: 4.4, wid: 1.8, h: 1.42, opaque: false },
  taxi: { len: 4.5, wid: 1.75, h: 1.5, opaque: false },
  kei: { len: 3.4, wid: 1.5, h: 1.85, opaque: true },
  boxtruck: { len: 6.0, wid: 2.3, h: 3.0, opaque: true },
  patrol: { len: 4.6, wid: 1.8, h: 1.5, opaque: false },
  van: { len: 5.2, wid: 2.2, h: 2.4, opaque: true },
  utility: { len: 5.3, wid: 2.1, h: 2.3, opaque: true },
};

class Builder {
  boxes: Box[] = [];
  dyn: Record<string, Box> = {};
  props: Prop[] = [];
  lights: LightDef[] = [];
  interactables: InteractDef[] = [];
  enemies: EnemyDef[] = [];
  rattles: { x: number; y: number; z: number }[] = [];
  private seed = 1;

  collider(
    x0: number,
    z0: number,
    x1: number,
    z1: number,
    y0: number,
    y1: number,
    f: { solid?: boolean; opaque?: boolean; thin?: boolean; ceil?: boolean; id?: string } = {},
  ): Box {
    const b: Box = {
      x0: Math.min(x0, x1),
      z0: Math.min(z0, z1),
      x1: Math.max(x0, x1),
      z1: Math.max(z0, z1),
      y0,
      y1,
      solid: f.solid ?? true,
      opaque: f.opaque ?? false,
      thin: f.thin ?? false,
      ceil: f.ceil ?? false,
      on: true,
    };
    if (f.id !== undefined) {
      b.id = f.id;
      this.dyn[f.id] = b;
    }
    this.boxes.push(b);
    return b;
  }

  /** Full-height wall: blocks walking, sight, bullets and the camera. */
  wall(x0: number, z0: number, x1: number, z1: number, h: number, mat: MatName): void {
    this.collider(x0, z0, x1, z1, 0, h, { opaque: true });
    this.props.push({ k: "box", x0, z0, x1, z1, y0: 0, y1: h, mat });
  }

  /** A solid prop drawn as a plain box. Opaque when taller than eye level. */
  block(x0: number, z0: number, x1: number, z1: number, h: number, mat: MatName, opaque = h >= 1.7): void {
    this.collider(x0, z0, x1, z1, 0, h, { opaque });
    this.props.push({ k: "box", x0, z0, x1, z1, y0: 0, y1: h, mat });
  }

  /** Visual-only box. */
  deco(x0: number, z0: number, x1: number, z1: number, y0: number, y1: number, mat: MatName): void {
    this.props.push({ k: "box", x0, z0, x1, z1, y0, y1, mat });
  }

  building(x0: number, z0: number, x1: number, z1: number, h: number, tone: number): void {
    this.collider(x0, z0, x1, z1, 0, h, { opaque: true });
    this.props.push({ k: "building", x0, z0, x1, z1, h, tone });
  }

  shop(
    face: "e" | "w",
    x: number,
    back: number,
    z0: number,
    z1: number,
    h: number,
    name: string,
    sub: string,
    tone: number,
    shutter: "closed" | "gap" | "half" | "glass" = "closed",
    rattle = false,
  ): void {
    this.collider(Math.min(x, back), z0, Math.max(x, back), z1, 0, h, { opaque: true });
    this.props.push({ k: "shop", face, x, back, z0, z1, h, name, sub, tone, shutter, rattle });
    if (rattle) this.rattles.push({ x: x + (face === "e" ? 0.15 : -0.15), y: 1.1, z: (z0 + z1) / 2 });
  }

  car(cx: number, cz: number, heading: 0 | 1 | 2 | 3, model: CarModel, color: number): void {
    const d = CAR_DIMS[model];
    const alongZ = heading === 0 || heading === 2;
    const hx = (alongZ ? d.wid : d.len) / 2;
    const hz = (alongZ ? d.len : d.wid) / 2;
    this.collider(cx - hx, cz - hz, cx + hx, cz + hz, 0, d.h, { opaque: d.opaque });
    this.props.push({ k: "car", x0: cx - hx, z0: cz - hz, x1: cx + hx, z1: cz + hz, heading, model, color });
  }

  rail(
    x0: number,
    z0: number,
    x1: number,
    z1: number,
    h: number,
    style: "rail" | "barricade" | "hedge" | "chain",
  ): void {
    this.collider(x0, z0, x1, z1, 0, h, { thin: style !== "hedge" });
    this.props.push({ k: "rail", x0, z0, x1, z1, h, style });
  }

  light(
    x: number,
    y: number,
    z: number,
    color: number,
    power: number,
    range: number,
    mode: LightMode,
    o: { glow?: number; group?: "bridgeWarn" | "guide"; streak?: boolean } = {},
  ): number {
    const def: LightDef = {
      x,
      y,
      z,
      color,
      power,
      range,
      mode,
      seed: this.seed++ * 7.31,
      glow: o.glow ?? 1.2,
      streak: o.streak ?? true,
    };
    if (o.group !== undefined) def.group = o.group;
    this.lights.push(def);
    return this.lights.length - 1;
  }

  lamp(
    fixture: "ceiling" | "wall" | "pole" | "flasher" | "beacon" | "bare" | "none",
    x: number,
    y: number,
    z: number,
    color: number,
    power: number,
    range: number,
    mode: LightMode,
    o: { glow?: number; group?: "bridgeWarn" | "guide"; streak?: boolean; face?: Facing } = {},
  ): void {
    const light = this.light(x, y, z, color, power, range, mode, o);
    const p: Prop = { k: "lamp", light, fixture };
    if (o.face !== undefined) p.face = o.face;
    this.props.push(p);
  }

  sign(
    x: number,
    y: number,
    z: number,
    face: Facing,
    w: number,
    h: number,
    lines: string[],
    style: SignStyle,
    o: { arrow?: "l" | "r" | "u"; lit?: boolean } = {},
  ): void {
    const p: Prop = { k: "sign", x, y, z, face, w, h, lines, style, lit: o.lit ?? false };
    if (o.arrow !== undefined) p.arrow = o.arrow;
    this.props.push(p);
  }

  enemy(
    id: string,
    x: number,
    z: number,
    yaw: number,
    o: { patrol?: [number, number][]; pingPong?: boolean; dormant?: boolean; look?: number } = {},
  ): void {
    this.enemies.push({
      id,
      x,
      z,
      yaw,
      patrol: (o.patrol ?? []).map(([px, pz]) => ({ x: px, z: pz })),
      pingPong: o.pingPong ?? false,
      dormant: o.dormant ?? false,
      look: o.look ?? this.enemies.length,
    });
  }

  interact(def: InteractDef): void {
    this.interactables.push(def);
  }
}

export const FLOOD_Y = 0.13;
/** Facing the aisle between the benches, the lit staff door ahead to the right: holding W crosses the hall. */
const START_YAW = -1.12;

export function buildLevel(): Level {
  const L = new Builder();

  // ================================================================ terminal
  const TH = 4.7; // shell height
  L.wall(-14.3, -14.3, -14, 0.3, TH, "termWall"); // west
  L.wall(-14.3, 0, 14.3, 0.3, TH, "termWall"); // south (pier side)
  L.wall(14, -14.3, 14.3, -12.6, TH, "termWall"); // east, north of the back door
  L.wall(14, -11.4, 14.3, 0.3, TH, "termWall"); // east, south of the back door
  L.wall(-14.3, -14.3, -12.5, -14, TH, "termWall"); // north, west of the glass
  L.wall(4.5, -14.3, 14.3, -14, TH, "termWall"); // north, east of the glass
  // fogged glass front with the dead automatic doors
  L.collider(-12.5, -14.3, 4.5, -14, 0, TH, { opaque: true });
  L.props.push({ k: "glassWall", x0: -12.5, x1: 4.5, z: -14.15, doorX0: -2, doorX1: 2, h: TH });
  // partition between the waiting hall and the staff side
  L.wall(5.85, -14, 6.15, -6.1, 4.4, "termInner");
  L.wall(5.85, -4.9, 6.15, 0, 4.4, "termInner");
  L.collider(5.85, -6.1, 6.15, -4.9, 2.1, 4.4, { solid: false, ceil: true });
  L.deco(5.85, -6.1, 6.15, -4.9, 2.1, 4.4, "termInner");
  L.collider(5.92, -6.1, 6.08, -4.9, 0, 2.1, { opaque: true, id: "D1" });
  L.props.push({ k: "door", id: "D1", hx: 6.0, hz: -4.9, ax: 0, az: -1, len: 1.2, h: 2.1, swing: 1, style: "staff" });
  // staff rooms (closed)
  L.wall(9, -10.4, 14, 0, 2.9, "termInner");
  // back door
  L.collider(14, -12.6, 14.3, -11.4, 2.1, TH, { solid: false, ceil: true });
  L.deco(14, -12.6, 14.3, -11.4, 2.1, TH, "termWall");
  L.collider(14.07, -12.6, 14.23, -11.4, 0, 2.1, { opaque: true, id: "D2" });
  L.props.push({ k: "door", id: "D2", hx: 14.15, hz: -12.6, ax: 0, az: 1, len: 1.2, h: 2.1, swing: -1, style: "steel" });
  // floors and ceilings
  L.props.push({ k: "ground", x0: -14, z0: -14, x1: 5.85, z1: 0, y: 0.02, mat: "tile" });
  L.props.push({ k: "ground", x0: 6.15, z0: -14, x1: 14, z1: 0, y: 0.02, mat: "lino" });
  L.collider(-14.3, -14.3, 5.85, 0.3, 4.4, 4.7, { solid: false, ceil: true });
  L.props.push({ k: "ceiling", x0: -14.3, z0: -14.3, x1: 5.85, z1: 0.3, y: 4.4 });
  L.collider(5.85, -14.3, 14.3, 0.3, 2.9, 4.7, { solid: false, ceil: true });
  L.props.push({ k: "ceiling", x0: 6.15, z0: -14, x1: 14, z1: 0, y: 2.9 });
  L.deco(5.85, -14.3, 14.3, 0.3, 4.4, 4.7, "roof");

  // hall furniture
  for (const z of [-4.0, -7.0, -10.0]) {
    for (const x of [-9.5, -3.9]) {
      L.collider(x, z - 0.3, x + 3.6, z + 0.3, 0, 0.9, {});
      L.props.push({ k: "bench", x0: x, z0: z - 0.3, x1: x + 3.6, z1: z + 0.3, back: "s" });
    }
  }
  L.block(-13.7, -11.5, -12.4, -5, 1.1, "counter"); // ticket counter
  L.block(-0.6, -0.85, 0.4, -0.05, 1.85, "vending");
  L.block(0.6, -0.85, 1.6, -0.05, 1.85, "vending");
  L.block(4.3, -1.2, 4.75, -0.75, 0.75, "bin");
  L.block(-11.0, -0.55, -9.4, -0.05, 1.0, "counter"); // boarding gate desk
  // staff corridor
  L.block(6.15, -3.6, 6.7, -0.4, 1.9, "locker");
  L.block(8.45, -1.6, 8.95, -1.1, 0.5, "bin");

  L.sign(-4.0, 3.2, -0.02, "n", 5.2, 0.9, ["本日の運航は 全便欠航 です"], "notice");
  L.sign(-13.95, 2.3, -8.2, "e", 3.0, 0.5, ["きっぷうりば"], "plate");
  L.sign(5.82, 2.45, -5.5, "w", 0.95, 0.34, ["非常口"], "exit", { lit: true });
  L.sign(7.55, 2.42, -13.97, "s", 0.95, 0.34, ["非常口"], "exit", { arrow: "r", lit: true });
  L.sign(13.97, 2.45, -12.0, "w", 0.95, 0.34, ["非常口"], "exit", { lit: true });
  L.sign(8.97, 1.6, -6.4, "w", 1.5, 1.0, ["夜間設備点検 当番表", "機関室／給電盤／浮桟橋", "担当：設備課"], "notice");
  L.sign(8.97, 1.7, -2.4, "w", 0.7, 0.22, ["設備室"], "plate");
  L.sign(8.97, 1.7, -9.0, "w", 0.7, 0.22, ["休憩室"], "plate");
  L.sign(-4.0, 3.75, -14.32, "n", 9.0, 0.8, ["汐凪渡船ターミナル"], "plate");

  L.lamp("ceiling", -8.6, 4.32, -1.7, C_AMBER, 1.0, 9, "steady", { streak: false });
  L.lamp("ceiling", -2.2, 4.32, -2.7, C_AMBER, 1.0, 9, "flicker", { streak: false });
  L.lamp("ceiling", 3.4, 4.32, -4.3, C_AMBER, 1.0, 9, "steady", { streak: false });
  L.lamp("none", 5.6, 2.45, -5.5, C_GREEN, 0.3, 5, "steady", { glow: 0.8, streak: false });
  L.lamp("ceiling", 7.6, 2.82, -8.6, C_AMBER, 0.8, 7, "buzz", { streak: false });
  L.lamp("none", 7.55, 2.42, -13.75, C_GREEN, 0.28, 5, "steady", { glow: 0.8, streak: false });
  L.lamp("ceiling", 11.2, 2.82, -12.2, C_AMBER, 0.8, 7, "steady", { streak: false });
  L.lamp("none", 13.75, 2.45, -12.0, C_GREEN, 0.3, 5, "steady", { glow: 0.8, streak: false });

  L.interact({ id: "D1", kind: "door", x: 6.0, z: -5.5, r: 1.5, label: "扉を開ける" });
  L.interact({
    id: "frontDoor",
    kind: "examine",
    x: 0,
    z: -13.6,
    r: 1.7,
    label: "調べる",
    note: "自動ドアは動かない。……外に、何かいる。",
  });
  L.interact({ id: "D2", kind: "door", x: 14.15, z: -12.0, r: 1.5, label: "裏口を開ける" });

  // ================================================================ plaza
  L.building(-26, -24, -14.3, 2, 9, 3); // west block
  L.props.push({ k: "ground", x0: -14, z0: -24, x1: 14, z1: -14.3, y: 0.015, mat: "paving" });
  L.props.push({ k: "pole", x: 0, z: -19.2, h: 4.6, kind: "clock" });
  L.collider(-0.18, -19.38, 0.18, -19.02, 0, 4.6, {});
  L.car(8.5, -20.3, 3, "taxi", 0x1d5a48);
  L.car(-9.0, -19.9, 1, "taxi", 0x1d5a48);
  L.block(-13.2, -23.6, -12.0, -22.4, 0.7, "planter");
  L.block(11.6, -15.9, 12.8, -14.7, 0.7, "planter");
  L.block(10.4, -15.35, 11.2, -15.05, 2.2, "metalPaint", false); // timetable totem
  L.props.push({ k: "pole", x: -4.0, z: -17.6, h: 5.8, kind: "lamp" });
  L.collider(-4.12, -17.72, -3.88, -17.48, 0, 5.8, {});
  L.lamp("none", -4.0, 5.6, -17.3, C_COLD, 2.2, 17, "flicker", { glow: 1.8 });
  // evacuation board that faces the T-junction opening
  L.props.push({ k: "pole", x: 11.6, z: -23.2, h: 2.9, kind: "utility" });
  L.collider(11.5, -23.3, 11.7, -23.1, 0, 2.9, {});
  L.sign(11.72, 2.2, -23.2, "e", 1.5, 1.15, ["避難所", "汐凪警察署", "なぎさ通り経由"], "evac", { arrow: "u", lit: true });
  // disaster-radio loudspeaker masts
  L.props.push({ k: "pole", x: 12.9, z: -18.2, h: 7.2, kind: "speaker" });
  L.collider(12.78, -18.32, 13.02, -18.08, 0, 7.2, {});
  L.props.push({ k: "pole", x: -4.45, z: -104.9, h: 7.2, kind: "speaker" });
  L.collider(-4.57, -105.02, -4.33, -104.78, 0, 7.2, {});
  // arch over the mouth of the shopping street
  L.props.push({ k: "arch", x0: -5, x1: 5, z: -24.25 });
  L.collider(-5.25, -24.5, -4.75, -24.0, 0, 5.6, {});
  L.collider(4.75, -24.5, 5.25, -24.0, 0, 5.6, {});
  L.lamp("none", 0, 4.9, -24.0, C_AMBER, 1.0, 10, "buzz", { glow: 1.4 });

  // ================================================================ service lane
  L.building(18, -24, 30, 0.6, 8, 5); // warehouse east of the lane
  L.wall(14.3, 0.3, 18, 0.6, 2.8, "concrete"); // south end
  L.wall(14, -21.5, 14.3, -14.3, 2.8, "concrete"); // lane | plaza
  L.block(16.7, -8.2, 17.9, -6.2, 1.25, "dumpster");
  L.block(14.45, -18.8, 15.55, -17.6, 1.1, "pallet");
  L.block(16.4, -4.2, 17.6, -1.8, 2.0, "metalPaint", false); // forklift
  L.block(14.45, -3.3, 15.05, -2.7, 0.9, "bin");
  L.block(15.15, -2.9, 15.75, -2.3, 0.9, "bin");
  L.lamp("wall", 17.88, 3.2, -15.5, C_AMBER, 1.0, 9, "flicker", { face: "w" });
  L.lamp("wall", 17.3, 3.5, -23.86, C_AMBER, 1.0, 8, "steady", { face: "s" });
  L.sign(17.32, 2.15, -23.97, "s", 1.25, 1.2, ["避難所", "汐凪警察署"], "evac", { arrow: "l", lit: true });

  // ================================================================ main street
  const shopsW: [number, number, number, string, string, "closed" | "gap" | "half" | "glass", boolean][] = [
    [-32, -24, 7.4, "喫茶 汐風", "COFFEE & 軽食", "glass", false],
    [-39, -32, 8.2, "鮮魚 まるなぎ", "朝どれ・仕出し", "gap", true],
    [-47, -39, 7.0, "金物 とびうお商店", "船具・工具・合鍵", "closed", false],
    [-54, -47, 8.6, "理容 ナギサ", "カット・顔そり", "closed", false],
    [-62, -54, 7.6, "しおなぎ薬局", "処方せん受付", "closed", false],
    [-70, -62, 8.8, "写真 みなと館", "証明写真・現像", "half", true],
    [-77, -70, 7.2, "酒 はまかぜ", "地酒・たばこ", "closed", false],
    [-85, -77, 8.4, "電器のウシオ", "修理うけたまわります", "closed", false],
    [-93, -85, 7.8, "食堂 かもめ亭", "定食・丼・うどん", "closed", false],
    [-110, -93, 9.6, "汐凪信用金庫", "なぎさ支店", "closed", false],
  ];
  shopsW.forEach(([z0, z1, h, name, sub, sh, rat], i) => L.shop("e", -5, -14, z0, z1, h, name, sub, i, sh, rat));
  const shopsE: [number, number, number, number, string, string, "closed" | "gap" | "half" | "glass", boolean][] = [
    [-33, -24, 14.15, 8.0, "書店 海鳴堂", "新刊・雑誌・文具", "closed", false],
    [-44, -36, 14.15, 7.2, "釣具 沖の家", "えさ・仕掛け・氷", "closed", false],
    [-51, -44, 14.15, 8.6, "青果 八百浜", "野菜・くだもの", "gap", true],
    [-58, -51, 14.15, 7.4, "精肉 丸汐", "コロッケ揚げたて", "closed", false],
    [-66, -58, 17.15, 8.8, "時計・眼鏡 ひかり堂", "電池交換", "closed", false],
    [-74, -66, 17.15, 7.6, "クリーニング 白波", "即日仕上げ", "closed", false],
    [-81, -74, 17.15, 8.2, "呉服 千鳥", "きもの・ゆかた", "closed", false],
    [-92, -84, 17.15, 7.4, "玩具 なみのこ", "プラモデル・花火", "gap", true],
    [-104, -92, 17.15, 8.9, "中華 満潮軒", "ラーメン・餃子", "closed", false],
  ];
  shopsE.forEach(([z0, z1, back, h, name, sub, sh, rat], i) => L.shop("w", 5, back, z0, z1, h, name, sub, i + 3, sh, rat));

  // vehicles and clutter on the street
  L.car(1.1, -34.5, 1, "patrol", 0xe9e9e4); // patrol car, nose towards lane A
  L.car(-3.65, -44.7, 0, "kei", 0xd8d8d0);
  L.car(2.5, -50.0, 2, "sedan", 0x2c3138);
  L.car(-0.05, -61.5, 0, "boxtruck", 0x9aa4a8);
  L.props.push({ k: "heap", x0: -5, z0: -73.2, x1: -1.6, z1: -71.6, h: 2.0 });
  L.collider(-5, -73.2, -1.6, -71.6, 0, 2.0, { opaque: true });
  L.car(3.07, -77.95, 0, "taxi", 0x1d5a48);
  L.block(-5, -93.0, 1.8, -92.2, 1.0, "sandbag");
  L.block(4.2, -39.6, 4.95, -38.6, 1.85, "vending");
  L.block(-4.95, -59.5, -4.2, -58.5, 1.85, "vending");
  L.block(3.3, -69.2, 4.9, -68.4, 0.9, "wood"); // shop wagon
  L.props.push({ k: "aframe", x: -3.9, z: -29.2, rot: 0.3 });
  L.collider(-4.2, -29.45, -3.6, -28.95, 0, 0.9, {});
  L.props.push({ k: "aframe", x: 4.25, z: -42.3, rot: -0.2 });
  L.collider(3.95, -42.55, 4.55, -42.05, 0, 0.9, {});
  L.props.push({ k: "aframe", x: -4.2, z: -56.4, rot: 0.1 });
  L.collider(-4.5, -56.65, -3.9, -56.15, 0, 0.9, {});
  L.props.push({ k: "bike", x: 4.3, z: -46.2, rot: 0.4, fallen: true });
  L.props.push({ k: "bike", x: -4.3, z: -66.3, rot: 2.1, fallen: true });
  L.props.push({ k: "bike", x: 4.4, z: -87.2, rot: 0.0, fallen: false });
  const polesW = [-30, -62, -94];
  const polesE = [-46, -78];
  for (const z of polesW) {
    L.props.push({ k: "pole", x: -4.72, z, h: 5.6, kind: "lamp" });
    L.collider(-4.84, z - 0.12, -4.6, z + 0.12, 0, 5.6, {});
  }
  for (const z of polesE) {
    L.props.push({ k: "pole", x: 4.72, z, h: 5.6, kind: "lamp" });
    L.collider(4.6, z - 0.12, 4.84, z + 0.12, 0, 5.6, {});
  }
  L.sign(-4.72, 2.5, -29.85, "s", 0.9, 0.9, ["汐凪警察署", "150m"], "evac", { arrow: "u" });
  L.sign(-4.72, 2.5, -61.85, "s", 0.9, 0.9, ["汐凪警察署", "120m"], "evac", { arrow: "u" });
  L.sign(-4.72, 2.5, -93.85, "s", 0.9, 0.9, ["汐凪警察署", "90m"], "evac", { arrow: "u" });

  L.lamp("beacon", 0.9, 1.8, -34.5, C_RED, 1.6, 14, "beacon", { glow: 1.6 });
  L.lamp("none", 4.6, 0.72, -34.5, C_HEAD, 0.6, 10, "steady", { glow: 0.5 });
  L.lamp("wall", -4.86, 3.1, -43, C_AMBER, 0.8, 8, "flicker", { face: "e" });
  L.lamp("none", -4.84, 3.7, -58, C_GREEN, 0.7, 8, "pulse", { glow: 1.3 });
  L.lamp("wall", 4.86, 3.1, -62, C_AMBER, 0.8, 8, "buzz", { face: "w" });
  L.lamp("wall", -4.86, 3.1, -81, C_AMBER, 0.8, 8, "flicker", { face: "e" });
  L.lamp("flasher", 1.2, 1.18, -92.6, C_FLASH, 0.9, 9, "blink", { glow: 1.1 });

  L.props.push({ k: "item", id: "gun", kind: "gun", x: 2.75, y: 0.97, z: -34.5 });
  L.interact({ id: "gun", kind: "gun", x: 2.75, z: -34.5, r: 1.7, label: "拳銃を拾う" });
  L.props.push({ k: "item", id: "medkitB", kind: "medkit", x: -3.6, y: 0.98, z: -45.6 });
  L.interact({ id: "medkitB", kind: "medkit", x: -3.6, z: -45.6, r: 1.7, label: "救急箱を使う" });

  // flood water
  L.props.push({ k: "water", x0: -5, z0: -100, x1: 5, z1: -27, y: FLOOD_Y, kind: "flood" });
  L.props.push({ k: "water", x0: 5, z0: -36, x1: 13.6, z1: -33, y: FLOOD_Y, kind: "flood" });
  L.props.push({ k: "water", x0: 5, z0: -84, x1: 16.6, z1: -81, y: FLOOD_Y, kind: "flood" });

  // ================================================================ back alley
  L.building(16.65, -55.5, 30, -24, 7.5, 6); // east of the first alley leg
  L.building(19.65, -71, 30, -58, 8, 7); // east of the second leg, south of the alcove
  L.building(22.2, -74, 30, -71, 8, 7); // behind the alcove
  L.building(19.65, -110, 30, -74, 8.5, 4); // north of the alcove
  L.building(19.65, -58, 30, -55.5, 7.5, 6);
  // first leg
  L.block(16.25, -28.5, 16.62, -27.6, 0.9, "ac");
  L.block(15.75, -31.6, 16.6, -30.6, 1.0, "crate");
  L.block(16.25, -41.6, 16.62, -40.7, 0.9, "ac");
  L.block(14.2, -45.6, 14.85, -44.3, 1.05, "bin");
  L.block(14.2, -52.6, 14.9, -51.4, 1.3, "crate");
  L.props.push({ k: "bike", x: 16.25, z: -49.2, rot: 1.57, fallen: false });
  L.lamp("wall", 14.3, 2.8, -30.2, C_AMBER, 0.6, 7, "flicker", { face: "e", glow: 0.9 });
  // lane A clutter
  L.block(11.4, -33.95, 12.4, -33.05, 1.0, "crate");
  // dog-leg with the first-aid box
  L.block(18.75, -56.6, 19.6, -55.55, 0.72, "crate");
  L.props.push({ k: "item", id: "medkitA", kind: "medkit", x: 19.15, y: 0.74, z: -56.1 });
  L.interact({ id: "medkitA", kind: "medkit", x: 19.15, z: -56.1, r: 1.6, label: "救急箱を使う" });
  // second leg
  L.block(17.2, -63.6, 17.55, -62.7, 0.9, "ac");
  L.block(18.95, -67.5, 19.6, -66.3, 1.2, "crate");
  L.block(17.2, -79.0, 17.75, -77.9, 1.0, "bin");
  L.block(18.95, -90.2, 19.6, -89.2, 1.5, "stone"); // wayside shrine
  L.block(17.2, -96.4, 17.6, -95.5, 0.9, "ac");
  L.rattles.push({ x: 17.2, y: 1.0, z: -86.5 });
  L.lamp("wall", 19.52, 2.8, -98.5, C_AMBER, 0.7, 8, "buzz", { face: "w", glow: 0.9 });
  // lane B clutter
  L.block(13.2, -81.95, 14.1, -81.2, 0.9, "crate");

  // ================================================================ junction
  L.rail(-5, -110.3, 5, -110.05, 1.1, "barricade");
  L.sign(-0.2, 1.55, -109.98, "s", 1.9, 1.0, ["通行止", "この先 橋りょう流失"], "warn");
  L.sign(3.6, 2.0, -109.98, "s", 1.7, 1.1, ["歩行者う回路", "水門管理橋", "警察署方面"], "evac", { arrow: "r", lit: true });
  L.lamp("flasher", -2.4, 1.28, -110.0, C_FLASH, 0.9, 9, "blink", { glow: 1.1 });
  L.lamp("flasher", 2.0, 1.28, -110.0, C_FLASH, 0.9, 9, "blinkAlt", { glow: 1.1 });
  L.props.push({ k: "bike", x: 3.3, z: -108.5, rot: 0.9, fallen: true });
  L.wall(5, -110.3, 10, -110, 2.7, "concrete");
  L.wall(13, -110.3, 30, -110, 2.7, "concrete");
  L.sign(8.9, 1.65, -109.97, "s", 1.5, 0.42, ["汐凪水門管理所"], "plate");
  L.sign(14.6, 1.65, -109.97, "s", 1.5, 0.5, ["関係者以外 立入禁止"], "warn");
  L.lamp("wall", 11.5, 3.3, -109.9, C_COLD, 1.2, 10, "steady", { face: "s" });
  L.wall(-5.3, -132.3, -5, -110, 2.7, "concrete"); // west side of the washed-out approach

  // ================================================================ sluice yard
  L.wall(4.7, -132.3, 5, -110.3, 2.7, "concrete"); // west
  L.building(30, -132.3, 44, -110, 9, 5); // east
  L.props.push({ k: "ground", x0: 5, z0: -127.5, x1: 30, z1: -110.3, y: 0.015, mat: "concrete" });
  L.props.push({ k: "ground", x0: 5, z0: -132, x1: 30, z1: -127.5, y: 0.03, mat: "grate" });
  L.wall(13, -125, 20, -117, 4.6, "winch"); // winch house
  L.wall(13.3, -112.7, 15.1, -110.9, 2.5, "booth"); // gate booth
  L.car(7.35, -118.85, 0, "utility", 0xe0b030);
  L.block(5.3, -128.5, 6.6, -123.5, 1.0, "pipe");
  L.block(16.3, -113.9, 18.3, -112.7, 1.2, "sandbag");
  L.block(24, -115.2, 26, -112.4, 2.2, "crate", true);
  L.block(26.8, -131.2, 29.8, -128.6, 2.6, "container", true);
  L.rail(5, -132.2, 23, -132, 1.1, "rail");
  L.rail(25.5, -132.2, 30, -132, 1.1, "rail");
  L.props.push({ k: "panel", x: 9, z: -131.0 });
  L.collider(8.6, -131.35, 9.4, -130.75, 0, 1.5, {});
  L.props.push({ k: "sluice", x: -16, z: -138 });
  L.sign(16.5, 2.2, -116.97, "s", 2.6, 1.0, ["歩道橋 昇降操作盤", "水門側 保守通路"], "notice", { arrow: "l" });
  L.sign(22.3, 1.9, -131.9, "s", 1.1, 0.6, ["水門管理橋", "定員５名"], "plate");
  L.lamp("bare", 12.55, 0.16, -112.45, C_WHITE, 0.55, 4.5, "steady", { glow: 0.5, streak: false });
  L.lamp("none", 9.0, 1.9, -131.26, C_GREEN, 0.16, 4, "blink", { glow: 0.5, streak: false });
  L.lamp("wall", 20.14, 2.9, -121, C_AMBER, 0.6, 7, "flicker", { face: "e", glow: 0.9 });
  L.lamp("none", -16, 14.3, -134.8, C_RED, 1.0, 0, "pulse", { glow: 2.2, streak: false });
  L.lamp("beacon", 22.4, 3.5, -131.6, C_FLASH, 1.7, 15, "beacon", { glow: 1.6, group: "bridgeWarn" });

  L.props.push({ k: "item", id: "ammo", kind: "ammo", x: 13.18, y: 1.02, z: -111.9 });
  L.interact({ id: "ammo", kind: "ammo", x: 13.05, z: -111.9, r: 1.5, label: "弾を拾う" });
  L.interact({ id: "panel", kind: "panel", x: 9, z: -130.45, r: 1.5, label: "操作盤を動かす" });

  // ================================================================ canal + bridge
  // the canal is a pit: walking is blocked, sight and bullets are not
  L.collider(-40, -146, 22.85, -132.2, -4, 0, { thin: true });
  L.collider(25.65, -146, 60, -132.2, -4, 0, { thin: true });
  L.props.push({ k: "water", x0: -40, z0: -146.4, x1: 60, z1: -131.8, y: -2.6, kind: "canal" });
  L.props.push({ k: "bridge", x0: 23, x1: 25.5, z0: -146, z1: -132 });
  // side rails ride on the deck (the view draws them with the bridge)
  L.collider(22.85, -146, 23, -132, 0, 1.1, { thin: true });
  L.collider(25.5, -146, 25.65, -132, 0, 1.1, { thin: true });
  // the raised deck stands across the entry until the bridge is down
  L.collider(23, -132.5, 25.5, -132, 0, 6, { opaque: true, id: "bridgeGate" });

  // ================================================================ forecourt
  L.props.push({ k: "ground", x0: 8, z0: -174, x1: 40.5, z1: -146, y: 0.015, mat: "paving" });
  L.rail(8, -146.2, 23, -146, 1.2, "chain");
  L.rail(25.5, -146.2, 40.5, -146, 1.2, "chain");
  L.wall(7.7, -174, 8, -146, 2.6, "concrete");
  L.wall(40.5, -174, 40.8, -146, 2.6, "concrete");
  L.collider(6, -188, 42.5, -174, 0, 12, { opaque: true });
  L.props.push({ k: "box", x0: 6, z0: -188, x1: 42.5, z1: -174, y0: 0, y1: 12, mat: "station" });
  L.props.push({ k: "canopy", x0: 19.25, z0: -174, x1: 29.25, z1: -168.8, y: 3.7 });
  L.collider(19.4, -169.6, 20.0, -169.0, 0, 3.7, {});
  L.collider(28.5, -169.6, 29.1, -169.0, 0, 3.7, {});
  L.props.push({ k: "monument", x0: 21, z0: -162, x1: 27.5, z1: -156 });
  L.collider(21, -162, 27.5, -156, 0, 1.9, { opaque: true });
  L.car(33.6, -157.0, 3, "van", 0x2a3f6a);
  L.car(12.3, -153.0, 1, "patrol", 0xe9e9e4);
  L.car(12.3, -158.0, 1, "patrol", 0xe9e9e4);
  L.car(12.3, -163.0, 1, "patrol", 0xe9e9e4);
  L.rail(18.8, -150.2, 22, -150, 1.0, "barricade");
  L.rail(26.5, -150.2, 29.7, -150, 1.0, "barricade");
  L.block(15.5, -168, 21.2, -167.2, 1.1, "sandbag");
  L.block(27.3, -168, 33, -167.2, 1.1, "sandbag");
  L.props.push({ k: "pole", x: 22.4, z: -159, h: 7.5, kind: "flag" });
  L.props.push({ k: "pole", x: 24.25, z: -159, h: 8.2, kind: "flag" });
  L.props.push({ k: "pole", x: 26.1, z: -159, h: 7.5, kind: "flag" });
  L.sign(24.25, 4.35, -168.72, "s", 6.2, 0.9, ["汐凪警察署"], "station");
  L.sign(24.25, 2.72, -173.95, "s", 1.9, 0.5, ["避難所 入口"], "exit", { lit: true });
  L.lamp("none", 24.25, 2.95, -173.6, C_GUIDE, 3.0, 24, "steady", { glow: 2.6, group: "guide" });
  L.lamp("ceiling", 24.25, 3.62, -171.4, C_WHITE, 1.4, 9, "buzz", { glow: 1.0, group: "guide" });
  L.props.push({ k: "door", id: "exit", hx: 22.75, hz: -173.98, ax: 1, az: 0, len: 1.5, h: 2.4, swing: 1, style: "glass" });
  L.props.push({ k: "door", id: "exit2", hx: 25.75, hz: -173.98, ax: -1, az: 0, len: 1.5, h: 2.4, swing: -1, style: "glass" });
  L.interact({ id: "exit", kind: "exit", x: 24.25, z: -173.55, r: 1.7, label: "扉を開ける" });

  // ================================================================ backdrop
  L.props.push({ k: "water", x0: -60, z0: 0.6, x1: 80, z1: 60, y: -1.2, kind: "sea" });
  L.props.push({ k: "washout", x0: -5, z0: -132, x1: 4.7, z1: -110.4 }); // the road bridge that is gone

  // ================================================================ enemies
  // plaza: the figure behind the glass, a loiterer and the arch patrol
  // P1 hauls itself along the glass front (its shadow falls on the fogged panes)
  L.enemy("P1", 6.8, -15.25, W, {
    patrol: [
      [-12.3, -15.25],
      [-12.5, -18.4],
      [6.0, -18.4],
      [6.8, -15.25],
    ],
    dormant: true,
    look: 0,
  });
  L.enemy("P2", -3.5, -21.3, S, { look: 1 });
  L.enemy("E1", 9, -22.75, W, {
    patrol: [
      [9, -22.75],
      [-8.5, -22.4],
    ],
    pingPong: true,
    look: 2,
  });
  // main street
  L.enemy("E2", -2.6, -39.5, N, {
    patrol: [
      [-2.6, -39.5],
      [-3.2, -37.2],
      [0.5, -41.5],
    ],
    look: 3,
  });
  L.enemy("E3", 2.6, -55.5, W, {
    patrol: [
      [-3.2, -55.0],
      [3.6, -56.0],
    ],
    pingPong: true,
    look: 4,
  });
  L.enemy("E4", -3.2, -66.5, N, { look: 5 });
  L.enemy("E5", 0.8, -70, N, {
    patrol: [
      [0.8, -70],
      [1.0, -84],
    ],
    pingPong: true,
    look: 0,
  });
  L.enemy("E6", 0, -97, W, {
    patrol: [
      [-3.5, -97.5],
      [3.5, -96.5],
    ],
    pingPong: true,
    look: 1,
  });
  L.enemy("E7", -1.5, -107.4, N, { look: 2 });
  // back alley sleeper
  L.enemy("S1", 21.3, -72.5, E, { look: 3 });
  // sluice yard
  L.enemy("Y1", 27.6, -113.6, E, { look: 4 });
  L.enemy("Y2", 6.9, -113.4, W, { look: 5 });
  // forecourt (wake on the final trigger)
  L.enemy("F1", 33.6, -153.4, W, { dormant: true, look: 2 });
  L.enemy("F2", 16.4, -160.6, E, { dormant: true, look: 0 });
  L.enemy("F3", 13.5, -170.5, E, { dormant: true, look: 4 });

  // ================================================================ zones
  const zones: ZoneDef[] = [
    { name: "terminal", x0: -14, z0: -14, x1: 14.07, z1: 0, indoor: true },
    { name: "lane", x0: 14.07, z0: -24, x1: 18.3, z1: 0.6, indoor: false },
    { name: "plaza", x0: -14, z0: -24, x1: 14.07, z1: -14, indoor: false },
    { name: "street", x0: -5, z0: -104, x1: 5, z1: -24, indoor: false },
    { name: "alley", x0: 5, z0: -104, x1: 22.3, z1: -24, indoor: false },
    { name: "junction", x0: -5, z0: -110.3, x1: 19.65, z1: -104, indoor: false },
    { name: "yard", x0: 5, z0: -132.2, x1: 30, z1: -110.3, indoor: false },
    { name: "bridge", x0: 22.85, z0: -146, x1: 25.65, z1: -132.2, indoor: false },
    { name: "forecourt", x0: 8, z0: -174, x1: 40.5, z1: -146, indoor: false },
  ];
  const surfaces: SurfaceZone[] = [
    { surface: "tile", x0: -14, z0: -14, x1: 14.07, z1: 0 },
    { surface: "metal", x0: 5, z0: -132.2, x1: 30, z1: -127.5 },
    { surface: "metal", x0: 22.85, z0: -146, x1: 25.65, z1: -132.2 },
    { surface: "water", x0: -5, z0: -100, x1: 5, z1: -27 },
    { surface: "water", x0: 5, z0: -36, x1: 13.6, z1: -33 },
    { surface: "water", x0: 5, z0: -84, x1: 16.6, z1: -81 },
    { surface: "concrete", x0: 5, z0: -127.5, x1: 30, z1: -110.3 },
    { surface: "concrete", x0: 8, z0: -174, x1: 40.5, z1: -146 },
  ];
  const checkpoints: Checkpoint[] = [
    { id: "start", area: { x0: 0, z0: 0, x1: 0, z1: 0 }, x: -8.5, z: -2.2, yaw: START_YAW },
    { id: "lane", area: { x0: 14.3, z0: -13.4, x1: 18, z1: -10.6 }, x: 16.3, z: -12, yaw: N },
    { id: "junction", area: { x0: -5, z0: -110, x1: 19.65, z1: -104.4 }, x: 17.6, z: -106.9, yaw: W },
    { id: "forecourt", area: { x0: 23, z0: -149.6, x1: 25.5, z1: -146.2 }, x: 24.25, z: -147.6, yaw: N },
  ];

  return {
    boxes: L.boxes,
    dyn: L.dyn,
    props: L.props,
    lights: L.lights,
    zones,
    surfaces,
    interactables: L.interactables,
    enemies: L.enemies,
    checkpoints,
    start: { x: -8.5, z: -2.2, yaw: START_YAW },
    bounds: { x0: -28, z0: -190, x1: 46, z1: 3 },
    winch: { x: 20.7, z: -121 },
    rattles: L.rattles,
  };
}
