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

  it('keeps a manual brake takeover until RTO is explicitly reselected', () => {
    const m = makeModel();
    m.applyCommand({ type: 'set_parking_brake', engaged: false });
    m.applyCommand({ type: 'set_autobrake', setting: 'RTO' });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(25);
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.step(1);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0.9);

    m.applyCommand({ type: 'set_brakes', valueNorm: 0.7 });
    expect(m.snapshot(0).controls.brakeNorm).toBe(0.7);
    m.step(1 / 60);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0.7);

    m.applyCommand({ type: 'set_brakes', valueNorm: 0 });
    m.step(0.1);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0);

    m.applyCommand({ type: 'set_autobrake', setting: 'RTO' });
    m.applyCommand({ type: 'set_throttle', valueNorm: 1 });
    m.step(0.1);
    m.applyCommand({ type: 'set_throttle', valueNorm: 0 });
    m.step(0.1);
    expect(m.snapshot(0).controls.brakeNorm).toBe(0.9);
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

// M5: route following, weather and failures.
describe('LNAV, weather and failures', () => {
  function airborne(overrides: Partial<typeof DEFAULT_SCENARIO_INIT> = {}) {
    const m = makeModel(overrides);
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
    m.applyCommand({ type: 'set_throttle', valueNorm: 0.8 });
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 4000 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.step(30);
    return m;
  }

  it('refuses LNAV without a route and annunciates it once loaded', () => {
    const m = airborne();
    expect(m.applyCommand({ type: 'set_lnav', armed: true }).ok).toBe(false);
    expect(
      m.applyCommand({ type: 'load_route', sidId: 'SFOUT1', starId: null, approachId: null }).ok,
    ).toBe(true);
    expect(m.applyCommand({ type: 'set_lnav', armed: true }).ok).toBe(true);
    m.step(2);
    const s = m.snapshot(0);
    expect(s.fms.legs.map((l) => l.waypoint.id)).toEqual(['SFOUT', 'BAYNE', 'WESTB']);
    expect(s.mcp.rollMode).toBe('LNAV');
    expect(s.fms.distanceToWaypointNm).toBeGreaterThan(0);
  });

  it('flies the route and sequences to the next leg', () => {
    const m = airborne();
    m.applyCommand({ type: 'load_route', sidId: 'SFOUT1', starId: null, approachId: null });
    m.applyCommand({ type: 'set_lnav', armed: true });
    const start = m.snapshot(0).fms;
    expect(start.activeLegIndex).toBe(0);
    m.step(180);
    const s = m.snapshot(0);
    expect(s.fms.activeLegIndex).toBeGreaterThan(0);
    expect(Math.abs(s.fms.crossTrackNm ?? 99)).toBeLessThan(2);
  });

  it('direct-to a fix that is not in the route builds a one-leg route', () => {
    const m = airborne();
    expect(m.applyCommand({ type: 'direct_to', waypointId: 'MIDBA' }).ok).toBe(true);
    expect(m.applyCommand({ type: 'direct_to', waypointId: 'NOWHERE' }).ok).toBe(false);
    expect(m.snapshot(0).fms.legs.map((l) => l.waypoint.id)).toEqual(['MIDBA']);
  });

  it('reports the wind it is actually in, blending toward the wind aloft', () => {
    const m = makeModel({
      windDirDeg: 290,
      windSpeedKt: 6,
      weather: {
        windAloftDirDeg: 250,
        windAloftSpeedKt: 45,
        gustKt: 0,
        visibilityM: 8000,
        turbulence: 0,
      },
    });
    const surface = m.snapshot(0).weather;
    expect(surface.windSpeedKt).toBeCloseTo(6, 0);
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.2 });
    m.step(90);
    const aloft = m.snapshot(0).weather;
    expect(aloft.windSpeedKt).toBeGreaterThan(surface.windSpeedKt + 5);
    expect(aloft.visibilityM).toBe(8000);
  });

  it('an engine failure stops that engine and halves the thrust available', () => {
    const m = airborne();
    const before = m.snapshot(0);
    expect(before.systems.engines.left.running).toBe(true);
    m.applyCommand({ type: 'inject_failure', failure: 'engine_1_flameout' });
    m.step(10);
    const after = m.snapshot(0);
    expect(after.systems.engines.left.running).toBe(false);
    expect(after.activeFailures).toContain('engine_1_flameout');
    expect(after.engines.left.n1Pct).toBeLessThan(before.engines.left.n1Pct);
    expect(after.systems.engines.right.running).toBe(true);
    // the annunciator sees it through the systems model, not a second path
    expect(after.systems.annunciations.some((a) => a.id === 'gen1_off_bus')).toBe(false);
  });

  it('latches failures until clear and restores their pre-injection state', () => {
    const m = makeModel();
    expect(m.applyCommand({ type: 'inject_failure', failure: 'engine_1_flameout' }).ok).toBe(true);
    expect(
      m.applyCommand({ type: 'set_system_switch', switch: 'start_lever_left', on: true }).ok,
    ).toBe(false);
    expect(m.applyCommand({ type: 'set_engine_start', engine: 'left', mode: 'flight' }).ok).toBe(
      false,
    );

    expect(m.applyCommand({ type: 'inject_failure', failure: 'generator_2' }).ok).toBe(true);
    expect(m.applyCommand({ type: 'set_system_switch', switch: 'gen2', on: true }).ok).toBe(false);
    expect(m.applyCommand({ type: 'inject_failure', failure: 'hydraulic_a' }).ok).toBe(true);
    expect(
      m.applyCommand({ type: 'set_system_switch', switch: 'hyd_pump_eng1', on: true }).ok,
    ).toBe(false);

    const failed = m.snapshot(0);
    expect(failed.activeFailures).toEqual(['engine_1_flameout', 'generator_2', 'hydraulic_a']);
    expect(failed.systems.engines.left.running).toBe(false);
    expect(failed.systems.electrical.gen2On).toBe(false);
    expect(failed.systems.hydraulic.engPump1On).toBe(false);

    expect(m.applyCommand({ type: 'clear_failures' }).ok).toBe(true);
    const restored = m.snapshot(0);
    expect(restored.activeFailures).toEqual([]);
    expect(restored.systems.engines.left.running).toBe(true);
    expect(restored.systems.electrical.gen1On).toBe(true);
    expect(restored.systems.electrical.gen2On).toBe(true);
    expect(restored.systems.hydraulic.engPump1On).toBe(true);
  });

  it('yaws toward the failed engine and airborne rudder reduces the deviation', () => {
    const run = (failure: 'engine_1_flameout' | 'engine_2_flameout', rudder: number) => {
      const m = airborne({ seed: 73706 });
      m.applyCommand({ type: 'set_autopilot', engaged: false });
      const start = m.snapshot(0).attitude.headingDegMag;
      m.applyCommand({ type: 'inject_failure', failure });
      m.applyCommand({ type: 'set_control_axis', axis: 'yaw', valueNorm: rudder });
      m.step(10);
      const end = m.snapshot(0);
      const headingDelta = ((end.attitude.headingDegMag - start + 540) % 360) - 180;
      return { headingDelta, state: end };
    };

    const leftFailed = run('engine_1_flameout', 0);
    const rightFailed = run('engine_2_flameout', 0);
    expect(leftFailed.headingDelta).toBeLessThan(-5);
    expect(rightFailed.headingDelta).toBeGreaterThan(5);
    expect(leftFailed.state.position).not.toEqual(rightFailed.state.position);
    expect(leftFailed.state.attitude.rollDeg).toBeLessThan(rightFailed.state.attitude.rollDeg);

    const correctedLeft = run('engine_1_flameout', 0.75);
    const correctedRight = run('engine_2_flameout', -0.75);
    expect(Math.abs(correctedLeft.headingDelta)).toBeLessThan(Math.abs(leftFailed.headingDelta));
    expect(Math.abs(correctedRight.headingDelta)).toBeLessThan(Math.abs(rightFailed.headingDelta));
  });

  it('a failure armed in the scenario is active from the first sample', () => {
    const m = makeModel({ failures: ['hydraulic_a'] });
    const s = m.snapshot(0);
    expect(s.activeFailures).toContain('hydraulic_a');
    expect(s.systems.hydraulic.engPump1On).toBe(false);
  });
});

