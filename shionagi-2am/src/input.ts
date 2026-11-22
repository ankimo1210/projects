// Keyboard and mouse. Movement and buttons are sampled once per simulation
// step; mouse-look is forwarded straight away so the view never lags the hand.

import type { InputFrame } from "./sim/types";

export class Input {
  private keys = new Set<string>();
  private aim = false;
  private fireEdge = false;
  private interactEdge = false;
  /** true once the pointer has been captured at least once */
  everLocked = false;
  locked = false;
  /** Free-look radians per pixel of mouse movement. */
  sensitivity = 0.00135;
  /** when false, key and mouse input is ignored (title, pause) */
  enabled = false;
  onLock: (locked: boolean) => void = () => {};
  onAnyKey: (code: string) => void = () => {};

  constructor(
    private canvas: HTMLCanvasElement,
    private look: (dYaw: number, dPitch: number) => void,
    private readonly aimProgress: () => number = () => 0,
  ) {
    window.addEventListener("keydown", (e) => {
      if (e.repeat) return;
      this.onAnyKey(e.code);
      if (!this.enabled) return;
      this.keys.add(e.code);
      if (e.code === "KeyE") this.interactEdge = true;
      if (e.code === "Tab" || e.code === "Space" || e.code.startsWith("Arrow")) e.preventDefault();
    });
    window.addEventListener("keyup", (e) => this.keys.delete(e.code));
    window.addEventListener("blur", () => this.release());
    canvas.addEventListener("mousedown", (e) => {
      if (!this.enabled) return;
      if (e.button === 0) this.fireEdge = true;
      if (e.button === 2) this.aim = true;
    });
    window.addEventListener("mouseup", (e) => {
      if (e.button === 2) this.aim = false;
    });
    window.addEventListener("contextmenu", (e) => e.preventDefault());
    window.addEventListener("mousemove", (e) => {
      if (!this.enabled) return;
      // without pointer lock (refused, or an embedded preview) look still works
      if (!this.locked && this.everLocked) return;
      const dx = clampDelta(e.movementX);
      const dy = clampDelta(e.movementY);
      const gain = this.radiansPerPixel;
      if (dx !== 0 || dy !== 0) this.look(-dx * gain, -dy * gain);
    });
    document.addEventListener("pointerlockchange", () => {
      this.locked = document.pointerLockElement === this.canvas;
      if (this.locked) this.everLocked = true;
      else this.release();
      this.onLock(this.locked);
    });
  }

  /** Follow the sight animation so entering and leaving aim never jumps between gains. */
  get radiansPerPixel(): number {
    return this.sensitivity * (1 - this.aimProgress() / 3);
  }

  requestLock(): void {
    try {
      const r = this.canvas.requestPointerLock() as unknown;
      if (r && typeof (r as Promise<void>).catch === "function") (r as Promise<void>).catch(() => {});
    } catch {
      // pointer lock unavailable: carry on with free mouse-look
    }
  }

  release(): void {
    this.keys.clear();
    this.aim = false;
    this.fireEdge = false;
    this.interactEdge = false;
  }

  /** Read (and clear) the input for one simulation step. */
  frame(): InputFrame {
    const k = this.keys;
    const mx = (k.has("KeyD") || k.has("ArrowRight") ? 1 : 0) - (k.has("KeyA") || k.has("ArrowLeft") ? 1 : 0);
    const mz = (k.has("KeyW") || k.has("ArrowUp") ? 1 : 0) - (k.has("KeyS") || k.has("ArrowDown") ? 1 : 0);
    const f: InputFrame = {
      mx,
      mz,
      run: k.has("ShiftLeft") || k.has("ShiftRight"),
      aim: this.aim,
      fire: this.fireEdge,
      interact: this.interactEdge,
    };
    this.fireEdge = false;
    this.interactEdge = false;
    return f;
  }
}

/** Browsers occasionally report a huge bogus delta right after locking. */
function clampDelta(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(-160, Math.min(160, v));
}
