import { describe, expect, it } from "vitest";
import { parseServerMsg } from "./dispatch";

describe("parseServerMsg", () => {
  it("classifies a dsky_state frame", () => {
    const r = parseServerMsg(
      JSON.stringify({ type: "dsky_state", verb: "16" }),
    );
    expect(r.kind).toBe("dsky");
  });

  it("classifies a telemetry frame and exposes it", () => {
    const r = parseServerMsg(
      JSON.stringify({ type: "telemetry", mm: "66", t_s: 3.0 }),
    );
    expect(r.kind).toBe("telemetry");
    if (r.kind === "telemetry") expect(r.frame.mm).toBe("66");
  });

  it("ignores unknown message types", () => {
    const r = parseServerMsg(JSON.stringify({ type: "nope" }));
    expect(r.kind).toBe("ignore");
  });

  it("ignores malformed JSON without throwing", () => {
    expect(parseServerMsg("{not json").kind).toBe("ignore");
  });
});
