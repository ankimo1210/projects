// Screens: title -> base -> dungeon -> result -> base. One canvas, keyboard only.
// This file owns state and input; drawing lives in ./render.

import { CARDS } from "../engine/cards";
import { createRun } from "../engine/dungeon";
import { CLASSES, DUNGEON_LIST, type DungeonDef } from "../engine/dungeon-def";
import { step } from "../engine/turn";
import { tileAt, type Action, type CardId, type ClassId, type Dir, type DungeonState } from "../engine/types";
import { buyCard, canStart, finishRun, loadSave, persist, sellCard, shopList, startRun, type SaveV1, type Store } from "../game/meta";
import { describe } from "./log";
import { ArtBank } from "./render/art";
import { drawCardBar, drawCastleCard, drawHelp, drawLog, drawMinimap, drawOverlay, drawPendingCard, drawTopBar, ruleTags } from "./render/hud";
import { H, MAP_X, MAP_Y, W } from "./render/layout";
import { SceneRenderer } from "./render/scene";
import { drawBase, drawResult, drawTitle, GRID, type BaseUi } from "./render/screens";

type Screen = "title" | "base" | "dungeon" | "result";

/** How long the castle name card stays up. */
const CARD_MS = 1700;

export class App {
  private screen: Screen = "title";
  private save: SaveV1;
  private run: DungeonState | null = null;
  private def: DungeonDef = DUNGEON_LIST[1]!;
  private hand: CardId[] = [];
  private log: string[] = [];
  private pendingCard: number | null = null;
  private discardMode = false;
  private base: BaseUi = { pane: "storage", cursor: 0, shopCursor: 0, picks: [], msg: "", dungeonIdx: 1 };
  private result: { text: string[] } | null = null;
  private overlayClosed = false;
  private helpOpen = false;
  private titleUntil = 0;
  private scene = new SceneRenderer();

  constructor(
    private ctx: CanvasRenderingContext2D,
    private store: Store,
    private now: () => number = () => performance.now(),
    readonly art: ArtBank = new ArtBank(),
  ) {
    this.save = loadSave(store);
  }

  // ---- input ---------------------------------------------------------------

  key(k: string): void {
    switch (this.screen) {
      case "title":
        if (k === "Enter" || k === " ") this.screen = "base";
        break;
      case "base":
        this.baseKey(k);
        break;
      case "dungeon":
        this.dungeonKey(k);
        break;
      case "result":
        if (k === "Enter" || k === " ") {
          this.screen = "base";
          this.base = { ...this.base, picks: [], cursor: 0, msg: "" };
        }
        break;
    }
    this.draw();
  }

  private baseKey(k: string): void {
    const b = this.base;
    b.msg = "";
    if (k === "Tab") {
      b.pane = b.pane === "storage" ? "shop" : "storage";
      return;
    }
    if (k === "c") {
      const ids = Object.keys(CLASSES) as ClassId[];
      this.save = { ...this.save, cls: ids[(ids.indexOf(this.save.cls) + 1) % ids.length]! };
      this.persist();
      return;
    }
    if (k === "[" || k === "]") {
      b.dungeonIdx = (b.dungeonIdx + (k === "[" ? -1 : 1) + DUNGEON_LIST.length) % DUNGEON_LIST.length;
      const limit = DUNGEON_LIST[b.dungeonIdx]!.handSize;
      if (b.picks.length > limit) b.picks = b.picks.slice(0, limit);
      return;
    }
    if (b.pane === "storage") {
      const n = this.save.storage.length;
      const last = Math.max(0, n - 1);
      // the storage is a grid now, so all four arrows move inside it
      if (k === "ArrowLeft") b.cursor = Math.max(0, b.cursor - 1);
      else if (k === "ArrowRight") b.cursor = Math.min(last, b.cursor + 1);
      else if (k === "ArrowUp") b.cursor = Math.max(0, b.cursor - GRID.cols);
      else if (k === "ArrowDown") b.cursor = Math.min(last, b.cursor + GRID.cols);
      else if (k === " ") {
        if (n === 0) return;
        const i = b.picks.indexOf(b.cursor);
        if (i >= 0) b.picks.splice(i, 1);
        else if (b.picks.length < this.selectedDef.handSize) b.picks.push(b.cursor);
        else b.msg = `持ち込みは${this.selectedDef.handSize}枚まで`;
      } else if (k === "s") {
        if (n === 0) return;
        this.save = sellCard(this.save, b.cursor);
        b.picks = [];
        b.cursor = Math.min(b.cursor, Math.max(0, this.save.storage.length - 1));
        this.persist();
      } else if (k === "Enter") this.startRun();
    } else {
      const list = shopList();
      if (k === "ArrowLeft") b.shopCursor = Math.max(0, b.shopCursor - 1);
      else if (k === "ArrowRight") b.shopCursor = Math.min(list.length - 1, b.shopCursor + 1);
      else if (k === "Enter") {
        const item = list[b.shopCursor]!;
        const r = buyCard(this.save, item.card);
        this.save = r.save;
        b.msg = r.error ?? `${CARDS[item.card].name}を買った`;
        this.persist();
      }
    }
  }

