import { afterEach, expect, it, vi } from "vitest";
import { Input } from "../src/input";

afterEach(() => vi.unstubAllGlobals());

it("makes small mouse movements finer as the weapon comes up, and restores free look on release", () => {
  const pointer = new EventTarget();
  vi.stubGlobal("window", pointer);
  vi.stubGlobal("document", new EventTarget());
  const canvas = new EventTarget() as HTMLCanvasElement;
  const look = vi.fn();
  let aim = 0;
  const input = new Input(canvas, look, () => aim);
  input.enabled = true;
  const move = () => pointer.dispatchEvent(Object.assign(new Event("mousemove"), { movementX: 100, movementY: -40 }));

  for (const [progress, expectedYaw] of [[0, -0.135], [0.5, -0.1125], [1, -0.09], [0, -0.135]] as const) {
    aim = progress;
    move();
    expect(look).toHaveBeenLastCalledWith(expect.closeTo(expectedYaw, 5), expect.closeTo(-expectedYaw * 0.4, 5));
  }
});
