// The quarter-view map: floor and wall blocks, everything standing on them, the
// camera, and the small animations (slides, hit flashes, floating numbers).
// Purely presentational — nothing here touches engine state.

import { knownTiles, visibleNow } from "../../engine/turn";
import { DIRS, idx, tileAt, type Action, type DungeonState, type Event, type Vec } from "../../engine/types";
import { classSprite, drawSprite, EMOJI, enemySprite, type ArtBank } from "./art";
import { ANIM_MS, Camera, FLOOR_H, isoX, isoY, S, TH, TW, WALL_H } from "./iso";
import { MAP_H, MAP_W, MAP_X, MAP_Y, UI_FONT } from "./layout";
import { clamp } from "./text";
import { block, emojiBillboard, flat, inset, tileColor } from "./tiles";

const FLOAT_MS = 700;
const FLASH_MS = 150;
/** Blocks south/east of the player are painted after them and can cover them. */
const OCCLUDERS: [number, number][] = [
  [1, 0],
  [0, 1],
  [1, 1],
];

type Float = { pos: Vec; text: string; color: string; until: number };
type ActorArt = {
  id: string;
  alpha: number;
  flash: boolean;
  ring: string | null;
  hp: number;
  hpColor: string;
  mark: string;
  markColor: string;
  scale: number;
  faceRight: boolean;
};

export class SceneRenderer {
  readonly cam = new Camera();
  private animFrom = new Map<string, Vec>();
  private animStart = Number.NEGATIVE_INFINITY;
  private flash = new Map<number, number>(); // enemyId -> until
  private playerFlashUntil = 0;
  private floats: Float[] = [];
  private faceRight = new Map<string, boolean>();

  /** New run or new floor: nothing to slide from, camera snaps. */
  reset(): void {
    this.cam.reset();
    this.animFrom.clear();
    this.flash.clear();
    this.playerFlashUntil = 0;
    this.floats = [];
    this.faceRight.clear();
  }

  /** Record what one engine step changed so the next frames can animate it. */
  onStep(before: DungeonState, state: DungeonState, events: Event[], t: number, action?: Action): void {
    this.floats = this.floats.filter((f) => f.until > t);
    // remember where everyone stood so this frame can slide out of it
    this.animFrom = new Map<string, Vec>([["p", { ...before.player.pos }]]);
    for (const e of before.enemies) this.animFrom.set(`e${e.id}`, { ...e.pos });
    for (const a of before.allies) this.animFrom.set(`a${a.id}`, { ...a.pos });
    this.animStart = t;
    // the player turns toward whatever they did, even when they did not move (attacks, bolts)
    if (action && "dir" in action && action.dir !== undefined) {
      const d = DIRS[action.dir]!;
      this.face("p", { x: 0, y: 0 }, d);
    } else this.face("p", before.player.pos, state.player.pos);
    for (const e of state.enemies) {
      const b = before.enemies.find((x) => x.id === e.id);
      if (b) this.face(`e${e.id}`, b.pos, e.pos);
    }
    for (const a of state.allies) {
      const b = before.allies.find((x) => x.id === a.id);
      if (b) this.face(`a${a.id}`, b.pos, a.pos);
    }
    if (state.floorNo !== before.floorNo) {
      this.animFrom.clear();
      this.cam.reset();
    }
    const posOf = (id: number): Vec | undefined =>
      before.enemies.find((x) => x.id === id)?.pos ?? state.enemies.find((x) => x.id === id)?.pos ?? before.allies.find((x) => x.id === id)?.pos;
    const float = (pos: Vec, text: string, color: string): void => {
      this.floats.push({ pos: { ...pos }, text, color, until: t + FLOAT_MS });
    };
    for (const e of events) {
      if (e.t === "attack") {
        if (e.target === "player") {
          this.playerFlashUntil = t + FLASH_MS;
          float(before.player.pos, `-${e.dmg}`, "#ff8080");
        } else {
          this.flash.set(e.target, t + FLASH_MS);
          const p = posOf(e.target);
          if (p) float(p, `-${e.dmg}${e.crit ? "!" : ""}`, e.crit ? "#ffd85a" : "#fff");
        }
      } else if (e.t === "allyHit") {
        const p = posOf(e.target);
        if (p) float(p, `-${e.dmg}`, "#8cf");
      } else if (e.t === "pickupWin") float(state.player.pos, `+${e.amount}`, "#fd4");
      else if (e.t === "grow") float(state.player.pos, "LEVEL UP", "#8f8");
      else if (e.t === "acid") float(state.player.pos, "-1", "#af6");
      else if (e.t === "doubleUp") float(state.player.pos, `×${e.multiplier}`, "#fa4");
    }
  }

