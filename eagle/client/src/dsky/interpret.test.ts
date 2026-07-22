import { describe, expect, it } from "vitest";
import { interpret } from "./interpret";
import { initialDsky } from "./reducer";

const base = { ...initialDsky, connected: true };

describe("interpret", () => {
  it("explains the mission clock monitor with register hints", () => {
    const i = interpret({ ...base, verb: "16", noun: "36", prog: "00" });
    expect(i.action).toContain("連続監視");
    expect(i.action).toContain("ミッション時計");
    expect(i.registers.join("/")).toContain("R3 = 秒");
    expect(i.program).toContain("P00");
  });

  it("explains the lamp test", () => {
    const i = interpret({ ...base, verb: "35" });
    expect(i.action).toContain("ランプテスト");
  });

  it("guides recovery on OPR ERR", () => {
    const i = interpret({ ...base, oprErr: true });
    expect(i.alerts.join("/")).toContain("RSET");
  });

  it("flags flashing as waiting for input", () => {
    const i = interpret({ ...base, verbNounFlash: true });
    expect(i.alerts.join("/")).toContain("待");
  });

  it("reports disconnect before anything else", () => {
    const i = interpret({ ...base, connected: false });
    expect(i.alerts.join("/")).toContain("未接続");
  });

  it("treats a blank display as idle", () => {
    const i = interpret(base);
    expect(i.action).toContain("VERB");
  });

  it("shows partial entry while typing", () => {
    const i = interpret({ ...base, verb: "1 " });
    expect(i.action).toContain("入力中");
  });
});
