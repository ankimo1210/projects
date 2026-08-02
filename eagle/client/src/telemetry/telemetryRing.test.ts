import { describe, expect, it } from "vitest";
import { TelemetryRing } from "./telemetryRing";
import type { TelemetryFrame } from "./types";

function frame(t: number, mm: string): TelemetryFrame {
  return {
    schema_version: 2,
    t_s: t,
    frozen: false,
    alt_m: 500 - t,
    vz_ms: -1,
    v_horiz_ms: 0,
    tilt_deg: 0,
    mass_kg: 9000,
    fuel_dps_kg: 1900,
    fuel_rcs_kg: 148,
    thrust_n: 14800,
    throttle_cmd_pulses: 1234,
    jets: 0,
    mm,
    agc_alt_m: null,
    agc_hdot_ms: null,
    nav_err_alt_m: null,
    nav_err_hdot_ms: null,
    drift_ms: 0,
    downlink_wps: 50,
    ingest_drops: 0,
    touchdown: null,
    demo_mode: false,
    assist_active: false,
    assist_target_vz_ms: null,
    touchdown_v_vert_ms: null,
    touchdown_v_horiz_ms: null,
    touchdown_tilt_deg: null,
    handover: false,
  };
}

describe("TelemetryRing", () => {
  it("caps at 3000 frames, dropping the oldest", () => {
    const ring = new TelemetryRing();
    for (let i = 0; i < 3100; i++) ring.push(frame(i, "63"));
    const frames = ring.frames();
    expect(frames.length).toBe(3000);
    expect(frames[0].t_s).toBe(100); // first 100 dropped
    expect(frames[frames.length - 1].t_s).toBe(3099);
  });

  it("tracks the latest frame", () => {
    const ring = new TelemetryRing();
    ring.push(frame(1, "63"));
    ring.push(frame(2, "63"));
    expect(ring.latest?.t_s).toBe(2);
  });

  it("records only mm transitions as phases", () => {
    const ring = new TelemetryRing();
    ring.push(frame(1, "63"));
    ring.push(frame(2, "63")); // no transition
    ring.push(frame(3, "66")); // 63 -> 66
    ring.push(frame(4, "66")); // no transition
    expect(ring.phases.map((p) => p.mm)).toEqual(["63", "66"]);
    expect(ring.phases[1].t_s).toBe(3);
  });

  it("ignores empty mm for phase tracking", () => {
    const ring = new TelemetryRing();
    ring.push(frame(1, ""));
    ring.push(frame(2, "63"));
    expect(ring.phases.map((p) => p.mm)).toEqual(["63"]);
  });

  it("increments version on each push", () => {
    const ring = new TelemetryRing();
    expect(ring.version).toBe(0);
    ring.push(frame(1, "63"));
    ring.push(frame(2, "63"));
    expect(ring.version).toBe(2);
  });
});