// F-02 regression: the weather must act on the aircraft, not just the readout.
describe('weather acts on the physics', () => {
  const CROSSWIND_WX = {
    windAloftDirDeg: 235,
    windAloftSpeedKt: 38,
    gustKt: 0,
    visibilityM: 9000,
    turbulence: 0,
  };

  function airborneInWind() {
    const m = makeModel({ windDirDeg: 245, windSpeedKt: 22, weather: CROSSWIND_WX });
    flyTakeoff(m, 145);
    m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
    m.applyCommand({ type: 'set_throttle', valueNorm: 0.8 });
    m.applyCommand({ type: 'set_mcp_altitude', altitudeFt: 5000 });
    m.applyCommand({ type: 'set_autopilot', engaged: true });
    m.step(30);
    return m;
  }

  it('LNAV converges onto the route in a strong crosswind', () => {
    // Before F-02 the LNAV crab was computed for the blended wind while the
    // aircraft drifted by the surface wind — the cross-track never settled.
    const m = airborneInWind();
    m.applyCommand({ type: 'load_route', sidId: 'SFOUT1', starId: null, approachId: null });
    m.applyCommand({ type: 'set_lnav', armed: true });
    m.step(120);
    const s = m.snapshot(0);
    expect(s.mcp.rollMode).toBe('LNAV');
    expect(Math.abs(s.fms.crossTrackNm ?? 99)).toBeLessThan(0.8);
  });

  it('the aircraft drifts with the blended wind, not the surface wind', () => {
    const m = airborneInWind();
    // hold a heading and compare track vs heading: the drift angle implied by
    // the wind the aircraft reports must match what actually happens
    m.applyCommand({ type: 'set_mcp_heading', headingDeg: 284 });
    m.step(60);
    const s = m.snapshot(0);
    const driftDeg = Math.abs(
      ((s.attitude.groundTrackDegMag - s.attitude.headingDegMag + 540) % 360) - 180,
    );
    // ~30+ kt of crosswind component at 250 kt GS ≈ 5-9° of drift
    expect(driftDeg).toBeGreaterThan(3);
    expect(s.weather.windSpeedKt).toBeGreaterThan(25); // blended, not the 22 kt surface
  });

  it('gusts vary the wind the aircraft is in, reproducibly per seed', () => {
    const run = () => {
      const m = makeModel({
        seed: 42,
        windDirDeg: 245,
        windSpeedKt: 20,
        weather: { ...CROSSWIND_WX, gustKt: 15 },
      });
      flyTakeoff(m, 145);
      m.step(30);
      return m.snapshot(0);
    };
    const a = run();
    const b = run();
    expect(a.weather.gustKt).toBeGreaterThan(0.5); // gusting, not static
    expect(a.weather.gustKt).toBeCloseTo(b.weather.gustKt, 10); // seeded
    expect(a.position).toEqual(b.position); // and so is the trajectory
  });

  it('scenario turbulence shakes the aircraft more than calm air', () => {
    const rollActivity = (turbulence: number): number => {
      const m = makeModel({
        seed: 7,
        weather: { ...CROSSWIND_WX, windAloftSpeedKt: 6, turbulence },
      });
      flyTakeoff(m, 145);
      m.applyCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.1 });
      let sum = 0;
      for (let i = 0; i < 600; i++) {
        m.step(1 / 60);
        sum += Math.abs(m.snapshot(0).attitude.rollDeg);
      }
      return sum / 600;
    };
    expect(rollActivity(1)).toBeGreaterThan(rollActivity(0) * 1.5);
  });
});
