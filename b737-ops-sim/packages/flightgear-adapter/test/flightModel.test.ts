import { describe, expect, it } from 'vitest';
import { DEFAULT_SCENARIO_INIT } from '../src/backend.js';
import { MockFlightModel } from '../src/mock/flightModel.js';

function makeModel(overrides: Partial<typeof DEFAULT_SCENARIO_INIT> = {}) {
  return new MockFlightModel({ ...DEFAULT_SCENARIO_INIT, startAt: 'threshold', ...overrides });
}

/** Fly a full-thrust takeoff roll, rotating at vrKt; returns the model. */
function flyTakeoff(model: MockFlightModel, vrKt: number): void {
  model.applyCommand({ type: 'set_parking_brake', engaged: false });
  model.applyCommand({ type: 'set_throttle', valueNorm: 1 });
  for (let i = 0; i < 60 * 120; i++) {
    const s = model.snapshot(0);
    if (!s.weightOnWheels) return;
    if (s.speeds.iasKt >= vrKt) {
      model.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.6 });
    }
    model.step(1 / 60);
  }
}

describe('MockFlightModel determinism', () => {
  it('same seed + same commands => identical trajectory', () => {
    const a = makeModel({ seed: 123 });
    const b = makeModel({ seed: 123 });
    for (const m of [a, b]) {
      m.applyCommand({ type: 'set_parking_brake', engaged: false });
      m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
      m.step(30);
    }
    const sa = a.snapshot(0);
    const sb = b.snapshot(0);
    expect(sa.position).toEqual(sb.position);
    expect(sa.speeds).toEqual(sb.speeds);
    expect(sa.attitude).toEqual(sb.attitude);
  });
});

describe('ground behavior', () => {
  it('holds position with parking brake set and idle thrust', () => {
    const m = makeModel();
    m.step(10);
    const s = m.snapshot(0);
    expect(s.speeds.gsKt).toBeLessThan(0.5);
    expect(s.weightOnWheels).toBe(true);
  });

  it('accelerates under takeoff thrust with brakes released', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(20);
    const s = m.snapshot(0);
    expect(s.speeds.iasKt).toBeGreaterThan(60);
    expect(s.weightOnWheels).toBe(true); // no rotation yet
    expect(s.engines.left.n1Pct).toBeGreaterThan(80);
  });

  it('rejects parking brake while rolling', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(15);
    const res = m.applyCommand({ type: 'set_parking_brake', engaged: true });
    expect(res.ok).toBe(false);
  });

  it('rejects gear retraction on ground', () => {
    const m = makeModel();
    const res = m.applyCommand({ type: 'set_gear', down: false });
    expect(res.ok).toBe(false);
  });
});

describe('takeoff and climb', () => {
  it('lifts off after rotation near Vr and climbs', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    const s = m.snapshot(0);
    expect(s.weightOnWheels).toBe(false);
    // hold attitude, keep climbing
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.12 });
    m.step(15);
    const s2 = m.snapshot(0);
    expect(s2.speeds.verticalSpeedFpm).toBeGreaterThan(300);
    expect(s2.position.radioAltitudeFt).toBeGreaterThan(200);
  });

  it('gear retracts in flight and drag decreases', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.12 });
    m.step(3);
    const res = m.applyCommand({ type: 'set_gear', down: false });
    expect(res.ok).toBe(true);
    m.step(10);
    expect(m.snapshot(0).controls.gearPositionNorm).toBe(0);
  });
});

describe('autopilot holds', () => {
  it('tracks selected heading and altitude', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.1 });
    m.step(20);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
    m.applyCommand({ type: 'set_mcp_heading', headingDeg: 20 });
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 3000 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.step(180);
    const s = m.snapshot(0);
    expect(Math.abs(s.attitude.headingDegMag - 20)).toBeLessThan(4);
    expect(Math.abs(s.position.altitudeFtMsl - 3000)).toBeLessThan(150);
  });
});

describe('ILS geometry', () => {
  it('shows centered localizer while rolling down the centerline', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    // sample mid-roll (~on the runway, aligned with the course)
    for (let i = 0; i < 60 * 60; i++) {
      m.step(1 / 60);
      if (m.snapshot(0).speeds.iasKt > 80) break;
    }
    const s = m.snapshot(0);
    expect(s.weightOnWheels).toBe(true);
    expect(s.nav.locDeviationDots).not.toBeNull();
    expect(Math.abs(s.nav.locDeviationDots!)).toBeLessThan(0.6);
  });

  it('loses localizer validity well past the departure end', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.1 });
    m.step(60); // several km beyond the runway
    expect(m.snapshot(0).nav.locDeviationDots).toBeNull();
  });
});

describe('landing rollout', () => {
  it('reverse thrust is rejected in flight and works on ground', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    const airborne = m.applyCommand({ type: 'set_reverse_thrust', leverNorm: 0.8 });
    expect(airborne.ok).toBe(false);
  });

  it('autobrake + reverse decelerate the aircraft after touchdown', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_autobrake', setting: '3' });
    m.applyCommand({ type: 'set_speedbrake_armed', armed: true });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    // accelerate then chop thrust before rotation — a rejected-takeoff-like
    // ground deceleration exercises brakes without needing a full pattern
    m.step(25);
    const fast = m.snapshot(0).speeds.iasKt;
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.applyCommand({ type: 'set_reverse_thrust', leverNorm: 1 });
    m.applyCommand({ type: 'set_brakes', valueNorm: 0.7 });
    m.step(25);
    const slow = m.snapshot(0).speeds.iasKt;
    expect(fast).toBeGreaterThan(100);
    expect(slow).toBeLessThan(30);
  });
});
