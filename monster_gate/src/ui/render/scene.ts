// The top-down map: floor and wall tiles on a square grid, everything standing
// on them, the camera, and the small animations (steps, hit flashes, attack
// lunges, floating numbers). Purely presentational — nothing here touches
// engine state.

import { knownTiles, visibleNow } from "../../engine/turn";
import { DIRS, idx, type Action, type Dir, type DungeonState, type Event, type Vec } from "../../engine/types";
import { classSprite, drawSprite, EMOJI, enemySprite, type ArtBank } from "./art";
import { ANIM_MS, Camera, FOOT, gx, gy, S, TS } from "./grid";
import { MAP_H, MAP_W, MAP_X, MAP_Y, UI_FONT } from "./layout";
import { clamp } from "./text";
import { emojiBillboard, flat, inset, square, tileColor, wallBlock } from "./tiles";
import { drawWeather } from "./weather";

const FLOAT_MS = 700;
const FLASH_MS = 150;
const ATTACK_MS = 220;

/** Eight engine directions collapse onto three drawings; sides are mirrored. */
type Facing = "f" | "b" | "s";
const FACING: Facing[] = ["b", "s", "s", "s", "f", "s", "s", "s"];
const FACE_RIGHT = [false, true, true, true, false, false, false, false];

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
  dir: Dir;
  /** 0 standing, 1 mid-step, 2 swinging */
  pose: 0 | 1 | 2;
};

export class SceneRenderer {
  readonly cam = new Camera();
  private animFrom = new Map<string, Vec>();
  private animStart = Number.NEGATIVE_INFINITY;
  private flash = new Map<number, number>(); // enemyId -> until
  private playerFlashUntil = 0;
  private floats: Float[] = [];
  private dir = new Map<string, Dir>();
  private attackUntil = 0;
  private attackDir: Dir = 4;
  private theme = "";

  /** New run or new floor: nothing to slide from, camera snaps.
   * `theme` is the castle id; tiles fall back to the unprefixed set when a
   * castle has no art of its own. */
  reset(theme = ""): void {
    this.theme = theme;
    this.cam.reset();
    this.animFrom.clear();
    this.flash.clear();
    this.playerFlashUntil = 0;
    this.attackUntil = 0;
    this.floats = [];
    this.dir.clear();
  }

