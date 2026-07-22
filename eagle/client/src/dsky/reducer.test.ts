import { describe, expect, it } from "vitest";
import { initialDsky, reduceServerMsg } from "./reducer";

describe("reduceServerMsg", () => {
  it("applies a dsky_state message", () => {
    const msg = {
      type: "dsky_state", schema_version: 1,
      prog: "63", verb: "16", noun: "36",
      r1: "+00031", r2: "      ", r3: "      ",
      lamps: { comp_acty: true },
      verb_noun_flash: true, restart: false, standby: false,
      key_rel: false, opr_err: false, temp: false,
    };
    const s = reduceServerMsg(initialDsky, msg as never);
    expect(s.verb).toBe("16");
    expect(s.r1).toBe("+00031");
    expect(s.lamps.comp_acty).toBe(true);
    expect(s.verbNounFlash).toBe(true);
  });

  it("ignores unknown message types", () => {
    const s = reduceServerMsg(initialDsky, { type: "bogus" } as never);
    expect(s).toBe(initialDsky);
  });
});