  /** Sprites are drawn facing screen-left; remember who turned right. */
  private face(key: string, from: Vec, to: Vec): void {
    const dx = isoX(to.x, to.y) - isoX(from.x, from.y);
    if (dx !== 0) this.faceRight.set(key, dx > 0);
  }

  /** True while something on screen is still moving; the host loop idles otherwise. */
  busy(t: number, s: DungeonState): boolean {
    if (t - this.animStart < ANIM_MS + 32) return true;
    if (this.floats.length > 0 || this.playerFlashUntil > t) return true;
    for (const until of this.flash.values()) if (until > t) return true;
    const p = s.player.pos;
    return !this.cam.settled(isoX(p.x, p.y), isoY(p.x, p.y));
  }

  draw(c: CanvasRenderingContext2D, bank: ArtBank, s: DungeonState, t: number): void {
    const { map, player } = s;
    const vis = visibleNow(s);
    const known = knownTiles(s);
    const k = clamp((t - this.animStart) / ANIM_MS, 0, 1);
    const ease = k * (2 - k);
    const slide = (key: string, pos: Vec): Vec => {
      const from = this.animFrom.get(key);
      if (!from || k >= 1) return pos;
      return { x: from.x + (pos.x - from.x) * ease, y: from.y + (pos.y - from.y) * ease };
    };

    const pdraw = slide("p", player.pos);
    this.cam.follow(isoX(pdraw.x, pdraw.y), isoY(pdraw.x, pdraw.y));
    const ox = MAP_X + MAP_W / 2 - this.cam.x;
    const oy = MAP_Y + MAP_H / 2 - this.cam.y;
    const px = (x: number, y: number) => ox + isoX(x, y);
    const py = (x: number, y: number) => oy + isoY(x, y);

    c.save();
    c.beginPath();
    c.rect(MAP_X, MAP_Y, MAP_W, MAP_H);
    c.clip();
    c.fillStyle = "#05060c";
    c.fillRect(MAP_X, MAP_Y, MAP_W, MAP_H);

    // Everything that stands on a tile is queued per cell, so the wall in front
    // of a monster is painted after it and actually hides it.
    const standing = new Map<number, (() => void)[]>();
    const at = (pos: Vec, fn: () => void): void => {
      const i = idx(map, pos);
      const list = standing.get(i);
      if (list) list.push(fn);
      else standing.set(i, [fn]);
    };

    for (const it of s.items) {
      const i = idx(map, it.pos);
      if (!vis[i] && !(player.mapped && known[i])) continue;
      const id = it.type === "card" ? "item.card" : it.type === "doubleUp" ? "item.doubleUp" : "item.win";
      at(it.pos, () => this.drawItem(c, bank, px(it.pos.x, it.pos.y), py(it.pos.x, it.pos.y), id, t));
    }
    for (const e of s.enemies) {
      const seen = !!vis[idx(map, e.pos)];
      if (!seen && !player.searched) continue;
      const key = `e${e.id}`;
      const p = slide(key, e.pos);
      const flash = (this.flash.get(e.id) ?? 0) > t;
      const mark = e.sleep > 0 || !e.awake ? "z" : e.confused > 0 ? "?" : "";
      at(e.pos, () =>
        this.drawActor(c, bank, px(p.x, p.y), py(p.x, p.y), {
          id: enemySprite(e.kind),
          alpha: seen ? 1 : 0.4,
          flash,
          ring: e.boss ? "#ffcc33" : null,
          hp: e.hp / e.maxHp,
          hpColor: "#f66",
          mark,
          markColor: e.confused > 0 ? "#fd8" : "#bcf",
          scale: e.boss ? 1.5 : 1,
          faceRight: this.faceRight.get(key) ?? false,
        }),
      );
    }
    for (const a of s.allies) {
      if (!vis[idx(map, a.pos)]) continue;
      const key = `a${a.id}`;
      const p = slide(key, a.pos);
      at(a.pos, () =>
        this.drawActor(c, bank, px(p.x, p.y), py(p.x, p.y), {
          id: enemySprite(a.kind),
          alpha: 1,
          flash: false,
          ring: "#4cf",
          hp: a.hp / a.maxHp,
          hpColor: "#6cf",
          mark: "",
          markColor: "#fff",
          scale: 1,
          faceRight: this.faceRight.get(key) ?? false,
        }),
      );
    }
    const playerArt: ActorArt = {
      id: classSprite(player.cls),
      alpha: 1,
      flash: this.playerFlashUntil > t,
      ring: "#8f8",
      hp: player.hp / player.maxHp,
      hpColor: "#6f6",
      mark: "",
      markColor: "#fff",
      scale: 1.1,
      faceRight: this.faceRight.get("p") ?? false,
    };
    at(player.pos, () => this.drawActor(c, bank, px(pdraw.x, pdraw.y), py(pdraw.x, pdraw.y), playerArt));

    // row-major order is already back-to-front for this projection
    for (let my = 0; my < map.height; my++) {
      for (let mx = 0; mx < map.width; mx++) {
        const i = my * map.width + mx;
        const X = px(mx, my);
        const Y = py(mx, my);
        if (X < MAP_X - TW || X > MAP_X + MAP_W + TW) continue;
        if (Y < MAP_Y - (WALL_H + TH * 2) || Y > MAP_Y + MAP_H + TH * 2) continue;
        const list = standing.get(i);
        const tile = map.tiles[i]!;
        let seen = !!vis[i];
        if (!known[i]) {
          // The FOV never marks a room's surrounding wall, so imply any wall that
          // touches something we know: without it rooms read as floating slabs.
          let lit = 0;
          if (tile.kind === "wall") {
            for (let ny = my - 1; ny <= my + 1; ny++) {
              for (let nx = mx - 1; nx <= mx + 1; nx++) {
                if (nx < 0 || ny < 0 || nx >= map.width || ny >= map.height) continue;
                const j = ny * map.width + nx;
                if (!known[j] || map.tiles[j]!.kind === "wall") continue;
                lit = Math.max(lit, vis[j] ? 2 : 1);
              }
            }
          }
          if (lit === 0) {
            if (list) for (const fn of list) fn();
            continue;
          }
          seen = lit === 2;
        }
        const dim = { dim: !seen };
        const grain = (mx * 7 + my * 13) % 12;
        if (tile.kind === "wall") {
          if (!drawSprite(c, bank, "tile.wall", X, Y, dim)) block(c, X, Y, FLOOR_H + WALL_H, seen ? "#5a5a6c" : "#2c2c36");
        } else {
          const ground = tile.kind === "ice" ? "tile.ice" : grain === 0 ? "tile.floor.b" : "tile.floor";
          const drewGround = drawSprite(c, bank, ground, X, Y, dim) || drawSprite(c, bank, "tile.floor", X, Y, dim);
          if (!drewGround) block(c, X, Y, FLOOR_H, tileColor(tile.kind, tile.lit, seen), 1 + ((grain % 3) - 1) * 0.04, 0.72);
          const top = Y - FLOOR_H;
          if (tile.kind === "stairsDown") {
            if (!drawSprite(c, bank, "tile.stairs", X, Y, dim)) {
              inset(c, X, top, "#101828");
              flat(c, X, top, "▼", 15 * S, seen ? "#ffd85a" : "#8a7a45");
            }
          } else if (tile.kind === "door") {
            // an archway across the passage: walls to the east and west mean it runs north-south
            const ew = mx > 0 && mx + 1 < map.width && map.tiles[i - 1]!.kind === "wall" && map.tiles[i + 1]!.kind === "wall";
            if (!drawSprite(c, bank, ew ? "tile.door.ew" : "tile.door.ns", X, Y, dim)) inset(c, X, top, seen ? "#a7743a" : "#553c22");
          } else if (tile.kind === "ice") {
            if (!drewGround) flat(c, X, top - 1, "❄", 12 * S, seen ? "#eaffff" : "#6d8f9c");
          } else if (tile.kind === "altar") {
            inset(c, X, top, "#2a2038");
            this.drawProp(c, bank, X, top, "tile.altar", 22 * S, t);
          } else if (tile.kind === "shop") {
            this.drawProp(c, bank, X, top, "tile.shop", 24 * S, t);
          } else if (tile.kind === "casino") {
            this.drawProp(c, bank, X, top, "tile.casino", 24 * S, t);
          }
        }
        if (list) for (const fn of list) fn();
      }
    }

    // x-ray: the blocks south/east of the player are painted after them, so put
    // a ghost back on top rather than punching holes in the walls
    const covered = OCCLUDERS.some(([dx, dy]) => {
      const v = { x: player.pos.x + dx, y: player.pos.y + dy };
      return v.x < map.width && v.y < map.height && tileAt(map, v).kind === "wall";
    });
    if (covered) {
      c.globalAlpha = 0.5;
      this.drawActor(c, bank, px(pdraw.x, pdraw.y), py(pdraw.x, pdraw.y), playerArt);
      c.globalAlpha = 1;
    }

    for (const f of this.floats) {
      const life = (f.until - t) / FLOAT_MS;
      if (life <= 0) continue;
      const X = px(f.pos.x, f.pos.y);
      const Y = py(f.pos.x, f.pos.y) - FLOOR_H - 34 * S - Math.round((1 - life) * 16 * S);
      c.save();
      c.globalAlpha = Math.min(1, life * 2);
      c.textAlign = "center";
      c.textBaseline = "alphabetic";
      c.font = `bold ${Math.round(14 * S)}px ${UI_FONT}`;
      c.fillStyle = "#000";
      c.fillText(f.text, X + 1, Y + 1);
      c.fillStyle = f.color;
      c.fillText(f.text, X, Y);
      c.restore();
    }

    c.restore();
  }

