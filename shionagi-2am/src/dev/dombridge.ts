// Runs a bot through the real input path: instead of handing its decisions to
// the simulation, it presses keys and moves the mouse by dispatching DOM events
// and lets the game's own Input class read them, exactly as it reads a person's.

import type { Input } from "../input";
import type { Sim } from "../sim/sim";
import type { InputFrame, SimEvent } from "../sim/types";
import type { Bot } from "./bot";
import type { Driver } from "./driver";

export class DomBridge implements Driver {
  private down = new Set<string>();
  private aim = false;
  private accX = 0;
  private accY = 0;
  private releaseE = false;
  /** events dispatched so far, by kind */
  readonly sent = { key: 0, mouseButton: 0, mouseMove: 0 };

  constructor(
    private bot: Bot,
    private input: Input,
    private canvas: HTMLCanvasElement,
  ) {
    // a real mouse reports whole pixels: carry the remainder to the next move
    bot.look = (_sim, dYaw, dPitch) => {
      const gain = this.input.radiansPerPixel;
      this.accX += -dYaw / gain;
      this.accY += -dPitch / gain;
    };
  }

  private key(code: string, on: boolean): void {
    if (on === this.down.has(code)) return;
    if (on) this.down.add(code);
    else this.down.delete(code);
    window.dispatchEvent(new KeyboardEvent(on ? "keydown" : "keyup", { code, bubbles: true }));
    this.sent.key++;
  }

  step(sim: Sim): InputFrame {
    const want = this.bot.step(sim);
    if (this.releaseE) {
      this.key("KeyE", false);
      this.releaseE = false;
    }
    this.key("KeyW", want.mz > 0);
    this.key("KeyS", want.mz < 0);
    this.key("KeyD", want.mx > 0);
    this.key("KeyA", want.mx < 0);
    this.key("ShiftLeft", want.run);
    if (want.interact) {
      this.key("KeyE", true);
      this.releaseE = true;
    }
    if (want.aim !== this.aim) {
      this.aim = want.aim;
      const target: EventTarget = want.aim ? this.canvas : window;
      target.dispatchEvent(new MouseEvent(want.aim ? "mousedown" : "mouseup", { button: 2, bubbles: true }));
      this.sent.mouseButton++;
    }
    if (want.fire) {
      this.canvas.dispatchEvent(new MouseEvent("mousedown", { button: 0, bubbles: true }));
      window.dispatchEvent(new MouseEvent("mouseup", { button: 0, bubbles: true }));
      this.sent.mouseButton += 2;
    }
    const px = Math.round(this.accX);
    const py = Math.round(this.accY);
    if (px !== 0 || py !== 0) {
      this.accX -= px;
      this.accY -= py;
      window.dispatchEvent(new MouseEvent("mousemove", { movementX: px, movementY: py, bubbles: true }));
      this.sent.mouseMove++;
    }
    return this.input.frame();
  }

  observe(ev: SimEvent, sim: Sim): void {
    this.bot.observe(ev, sim);
  }

  status(): string {
    return `${this.bot.status()} (DOM events: ${this.sent.key} key, ${this.sent.mouseButton} button, ${this.sent.mouseMove} move)`;
  }
}