  private get selectedDef(): DungeonDef {
    return DUNGEON_LIST[this.base.dungeonIdx]!;
  }

  private startRun(): void {
    const def = this.selectedDef;
    const hand = this.base.picks.map((i) => this.save.storage[i]!);
    const err = canStart(this.save, def, hand);
    if (err) {
      this.base.msg = err;
      return;
    }
    const r = startRun(this.save, def, this.base.picks);
    this.save = r.save;
    this.hand = r.hand;
    this.def = def;
    this.persist();
    const seed = (Date.now() ^ Math.floor(Math.random() * 0xffffffff)) >>> 0;
    this.run = createRun(seed, def, r.hand, this.save.cls);
    this.scene.reset(def.id);
    this.log = [`${def.name}に挑む（BET ${def.bet}）${ruleTags(def.rules).join(" ")}`, "移動 矢印/qezc  カード 1-0  階段/祭壇 Enter  ヘルプ ?"];
    this.pendingCard = null;
    this.discardMode = false;
    this.overlayClosed = false;
    this.helpOpen = false;
    this.titleUntil = this.now() + CARD_MS;
    this.screen = "dungeon";
  }

  /** shop/casino panel while standing on the tile, until dismissed with Esc */
  private get overlay(): "shop" | "casino" | null {
    if (!this.run || this.overlayClosed) return null;
    const kind = tileAt(this.run.map, this.run.player.pos).kind;
    return kind === "shop" || kind === "casino" ? kind : null;
  }

  private dungeonKey(k: string): void {
    if (!this.run) return;
    if (k === "?" || k === "/" || k === "h") {
      this.helpOpen = !this.helpOpen;
      return;
    }
    if (this.helpOpen) {
      if (k === "Escape" || k === "Enter" || k === " ") this.helpOpen = false;
      return;
    }
    const overlay = this.overlay;
    if (overlay) {
      if (k === "Escape") {
        this.overlayClosed = true;
        return;
      }
      if (overlay === "shop") {
        const i = keyToCardIndex(k);
        if (i !== null && i < 3) this.act({ type: "buy", index: i });
        return;
      }
      if (k === " " || k === "Enter") this.act({ type: "spin" });
      return;
    }
    const dir = keyToDir(k);
    if (k === "Escape") {
      this.pendingCard = null;
      this.discardMode = false;
      return;
    }
    const cardIdx = keyToCardIndex(k);
    if (this.discardMode) {
      if (cardIdx !== null) this.act({ type: "discardCard", index: cardIdx });
      this.discardMode = false;
      return;
    }
    if (this.pendingCard !== null) {
      if (dir !== null) {
        this.act({ type: "useCard", index: this.pendingCard, dir });
        this.pendingCard = null;
      }
      return;
    }
    if (k === "d") {
      this.discardMode = true;
      return;
    }
    if (cardIdx !== null) {
      const card = this.run.player.hand[cardIdx];
      if (card === undefined) return;
      if (CARDS[card].target === "dir") this.pendingCard = cardIdx;
      else this.act({ type: "useCard", index: cardIdx });
      return;
    }
    if (dir !== null) {
      this.act({ type: "move", dir });
      return;
    }
    if (k === "." || k === " ") this.act({ type: "wait" });
    else if (k === "Enter" || k === ">") {
      if (this.run.map.altar) this.act({ type: "takeAltar" });
      else this.act({ type: "descend" });
    }
  }

