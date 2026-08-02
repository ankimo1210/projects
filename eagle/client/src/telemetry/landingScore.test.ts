import { describe, expect, it } from "vitest";
import { landingScore } from "./landingScore";

describe("landingScore", () => {
  it("awards 100 for a motionless level contact", () => {
    expect(landingScore(0, 0, 0)).toBe(100);
  });

  it("uses the documented 40/35/25 component weights", () => {
    expect(landingScore(3, 1.5, 10)).toBe(50);
  });

  it("floors each component at zero", () => {
    expect(landingScore(60, 30, 200)).toBe(0);
  });
});
