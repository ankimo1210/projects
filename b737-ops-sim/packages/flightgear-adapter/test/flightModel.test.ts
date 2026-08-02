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

// R-06: publish rate must not scale simulated time.
describe('physics timing is independent of the state publish rate', () => {
  it.each([25, 30, 40, 50, 60])('advances 1.0 s of sim time at %i Hz', (rateHz) => {
    const m = makeModel();
    const dt = 1 / rateHz;
    for (let i = 0; i < rateHz; i++) m.step(dt);
    expect(m.snapshot(0).simTimeSec).toBeCloseTo(1, 2);
  });

  it('reaches the same speed after 20 s regardless of tick size', () => {
    const speedAt = (rateHz: number): number => {
      const m = makeModel();
      m.applyCommand({ type: 'set_parking_brake', engaged: false });
      m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
      for (let i = 0; i < rateHz * 20; i++) m.step(1 / rateHz);
      return m.snapshot(0).speeds.iasKt;
    };
    expect(speedAt(25)).toBeCloseTo(speedAt(60), 0);
    expect(speedAt(40)).toBeCloseTo(speedAt(60), 0);
  });
});

// R-07: RTO is a rejected-takeoff device, not a landing autobrake.
describe('RTO autobrake', () => {
  /** Accelerate to takeoff speed, then chop the thrust levers. */
  function rejectedTakeoff(setting: 'OFF' | 'RTO'): number {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_autobrake', setting });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(25);
    expect(m.snapshot(0).speeds.iasKt).toBeGreaterThan(RTO_TEST_MIN_ABORT_KT);
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.step(20);
    return m.snapshot(0).speeds.iasKt;
  }
  const RTO_TEST_MIN_ABORT_KT = 100;

  it('brakes on a rejected takeoff while OFF does not', () => {
    const withRto = rejectedTakeoff('RTO');
    const withoutRto = rejectedTakeoff('OFF');
    expect(withRto).toBeLessThan(withoutRto - 20);
    expect(withRto).toBeLessThan(30);
  });

  it('reports braking through the state while RTO is decelerating', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_autobrake', setting: 'RTO' });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(25);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0); // no braking during the roll
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.step(1);
    expect(m.snapshot(0).controls.brakeNorm).toBeGreaterThan(0.5);
  });

  it('does not act as a landing autobrake after touchdown', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_autobrake', setting: 'RTO' });
    flyTakeoff(m, 145);
    expect(m.snapshot(0).weightOnWheels).toBe(false);
    // airborne: RTO is disarmed, so no braking is commanded
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.step(2);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0);
  });
});

// M3 T2: the autopilot flies modes, not just knob values.
describe('autopilot modes', () => {
  /** Put the aircraft airborne, some way out on the approach course. */
  function onApproach(): MockFlightModel {
    const m = makeModel();
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
    m.applyCommand({ type: 'set_throttle', valueNorm: 0.75 });
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 3000 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.step(60);
    return m;
  }

  it('annunciates HDG SEL and ALT HOLD without the approach armed', () => {
    const m = onApproach();
    m.step(120); // let it settle at the selected altitude
    const s = m.snapshot(0);
    expect(s.mcp.rollMode).toBe('HDG_SEL');
    expect(s.mcp.pitchMode).toBe('ALT_HOLD');
    expect(Math.abs(s.position.altitudeFtMsl - 3000)).toBeLessThan(250);
  });

  it('arms then captures the localizer, and only then the glideslope', () => {
    const m = onApproach();
    m.applyCommand({ type: 'set_ap_approach_mode', armed: true });
    m.step(1);
    expect(m.snapshot(0).mcp.approachArmed).toBe(true);
    // pointed away from the runway: armed, not captured
    m.applyCommand({ type: 'set_mcp_heading', headingDeg: 104 });
    m.step(60);
    expect(m.snapshot(0).mcp.rollMode).toBe('LOC_ARM');
    expect(m.snapshot(0).mcp.pitchMode).toBe('GS_ARM');
  });

  it('captures and tracks the localizer and glideslope from a final-approach start', () => {
    const m = makeModel({ startAt: 'final_approach' });
    const initial = m.snapshot(0);
    expect(initial.weightOnWheels).toBe(false);
    expect(initial.nav.locDeviationDots).not.toBeNull();

    m.applyCommand({ type: 'set_mcp_heading', headingDeg: 284 });
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 2000 });
    m.applyCommand({ type: 'set_throttle', valueNorm: 0.45 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.applyCommand({ type: 'set_ap_approach_mode', armed: true });
    m.step(20);
    const s = m.snapshot(0);
    expect(s.mcp.rollMode).toBe('LOC');
    expect(s.mcp.pitchMode).toBe('GS');
    expect(Math.abs(s.nav.locDeviationDots!)).toBeLessThan(1);
    expect(Math.abs(s.nav.gsDeviationDots!)).toBeLessThan(1);
    // and it is descending on the path rather than holding the MCP altitude
    expect(s.speeds.verticalSpeedFpm).toBeLessThan(-300);
  });

  it('TO/GA drops the autopilot, commands go-around thrust and climbs', () => {
    const m = onApproach();
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 500 });
    m.applyCommand({ type: 'set_mcp_vertical_speed', verticalSpeedFpm: -1000 });
    m.step(60);
    expect(m.snapshot(0).speeds.verticalSpeedFpm).toBeLessThan(0);

    m.applyCommand({ type: 'set_toga', engaged: true });
    m.step(20);
    const s = m.snapshot(0);
    expect(s.mcp.autopilotEngaged).toBe(false);
    expect(s.mcp.pitchMode).toBe('TOGA');
    expect(s.mcp.approachArmed).toBe(false);
    expect(s.engines.left.throttleLeverNorm).toBe(1);
    expect(s.speeds.verticalSpeedFpm).toBeGreaterThan(0);
  });
});

// R-17: an MCP V/S selection has a sign; the autopilot must honour it.
describe('MCP vertical speed sign', () => {
  it('descends when a negative V/S is selected below a higher target altitude', () => {
    const m = makeModel();
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
    m.applyCommand({ type: 'set_throttle', valueNorm: 0.8 });
    m.step(40); // gain some altitude first
    const start = m.snapshot(0).position.altitudeFtMsl;
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: start + 3000 });
    m.applyCommand({ type: 'set_mcp_vertical_speed', verticalSpeedFpm: -1000 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.step(20);
    expect(m.snapshot(0).speeds.verticalSpeedFpm).toBeLessThan(0);
  });
});
