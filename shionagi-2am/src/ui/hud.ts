// The whole on-screen display: health, rounds left, and a line of control
// guidance when the moment needs one. Everything else is told by the world.

import { TUNE } from "../sim/sim";
import type { SimState } from "../sim/types";

const el = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`missing #${id}`);
  return node as T;
};

const key = (k: string): string => `<kbd>${k}</kbd>`;
const SEP = '<span class="sep"></span>';

const HINTS: Record<string, string> = {
  move: `${key("W")}${key("A")}${key("S")}${key("D")} 移動${SEP}マウス 視点`,
  run: `${key("Shift")} 走る —— 足音は遠くまで届く`,
  aim: `右クリック 構える${SEP}左クリック 撃つ`,
};

export class Hud {
  private root = el<HTMLDivElement>("hud");
  private health = el<HTMLDivElement>("health");
  private ammo = el<HTMLDivElement>("ammo");
  private pips = el<HTMLSpanElement>("ammo-pips");
  private num = el<HTMLElement>("ammo-num");
  private cross = el<HTMLDivElement>("crosshair");
  private prompt = el<HTMLDivElement>("prompt");
  private hint = el<HTMLDivElement>("hint");
  private message = el<HTMLDivElement>("message");
  private last = { hp: -1, ammo: -1, gun: false, prompt: "", hint: "", message: "", aim: false };
  private hintId = "";
  private hintT = 0;

  show(on: boolean): void {
    this.root.hidden = !on;
  }

  /** Show a control hint for a while (or until `clearHint`). */
  setHint(id: string, seconds: number): void {
    this.hintId = id;
    this.hintT = seconds;
  }

  clearHint(id: string): void {
    if (this.hintId === id) this.hintT = 0;
  }

  get currentHint(): string {
    return this.hintT > 0 ? this.hintId : "";
  }

  update(s: SimState, dt: number): void {
    const p = s.player;
    const l = this.last;
    if (p.hp !== l.hp) {
      l.hp = p.hp;
      const seg = this.health.children;
      const per = TUNE.maxHp / seg.length;
      for (let i = 0; i < seg.length; i++) (seg[i] as HTMLElement).classList.toggle("off", p.hp <= i * per);
      this.health.classList.toggle("low", p.hp <= per);
    }
    if (p.hasGun !== l.gun || p.ammo !== l.ammo) {
      l.gun = p.hasGun;
      l.ammo = p.ammo;
      this.ammo.hidden = !p.hasGun;
      this.num.textContent = String(p.ammo);
      this.pips.innerHTML = "<i></i>".repeat(Math.min(p.ammo, 12));
      this.ammo.classList.toggle("empty", p.ammo === 0);
    }
    const aim = p.aim > 0.5 && s.phase === "play";
    if (aim !== l.aim) {
      l.aim = aim;
      this.cross.hidden = !aim;
    }
    const prompt = s.prompt && s.phase === "play" ? `${key("E")} ${s.prompt.label}` : "";
    if (prompt !== l.prompt) {
      l.prompt = prompt;
      this.prompt.innerHTML = prompt;
    }
    this.hintT = Math.max(0, this.hintT - dt);
    const hint = this.hintT > 0 && s.phase === "play" ? (HINTS[this.hintId] ?? "") : "";
    if (hint !== l.hint) {
      l.hint = hint;
      this.hint.innerHTML = hint;
    }
    const msg = s.message && s.phase === "play" ? s.message.text : "";
    if (msg !== l.message) {
      l.message = msg;
      this.message.textContent = msg;
    }
  }
}

export type ScreenKind = "none" | "title" | "pause" | "dead" | "clear";

const CONTROLS = `
  <div class="keys">
    <span>${key("W")}${key("A")}${key("S")}${key("D")}</span><span>移動</span>
    <span>マウス</span><span>視点</span>
    <span>${key("Shift")}</span><span>走る</span>
    <span>${key("E")}</span><span>調べる・拾う</span>
    <span>右クリック</span><span>構える</span>
    <span>左クリック</span><span>撃つ</span>
    <span>${key("Esc")} ${key("P")}</span><span>一時停止</span>
  </div>`;

export class Screens {
  private root = el<HTMLDivElement>("screen");
  kind: ScreenKind = "none";

  show(kind: ScreenKind, s?: SimState): void {
    this.kind = kind;
    const r = this.root;
    r.className = kind === "none" ? "" : `show ${kind}`;
    switch (kind) {
      case "none":
        r.innerHTML = "";
        break;
      case "title":
        r.innerHTML = `
          <div class="panel">
            <h1>汐凪市 午前2時<small>SHIONAGI 02:00</small></h1>
            <p>豪雨。高潮。町じゅうの灯りが落ちて、もう一時間になる。<br />
              渡船ターミナルの夜勤は、あなたひとり。</p>
            <p class="radio">《防災無線》……避難先は、汐凪警察署です。</p>
            ${CONTROLS}
            <div><span class="go">クリックして始める</span></div>
            <p class="note">音が出ます。ヘッドホン推奨。</p>
          </div>`;
        break;
      case "pause":
        r.innerHTML = `
          <div class="panel">
            <h2>一時停止</h2>
            ${CONTROLS}
            <div><span class="go">クリックして再開</span></div>
          </div>`;
        break;
      case "dead":
        r.innerHTML = `
          <div class="panel late">
            <h2>雨音だけが残った</h2>
            <div><span class="go">${key("E")} / クリックでやり直す</span></div>
          </div>`;
        break;
      case "clear": {
        const st = s?.stats;
        const t = s ? s.time : 0;
        const clock = 120 + Math.floor(t / 60); // minutes after midnight
        const hh = Math.floor(clock / 60);
        const mm = String(clock % 60).padStart(2, "0");
        const dur = `${Math.floor(t / 60)}分${String(Math.floor(t % 60)).padStart(2, "0")}秒`;
        r.innerHTML = `
          <div class="panel late">
            <h2>午前${hh}時${mm}分&#12288;汐凪警察署</h2>
            <p>冷えた取っ手が、内側から引かれた。</p>
            <div class="stats">
              <span>所要時間</span><b>${dur}</b>
              <span>発砲</span><b>${st ? st.shots : 0} 発</b>
              <span>やり直し</span><b>${st ? st.deaths : 0} 回</b>
            </div>
            <div><span class="go">もう一度</span></div>
          </div>`;
        break;
      }
    }
  }
}