  act(action: Action): void {
    if (!this.run) return;
    const before = this.run;
    const beforeTile = tileAt(before.map, before.player.pos).kind;
    const { state, events } = step(before, action);
    this.run = state;
    for (const line of describe(events, before, state)) this.pushLog(line);
    this.scene.onStep(before, state, events, this.now(), action);
    if (tileAt(state.map, state.player.pos).kind !== beforeTile) this.overlayClosed = false;
    if (state.result) this.endRun(state);
  }

  private endRun(state: DungeonState): void {
    const outcome = { result: state.result!, winCollected: state.winCollected, multiplier: state.winMultiplier, hand: state.player.hand };
    const r = finishRun(this.save, this.def, outcome);
    this.save = r.save;
    this.persist();
    const head = state.result === "clear" ? "クリア！" : state.result === "dead" ? "力尽きた…" : "脱出";
    const mult = state.winMultiplier > 1 ? `  ダブルアップ ×${state.winMultiplier}${state.result === "clear" ? "" : "（未達成）"}` : "";
    const text = [head, `${this.def.name}  WIN +${r.payout}（所持 ${this.save.win}）${mult}`, `到達 ${state.floorNo}F / ${state.turn} ターン`];
    if (state.result !== "dead") text.push(`手札 ${state.player.hand.length} 枚を倉庫へ`);
    if (r.overflow.length) text.push(`倉庫が溢れて ${r.overflow.length} 枚失った`);
    text.push("", "Enter で拠点へ");
    this.result = { text };
    this.screen = "result";
  }

  private pushLog(line: string): void {
    this.log.push(line);
    if (this.log.length > 100) this.log.shift();
  }

  private persist(): void {
    persist(this.store, this.save);
  }

  /** True while something on screen is still moving; the host loop idles otherwise. */
  get busy(): boolean {
    if (this.screen !== "dungeon" || !this.run) return false;
    // the particle layer and the castle card both animate on their own
    return this.titleUntil > this.now() || this.scene.busy(this.now(), this.run);
  }

  // ---- drawing -------------------------------------------------------------

  draw(): void {
    const c = this.ctx;
    c.fillStyle = "#000";
    c.fillRect(0, 0, W, H);
    switch (this.screen) {
      case "title":
        drawTitle(c);
        break;
      case "base":
        drawBase(c, this.art, this.save, this.base, this.selectedDef);
        break;
      case "dungeon":
        this.drawDungeon();
        break;
      case "result":
        if (this.result) drawResult(c, this.result.text);
        break;
    }
  }

  private drawDungeon(): void {
    const s = this.run;
    if (!s) return;
    const c = this.ctx;
    this.scene.draw(c, this.art, s, this.now());
    drawMinimap(c, s, MAP_X + 8, MAP_Y + 8);
    drawTopBar(c, s, this.def);
    drawLog(c, this.log);
    drawCardBar(c, this.art, s, this.pendingCard, this.discardMode);
    const pending = this.pendingCard === null ? undefined : s.player.hand[this.pendingCard];
    if (pending) drawPendingCard(c, this.art, pending);
    const ov = this.overlay;
    if (ov) drawOverlay(c, this.art, s, ov);
    if (this.helpOpen) drawHelp(c);
    const left = this.titleUntil - this.now();
    if (left > 0) drawCastleCard(c, this.def, Math.min(1, left / 420, (CARD_MS - left) / 160));
  }

  // ---- debug hooks ---------------------------------------------------------
  get state() {
    return { screen: this.screen, save: this.save, run: this.run, log: this.log, hand: this.hand };
  }
}

function keyToDir(k: string): Dir | null {
  switch (k) {
    case "ArrowUp":
    case "8":
    case "k":
      return 0;
    case "e":
    case "9":
      return 1;
    case "ArrowRight":
    case "6":
    case "l":
      return 2;
    case "c":
    case "3":
      return 3;
    case "ArrowDown":
    case "2":
    case "j":
      return 4;
    case "z":
    case "1":
      return 5;
    case "ArrowLeft":
    case "4":
    case "h":
      return 6;
    case "q":
    case "7":
      return 7;
    default:
      return null;
  }
}

function keyToCardIndex(k: string): number | null {
  if (k.length !== 1 || k < "0" || k > "9") return null;
  return k === "0" ? 9 : Number(k) - 1;
}
