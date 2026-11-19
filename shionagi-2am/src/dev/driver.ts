import type { Sim } from "../sim/sim";
import type { InputFrame, SimEvent } from "../sim/types";

/** Something that plays the game through the same inputs as a person. */
export interface Driver {
  /** Called once per simulation step, before it. May turn the view with `sim.applyLook`. */
  step(sim: Sim): InputFrame;
  /** Optional: told about everything the simulation emits. */
  observe?(ev: SimEvent, sim: Sim): void;
  status(): string;
}