  /** Record what one engine step changed so the next frames can animate it. */
  onStep(before: DungeonState, state: DungeonState, events: Event[], t: number, action?: Action): void {
    this.floats = this.floats.filter((f) => f.until > t);
    // remember where everyone stood so this frame can slide out of it
    this.animFrom = new Map<string, Vec>([["p", { ...before.player.pos }]]);
    for (const e of before.enemies) this.animFrom.set(`e${e.id}`, { ...e.pos });
    for (const a of before.allies) this.animFrom.set(`a${a.id}`, { ...a.pos });
    this.animStart = t;
    // the player turns toward whatever they did, even when they did not move
    if (action && "dir" in action && action.dir !== undefined) this.dir.set("p", action.dir);
    else this.face("p", before.player.pos, state.player.pos);
    for (const e of state.enemies) {
      const b = before.enemies.find((x) => x.id === e.id);
      if (b) this.face(`e${e.id}`, b.pos, e.pos);
    }
    for (const a of state.allies) {
      const b = before.allies.find((x) => x.id === a.id);
      if (b) this.face(`a${a.id}`, b.pos, a.pos);
    }
    // a swing the player made: an explicit attack, or a move that landed a hit
    const struck = events.some((e) => e.t === "attack" && e.by === "player" && !e.ranged);
    if (action && "dir" in action && action.dir !== undefined && (action.type === "attack" || struck)) {
      this.attackUntil = t + ATTACK_MS;
      this.attackDir = action.dir;
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
      } else if (e.t === "miss") float(state.player.pos, "空振り", "#889");
      else if (e.t === "pickupWin") float(state.player.pos, `+${e.amount}`, "#fd4");
      else if (e.t === "grow") float(state.player.pos, "LEVEL UP", "#8f8");
      else if (e.t === "acid") float(state.player.pos, "-1", "#af6");
      else if (e.t === "doubleUp") float(state.player.pos, `×${e.multiplier}`, "#fa4");
    }
  }

  /** Which way the player is looking, for the attack button. */
  get playerDir(): Dir {
    return this.dir.get("p") ?? 4;
  }

  private face(key: string, from: Vec, to: Vec): void {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    if (dx === 0 && dy === 0) return;
    const found = DIRS.findIndex((d) => Math.sign(d.x) === Math.sign(dx) && Math.sign(d.y) === Math.sign(dy));
    if (found >= 0) this.dir.set(key, found as Dir);
  }

  /** True while something on screen is still moving; the host loop idles otherwise. */
  busy(t: number, s: DungeonState): boolean {
    if (t - this.animStart < ANIM_MS + 32) return true;
    if (this.floats.length > 0 || this.playerFlashUntil > t || this.attackUntil > t) return true;
    for (const until of this.flash.values()) if (until > t) return true;
    const p = s.player.pos;
    return !this.cam.settled(gx(p.x), gy(p.y));
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
    this.cam.follow(gx(pdraw.x), gy(pdraw.y));
    const ox = MAP_X + MAP_W / 2 - this.cam.x;
    const oy = MAP_Y + MAP_H / 2 - this.cam.y;
    const px = (x: number) => ox + gx(x);
    const py = (y: number) => oy + gy(y);

    c.save();
    c.beginPath();
    c.rect(MAP_X, MAP_Y, MAP_W, MAP_H);
    c.clip();
    c.fillStyle = "#05060c";
    c.fillRect(MAP_X, MAP_Y, MAP_W, MAP_H);

    // ---- ground. Straight down, so plain iteration order is fine.
    const x0 = Math.max(0, Math.floor((MAP_X - ox) / TS) - 1);
    const x1 = Math.min(map.width - 1, Math.ceil((MAP_X + MAP_W - ox) / TS));
    const y0 = Math.max(0, Math.floor((MAP_Y - oy) / TS) - 1);
    const y1 = Math.min(map.height - 1, Math.ceil((MAP_Y + MAP_H - oy) / TS));
    for (let my = y0; my <= y1; my++) {
      for (let mx = x0; mx <= x1; mx++) {
        const i = my * map.width + mx;
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
          if (lit === 0) continue;
          seen = lit === 2;
        }
        const X = px(mx) + TS / 2;
        const Y = py(my) + TS / 2;
        const dim = { dim: !seen };
        const grain = (mx * 7 + my * 13) % 12;
        if (tile.kind === "wall") {
          if (!this.tile(c, bank, "tile.wall", X, Y, dim)) wallBlock(c, X, Y, seen ? "#5a5a6c" : "#2c2c36");
          continue;
        }
        const ground = tile.kind === "ice" ? "tile.ice" : grain === 0 ? "tile.floor.b" : "tile.floor";
        const drew = this.tile(c, bank, ground, X, Y, dim) || this.tile(c, bank, "tile.floor", X, Y, dim);
        if (!drew) square(c, X, Y, tileColor(tile.kind, tile.lit, seen), 1 + ((grain % 3) - 1) * 0.04);
        if (tile.kind === "stairsDown") {
          if (!this.tile(c, bank, "tile.stairs", X, Y, dim)) {
            inset(c, X, Y, "#101828");
            flat(c, X, Y, "▼", 22 * S, seen ? "#ffd85a" : "#8a7a45");
          }
        } else if (tile.kind === "door") {
          // an archway across the passage: walls east and west mean it runs north-south
          const ew = mx > 0 && mx + 1 < map.width && map.tiles[i - 1]!.kind === "wall" && map.tiles[i + 1]!.kind === "wall";
          if (!this.tile(c, bank, ew ? "tile.door.ew" : "tile.door.ns", X, Y, dim)) inset(c, X, Y, seen ? "#a7743a" : "#553c22");
        } else if (tile.kind === "ice") {
          if (!drew) flat(c, X, Y, "❄", 18 * S, seen ? "#eaffff" : "#6d8f9c");
        } else if (tile.kind === "altar") {
          this.drawProp(c, bank, X, Y, "tile.altar", 30 * S, t);
        } else if (tile.kind === "shop") {
          this.drawProp(c, bank, X, Y, "tile.shop", 32 * S, t);
        } else if (tile.kind === "casino") {
          this.drawProp(c, bank, X, Y, "tile.casino", 32 * S, t);
        }
      }
    }

    // ---- items, then everyone, sorted so a lower actor overlaps a higher one
    for (const it of s.items) {
      const i = idx(map, it.pos);
      if (!vis[i] && !(player.mapped && known[i])) continue;
      const id = it.type === "card" ? "item.card" : it.type === "doubleUp" ? "item.doubleUp" : "item.win";
      this.drawItem(c, bank, px(it.pos.x) + TS / 2, py(it.pos.y) + TS / 2, id, t);
    }

    const cast: { y: number; run: () => void }[] = [];
    const stepPose = (key: string): 0 | 1 => (this.animFrom.has(key) && k > 0.12 && k < 0.88 ? 1 : 0);
    for (const e of s.enemies) {
      const seen = !!vis[idx(map, e.pos)];
      if (!seen && !player.searched) continue;
      const key = `e${e.id}`;
      const p = slide(key, e.pos);
      const flash = (this.flash.get(e.id) ?? 0) > t;
      const mark = e.sleep > 0 || !e.awake ? "z" : e.confused > 0 ? "?" : "";
      const X = px(p.x) + TS / 2;
      const Y = py(p.y) + TS / 2;
      cast.push({
        y: Y,
        run: () =>
          this.drawActor(c, bank, X, Y, {
            id: enemySprite(e.kind),
            alpha: seen ? 1 : 0.4,
            flash,
            ring: e.boss ? "#ffcc33" : null,
            hp: e.hp / e.maxHp,
            hpColor: "#f66",
            mark,
            markColor: e.confused > 0 ? "#fd8" : "#bcf",
            scale: e.boss ? 1.5 : 1,
            dir: this.dir.get(key) ?? 4,
            pose: stepPose(key),
          }),
      });
    }
    for (const a of s.allies) {
      if (!vis[idx(map, a.pos)]) continue;
      const key = `a${a.id}`;
      const p = slide(key, a.pos);
      const X = px(p.x) + TS / 2;
      const Y = py(p.y) + TS / 2;
      cast.push({
        y: Y,
        run: () =>
          this.drawActor(c, bank, X, Y, {
            id: enemySprite(a.kind),
            alpha: 1,
            flash: false,
            ring: "#4cf",
            hp: a.hp / a.maxHp,
            hpColor: "#6cf",
            mark: "",
            markColor: "#fff",
            scale: 1,
            dir: this.dir.get(key) ?? 4,
            pose: stepPose(key),
          }),
      });
    }
    // the swing: lean into the blow, then settle back
    const swinging = this.attackUntil > t;
    // clamped: a long stall between frames must not send the swing past its ends
    const swing = clamp(1 - (this.attackUntil - t) / ATTACK_MS, 0, 1);
    let lx = 0;
    let ly = 0;
    if (swinging) {
      const a = swing;
      const reach = Math.sin(Math.PI * Math.min(1, a * 1.35)) * TS * 0.34;
      const d = DIRS[this.attackDir]!;
      lx = d.x * reach;
      ly = d.y * reach;
    }
    const pX = px(pdraw.x) + TS / 2 + lx;
    const pY = py(pdraw.y) + TS / 2 + ly;
    cast.push({
      y: pY,
      run: () => {
        if (swinging) this.drawSlash(c, pX, pY, this.attackDir, swing);
        this.drawActor(c, bank, pX, pY, {
          id: classSprite(player.cls),
          alpha: 1,
          flash: this.playerFlashUntil > t,
          ring: "#8f8",
          hp: player.hp / player.maxHp,
          hpColor: "#6f6",
          mark: "",
          markColor: "#fff",
          scale: 1.08,
          dir: swinging ? this.attackDir : this.playerDir,
          pose: swinging ? 2 : stepPose("p"),
        });
      },
    });
    cast.sort((a, b) => a.y - b.y);
    for (const entry of cast) entry.run();

    for (const f of this.floats) {
      const life = (f.until - t) / FLOAT_MS;
      if (life <= 0) continue;
      const X = px(f.pos.x) + TS / 2;
      const Y = py(f.pos.y) + TS / 2 - 26 - Math.round((1 - life) * 16);
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
    drawWeather(c, this.theme, t);
  }

  /** Castle-specific tile first, then the shared set. */
  private tile(c: CanvasRenderingContext2D, bank: ArtBank, id: string, X: number, Y: number, dim: { dim: boolean }): boolean {
    return (this.theme !== "" && drawSprite(c, bank, `${this.theme}.${id}`, X, Y, dim)) || drawSprite(c, bank, id, X, Y, dim);
  }

  /** A crescent thrown out in the direction of the blow. */
  private drawSlash(c: CanvasRenderingContext2D, X: number, Y: number, dir: Dir, a: number): void {
    const d = DIRS[dir]!;
    const ang = Math.atan2(d.y, d.x);
    c.save();
    c.translate(X + d.x * TS * 0.34, Y + d.y * TS * 0.34 - FOOT * 0.5);
    c.rotate(ang);
    c.globalAlpha = Math.sin(Math.PI * a) * 0.9;
    c.strokeStyle = "#fff";
    c.lineWidth = 4;
    c.lineCap = "round";
    c.beginPath();
    c.arc(0, 0, TS * (0.26 + a * 0.2), -1.1 + a * 0.9, 1.1 + a * 0.9);
    c.stroke();
    c.restore();
  }

  /** Scenery sitting on a tile, with its own shadow. */
  private drawProp(c: CanvasRenderingContext2D, bank: ArtBank, X: number, Y: number, id: string, size: number, t: number): void {
    c.save();
    c.fillStyle = "rgba(0,0,0,0.4)";
    c.beginPath();
    c.ellipse(X, Y + FOOT - 2, 13 * S, 6 * S, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
    const y = Y + FOOT + Math.sin(t / 420) * 1.2;
    if (!drawSprite(c, bank, id, X, y)) emojiBillboard(c, EMOJI[id] ?? "?", X, y, size, false);
  }

  /** Item bobbing above the floor. */
  private drawItem(c: CanvasRenderingContext2D, bank: ArtBank, X: number, Y: number, id: string, t: number): void {
    c.save();
    c.fillStyle = "rgba(0,0,0,0.4)";
    c.beginPath();
    c.ellipse(X, Y + FOOT - 2, 10 * S, 5 * S, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
    const y = Y + FOOT - 5 + Math.sin(t / 260) * 2.5;
    if (!drawSprite(c, bank, id, X, y)) emojiBillboard(c, EMOJI[id] ?? "?", X, y, 24 * S, false);
  }

  /** Player / monster / summon: shadow, footprint ring, sprite, hp bar. */
  private drawActor(c: CanvasRenderingContext2D, bank: ArtBank, X: number, Y: number, o: ActorArt): void {
    const base = Y + FOOT;
    const sc = o.scale * S;
    c.save();
    c.globalAlpha *= o.alpha;
    c.fillStyle = "rgba(0,0,0,0.45)";
    c.beginPath();
    c.ellipse(X, base - 1, 13 * sc, 6 * sc, 0, 0, Math.PI * 2);
    c.fill();
    if (o.ring) {
      c.strokeStyle = o.ring;
      c.lineWidth = 2;
      c.beginPath();
      c.ellipse(X, base - 1, 14 * sc, 7 * sc, 0, 0, Math.PI * 2);
      c.stroke();
    }
    if (o.flash) {
      c.fillStyle = "rgba(255,255,255,0.5)";
      c.beginPath();
      c.ellipse(X, base - 16 * sc, 12 * sc, 15 * sc, 0, 0, Math.PI * 2);
      c.fill();
    }
    const facing = FACING[o.dir]!;
    const suffix = o.pose === 1 ? ".w" : o.pose === 2 ? ".a" : "";
    const opts = { scale: o.scale, flip: facing === "s" && FACE_RIGHT[o.dir] === true };
    const drew =
      drawSprite(c, bank, `${o.id}.${facing}${suffix}`, X, base, opts) ||
      drawSprite(c, bank, `${o.id}.${facing}`, X, base, opts) ||
      drawSprite(c, bank, o.id, X, base, opts);
    if (!drew) emojiBillboard(c, EMOJI[o.id] ?? "?", X, base, 30 * sc);
    if (o.hp < 1) {
      const w = 26 * sc;
      const by = base - 44 * sc;
      c.fillStyle = "#200";
      c.fillRect(X - w / 2, by, w, 3);
      c.fillStyle = o.hpColor;
      c.fillRect(X - w / 2, by, Math.round(w * clamp(o.hp, 0, 1)), 3);
    }
    if (o.mark) {
      c.font = `${Math.round(13 * S)}px ${UI_FONT}`;
      c.textAlign = "center";
      c.textBaseline = "alphabetic";
      c.fillStyle = o.markColor;
      c.fillText(o.mark, X + 14 * sc, base - 40 * sc);
    }
    c.restore();
  }
}