  /** Scenery standing upright on a tile, with its own shadow. */
  private drawProp(c: CanvasRenderingContext2D, bank: ArtBank, X: number, topY: number, id: string, size: number, t: number): void {
    c.save();
    c.fillStyle = "rgba(0,0,0,0.4)";
    c.beginPath();
    c.ellipse(X, topY + 3, 12 * S, 6 * S, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
    const y = topY + 4 + Math.sin(t / 420) * 1.2;
    if (!drawSprite(c, bank, id, X, y)) emojiBillboard(c, EMOJI[id] ?? "?", X, y, size, false);
  }

  /** Item bobbing above the floor. */
  private drawItem(c: CanvasRenderingContext2D, bank: ArtBank, X: number, Y: number, id: string, t: number): void {
    const base = Y - FLOOR_H;
    c.save();
    c.fillStyle = "rgba(0,0,0,0.4)";
    c.beginPath();
    c.ellipse(X, base + 1, 11 * S, 5.5 * S, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
    const y = base - 3 + Math.sin(t / 260) * 2.5;
    if (!drawSprite(c, bank, id, X, y)) emojiBillboard(c, EMOJI[id] ?? "?", X, y, 22 * S, false);
  }

  /** Player / monster / summon: shadow, footprint ring, billboard, hp bar. */
  private drawActor(c: CanvasRenderingContext2D, bank: ArtBank, X: number, Y: number, o: ActorArt): void {
    const base = Y - FLOOR_H;
    const sc = o.scale * S;
    c.save();
    c.globalAlpha *= o.alpha;
    c.fillStyle = "rgba(0,0,0,0.45)";
    c.beginPath();
    c.ellipse(X, base + 2, 13 * sc, 6.5 * sc, 0, 0, Math.PI * 2);
    c.fill();
    if (o.ring) {
      c.strokeStyle = o.ring;
      c.lineWidth = 2;
      c.beginPath();
      c.ellipse(X, base + 2, 14 * sc, 7 * sc, 0, 0, Math.PI * 2);
      c.stroke();
    }
    if (o.flash) {
      c.fillStyle = "rgba(255,255,255,0.5)";
      c.beginPath();
      c.ellipse(X, base - 10 * sc, 12 * sc, 13 * sc, 0, 0, Math.PI * 2);
      c.fill();
    }
    // sprites are authored for the current tile size, so only the boss scale applies to them
    if (!drawSprite(c, bank, o.id, X, base + 3, { scale: o.scale, flip: o.faceRight })) emojiBillboard(c, EMOJI[o.id] ?? "?", X, base + 3, 26 * sc);
    if (o.hp < 1) {
      const w = 24 * sc;
      const by = base - 26 * sc;
      c.fillStyle = "#200";
      c.fillRect(X - w / 2, by, w, 3);
      c.fillStyle = o.hpColor;
      c.fillRect(X - w / 2, by, Math.round(w * clamp(o.hp, 0, 1)), 3);
    }
    if (o.mark) {
      c.font = `${Math.round(12 * S)}px ${UI_FONT}`;
      c.textAlign = "center";
      c.textBaseline = "alphabetic";
      c.fillStyle = o.markColor;
      c.fillText(o.mark, X + 13 * sc, base - 24 * sc);
    }
    c.restore();
  }
}
