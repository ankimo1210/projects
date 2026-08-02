import { beforeEach, describe, expect, it } from 'vitest';
import { MockFlightModel } from '@b737/flightgear-adapter';
import {
  APPROACH_DRILL_SCENARIO,
  COLD_AND_DARK_SCENARIO,
  GATE_TO_GATE_SCENARIO,
} from '@b737/scenario-engine';
import {
  KSFO_TAXI,
  angleDiffDeg,
  bearingDeg,
  clamp,
  distanceM,
  type AircraftCommand,
  type AircraftState,
} from '@b737/shared';
import { TrainingSession } from '../src/trainingSession.js';
import { resetTranscriptIds } from '../src/transcript.js';

/**
 * Golden tests for the M3 scenarios (spec §21 "do not declare success from
 * static screens"): a scripted crew flies each scenario against the real mock
 * model, and the scenario/ATC/crew layers observe real state throughout.
 */

const DT = 0.2;

/** Steers along the taxi network and flies the ILS with the autopilot. */
class Crew {
  private target: { latDeg: number; lonDeg: number } | null = null;
  private answered = new Set<string>();

  constructor(
    private model: MockFlightModel,
    private session: TrainingSession,
  ) {}

  cmd(command: AircraftCommand): void {
    const result = this.model.applyCommand(command);
    if (!result.ok) throw new Error(`${command.type} rejected: ${result.error}`);
  }

  answerPrompts(): void {
    for (const entry of this.session.transcript) {
      if (entry.expectedResponse && !entry.responseResult && !this.answered.has(entry.id)) {
        this.answered.add(entry.id);
        const correct = entry.expectedResponse.options.find((o) => o.correct);
        if (correct) this.session.respond(entry.id, correct.id);
      }
    }
  }

  taxiTo(nodeId: string): void {
    const node = KSFO_TAXI.nodes[nodeId];
    this.target = node ? { latDeg: node.latDeg, lonDeg: node.lonDeg } : null;
  }

  /** Proportional nosewheel steering + speed hold toward the current target. */
  driveTaxi(s: AircraftState, targetSpeedKt = 14, stopWithinM = 0): boolean {
    if (!this.target) return false;
    const distM = distanceM(
      s.position.latDeg,
      s.position.lonDeg,
      this.target.latDeg,
      this.target.lonDeg,
    );
    if (stopWithinM > 0 && distM < stopWithinM) {
      this.cmd({ type: 'set_throttle', valueNorm: 0 });
      this.cmd({ type: 'set_brakes', valueNorm: 0.6 });
      this.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 0 });
      return true;
    }
    const bearing = bearingDeg(
      s.position.latDeg,
      s.position.lonDeg,
      this.target.latDeg,
      this.target.lonDeg,
    );
    const headingTrue = s.attitude.headingDegMag + 13.5; // KSFO variation
    const err = angleDiffDeg(headingTrue, bearing);
    this.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: clamp(err / 25, -1, 1) });
    const fast = s.speeds.gsKt > targetSpeedKt;
    this.cmd({ type: 'set_throttle', valueNorm: fast ? 0 : 0.32 });
    this.cmd({ type: 'set_brakes', valueNorm: s.speeds.gsKt > targetSpeedKt + 6 ? 0.35 : 0 });
    return false;
  }

  get reachedTarget(): boolean {
    return this.target === null;
  }
}

function step(model: MockFlightModel, session: TrainingSession, crew: Crew): AircraftState {
  model.step(DT);
  const state = model.snapshot(0);
  session.update(state);
  crew.answerPrompts();
  return state;
}

describe('gate-to-gate scenario', () => {
  beforeEach(() => resetTranscriptIds());

  it('taxis out under ground control, holds short, and only crosses when cleared', () => {
    const scenario = GATE_TO_GATE_SCENARIO;
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const crew = new Crew(model, session);
    session.update(model.snapshot(0));

    // ---- at the stand: Before Start, then request taxi ----
    expect(session.phaseId).toBe('preflight');
    for (let i = 0; i < 3; i++) session.answerChecklistItem('before_start');
    expect(session.runtime.checklistRuns.get('before_start')!.complete).toBe(true);

    session.requestTaxiClearance();
    crew.answerPrompts();
    expect(session.runtime.getFlag('taxiClearanceReceived')).toBe(true);

    // ---- Before Taxi, then taxi to the holding point ----
    crew.cmd({ type: 'set_light', light: 'taxi', on: true });
    crew.cmd({ type: 'set_flaps', detent: 5 });
    for (let t = 0; t < 30; t += DT) step(model, session, crew); // flaps travel
    crew.cmd({ type: 'set_parking_brake', engaged: false });
    step(model, session, crew);
    for (let i = 0; i < 4; i++) session.answerChecklistItem('before_taxi');
    expect(session.runtime.checklistRuns.get('before_taxi')!.complete).toBe(true);

    const route = ['P1', 'A1'];
    let legIndex = 0;
    crew.taxiTo(route[0]!);
    let simTime = 0;
    let heldShort = false;
    while (simTime < 400 && !heldShort) {
      const state = step(model, session, crew);
      simTime += DT;
      const last = legIndex === route.length - 1;
      const arrived = crew.driveTaxi(state, last ? 10 : 14, last ? 45 : 25);
      if (arrived && !last) {
        legIndex += 1;
        crew.taxiTo(route[legIndex]!);
      } else if (arrived && last && state.speeds.gsKt < 1) {
        heldShort = session.phaseId === 'hold_short';
      }
    }

    expect(session.phaseId).toBe('hold_short');
    // holding short means exactly that: never crossed the line uncleared
    const incursion = session.runtime.events.find((e) => e.id === 'runway_incursion');
    expect(incursion).toBeUndefined();
    // and ground handed us to the tower
    expect(session.transcript.some((e) => e.message.includes('contact tower'))).toBe(true);

    // ---- Before Takeoff + clearance ----
    for (const v of [1, -1, 0]) {
      session.notifyAxisInput('roll', v);
      session.notifyAxisInput('pitch', v);
      session.notifyAxisInput('yaw', v);
    }
    crew.cmd({ type: 'set_autobrake', setting: 'RTO' });
    crew.cmd({ type: 'set_light', light: 'landing', on: true });
    crew.cmd({ type: 'set_light', light: 'strobe', on: true });
    crew.cmd({ type: 'set_speedbrake', leverNorm: 0 });
    step(model, session, crew);
    for (let i = 0; i < 6; i++) session.answerChecklistItem('before_takeoff');
    expect(session.runtime.checklistRuns.get('before_takeoff')!.complete).toBe(true);

    session.requestTakeoffClearance();
    crew.answerPrompts();
    expect(session.runtime.getFlag('takeoffClearanceReceived')).toBe(true);

    // rolling onto the runway now is legal — the phase machine follows
    crew.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 0 });
    crew.cmd({ type: 'set_throttle', valueNorm: 0.6 });
    for (let t = 0; t < 20 && session.phaseId === 'hold_short'; t += DT) {
      step(model, session, crew);
    }
    expect(['before_takeoff', 'line_up', 'takeoff_roll']).toContain(session.phaseId);
    expect(session.runtime.events.some((e) => e.id === 'runway_incursion')).toBe(false);
  });
});

describe('approach drill scenario', () => {
  beforeEach(() => resetTranscriptIds());

  it('starts established on the ILS and lands using LOC/GS capture', () => {
    const scenario = APPROACH_DRILL_SCENARIO;
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const crew = new Crew(model, session);

    const first = model.snapshot(0);
    session.update(first);
    expect(first.weightOnWheels).toBe(false);
    expect(session.phaseId).toBe('final_approach');

    // configure and let the autopilot fly the approach
    crew.cmd({ type: 'set_mcp_heading', headingDeg: 284 });
    crew.cmd({ type: 'set_mcp_altitude', altitudeFt: 2000 });
    crew.cmd({ type: 'set_autopilot', engaged: true });
    crew.cmd({ type: 'set_ap_approach_mode', armed: true });
    crew.cmd({ type: 'set_gear', down: true });
    crew.cmd({ type: 'set_flaps', detent: 30 });
    crew.cmd({ type: 'set_speedbrake_armed', armed: true });
    crew.cmd({ type: 'set_autobrake', setting: '3' });
    crew.cmd({ type: 'set_throttle', valueNorm: 0.42 });

    let captured = false;
    let simTime = 0;
    let flaring = false;
    while (simTime < 300 && session.phaseId !== 'debrief') {
      const s = step(model, session, crew);
      simTime += DT;
      if (s.mcp.rollMode === 'LOC' && s.mcp.pitchMode === 'GS') captured = true;
      // speed control (no autothrottle)
      if (!s.weightOnWheels && !flaring) {
        const err = session.fo.vSpeeds.vappKt - s.speeds.iasKt;
        crew.cmd({
          type: 'set_throttle',
          valueNorm: clamp(s.engines.left.throttleLeverNorm + err * 0.004, 0, 1),
        });
      }
      // flare + rollout
      if (!s.weightOnWheels && s.position.radioAltitudeFt < 40 && !flaring) {
        flaring = true;
        crew.cmd({ type: 'set_autopilot', engaged: false });
        crew.cmd({ type: 'set_throttle', valueNorm: 0 });
      }
      if (flaring && !s.weightOnWheels) {
        crew.cmd({
          type: 'set_control_axis',
          axis: 'pitch',
          valueNorm: clamp((4 - s.attitude.pitchDeg) * 0.2, -0.4, 0.7),
        });
      }
      if (s.weightOnWheels && flaring) {
        crew.cmd({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
        if (s.speeds.gsKt > 60) crew.cmd({ type: 'set_reverse_thrust', leverNorm: 1 });
        if (session.phaseId === 'rollout') {
          crew.cmd({ type: 'set_reverse_thrust', leverNorm: 0 });
          crew.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 1 });
          crew.cmd({ type: 'set_throttle', valueNorm: s.speeds.gsKt < 12 ? 0.3 : 0 });
        }
        if (session.phaseId === 'runway_exit') {
          crew.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 0 });
          crew.cmd({ type: 'set_throttle', valueNorm: 0 });
          crew.cmd({ type: 'set_brakes', valueNorm: 0.3 });
          crew.cmd({ type: 'set_speedbrake', leverNorm: 0 });
          crew.cmd({ type: 'set_flaps', detent: 0 });
          crew.cmd({ type: 'set_autobrake', setting: 'OFF' });
          crew.cmd({ type: 'set_light', light: 'strobe', on: false });
          crew.cmd({ type: 'set_light', light: 'landing', on: false });
          crew.cmd({ type: 'set_light', light: 'taxi', on: true });
          session.answerChecklistItem('after_landing');
        }
      }
    }

    expect(captured, 'the autopilot never captured LOC and G/S').toBe(true);
    expect(session.phaseId, `ended in ${session.phaseId} at t=${simTime.toFixed(0)}`).toBe(
      'debrief',
    );
    const messages = session.transcript.map((e) => e.message);
    expect(messages.some((m) => m.startsWith('1000,'))).toBe(true);
    expect(messages.some((m) => m.startsWith('500,'))).toBe(true);
    expect(messages.some((m) => m.startsWith('Minimums'))).toBe(true);
  });

  it('flies a go-around when the crew calls it, and the drill records it', () => {
    const scenario = APPROACH_DRILL_SCENARIO;
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const crew = new Crew(model, session);
    session.update(model.snapshot(0));

    crew.cmd({ type: 'set_mcp_heading', headingDeg: 284 });
    crew.cmd({ type: 'set_autopilot', engaged: true });
    crew.cmd({ type: 'set_ap_approach_mode', armed: true });
    crew.cmd({ type: 'set_gear', down: true });
    crew.cmd({ type: 'set_flaps', detent: 30 });
    crew.cmd({ type: 'set_throttle', valueNorm: 0.42 });

    // descend to roughly the decision altitude, then go around
    let simTime = 0;
    while (simTime < 200 && model.snapshot(0).position.radioAltitudeFt > 300) {
      step(model, session, crew);
      simTime += DT;
    }
    session.announceGoAround();
    crew.cmd({ type: 'set_toga', engaged: true });
    crew.cmd({ type: 'set_gear', down: false });
    crew.cmd({ type: 'set_flaps', detent: 15 });
    crew.answerPrompts();

    while (simTime < 400 && session.phaseId !== 'debrief') {
      step(model, session, crew);
      simTime += DT;
    }

    expect(session.phaseId).toBe('debrief');
    expect(session.runtime.events.some((e) => e.id === 'go_around_established')).toBe(true);
    expect(
      session.transcript.some((e) => e.message.includes('go around, fly runway heading')),
    ).toBe(true);
    expect(model.snapshot(0).position.radioAltitudeFt).toBeGreaterThan(1500);
  });
});

describe('cold and dark scenario', () => {
  beforeEach(() => resetTranscriptIds());

  it('brings the aeroplane from cold and dark to both engines running', () => {
    const scenario = COLD_AND_DARK_SCENARIO;
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const crew = new Crew(model, session);
    session.update(model.snapshot(0));

    // ---- everything is off ----
    expect(session.phaseId).toBe('cold_and_dark');
    const dark = model.snapshot(0).systems;
    expect(dark.electrical.dcBusPowered).toBe(false);
    expect(dark.engines.left.running).toBe(false);

    // ---- power on + IRS ----
    crew.cmd({ type: 'set_system_switch', switch: 'battery', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'standby_power', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'irs_left', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'irs_right', on: true });
    step(model, session, crew);
    expect(session.phaseId).toBe('power_on');
    for (let i = 0; i < 3; i++) session.answerChecklistItem('preflight');
    expect(session.runtime.checklistRuns.get('preflight')!.complete).toBe(true);

    // ---- APU start (needs DC power) ----
    crew.cmd({ type: 'set_system_switch', switch: 'apu_master', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'apu_start', on: true });
    for (let t = 0; t < 32; t += DT) step(model, session, crew);
    expect(model.snapshot(0).systems.apu.state).toBe('running');
    expect(session.phaseId).toBe('apu_available');

    // ---- Before Start: generator, fuel, packs off, bleed ----
    crew.cmd({ type: 'set_system_switch', switch: 'apu_gen', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'fuel_pump_left', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'fuel_pump_right', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'bleed_apu', on: true });
    step(model, session, crew);
    for (let i = 0; i < 4; i++) session.answerChecklistItem('before_start_systems');
    expect(session.runtime.checklistRuns.get('before_start_systems')!.complete).toBe(true);
    step(model, session, crew); // the phase machine runs on the next sample
    expect(session.phaseId).toBe('engine_start');

    // ---- start both engines ----
    for (const [engine, lever] of [
      ['left', 'start_lever_left'],
      ['right', 'start_lever_right'],
    ] as const) {
      crew.cmd({ type: 'set_engine_start', engine, mode: 'ground' });
      for (let t = 0; t < 8; t += DT) step(model, session, crew); // motoring
      expect(model.snapshot(0).systems.engines[engine].n2Pct).toBeGreaterThan(20);
      crew.cmd({ type: 'set_system_switch', switch: lever, on: true });
      for (let t = 0; t < 12; t += DT) step(model, session, crew);
      expect(model.snapshot(0).systems.engines[engine].running).toBe(true);
    }
    expect(session.phaseId).toBe('after_start');

    // ---- After Start: generators, bleed off, packs on, hydraulics ----
    crew.cmd({ type: 'set_system_switch', switch: 'gen1', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'gen2', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'bleed_apu', on: false });
    crew.cmd({ type: 'set_system_switch', switch: 'bleed_eng1', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'bleed_eng2', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'pack_left', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'pack_right', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'hyd_pump_eng1', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'hyd_pump_eng2', on: true });
    for (let t = 0; t < 8; t += DT) step(model, session, crew);
    for (let i = 0; i < 4; i++) session.answerChecklistItem('after_start');
    expect(session.runtime.checklistRuns.get('after_start')!.complete).toBe(true);
    step(model, session, crew);
    expect(session.phaseId).toBe('ready_to_taxi');

    const s = model.snapshot(0).systems;
    expect(s.electrical.gen1On && s.electrical.gen2On).toBe(true);
    expect(s.hydraulic.systemAPressurePsi).toBeGreaterThan(2500);
    expect(s.annunciations.filter((a) => a.severity !== 'advisory')).toEqual([]);
    // and the aeroplane can now actually move
    crew.cmd({ type: 'set_parking_brake', engaged: false });
    crew.cmd({ type: 'set_throttle', valueNorm: 0.4 });
    for (let t = 0; t < 10; t += DT) step(model, session, crew);
    expect(model.snapshot(0).speeds.gsKt).toBeGreaterThan(3);
  });

  it('refuses an engine start with the packs on APU bleed', () => {
    const scenario = COLD_AND_DARK_SCENARIO;
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const crew = new Crew(model, session);
    session.update(model.snapshot(0));

    crew.cmd({ type: 'set_system_switch', switch: 'battery', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'apu_master', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'apu_start', on: true });
    for (let t = 0; t < 32; t += DT) step(model, session, crew);
    crew.cmd({ type: 'set_system_switch', switch: 'bleed_apu', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'pack_left', on: true });
    crew.cmd({ type: 'set_system_switch', switch: 'pack_right', on: true });
    step(model, session, crew);

    const rejected = model.applyCommand({
      type: 'set_engine_start',
      engine: 'left',
      mode: 'ground',
    });
    expect(rejected.ok).toBe(false);
    expect(rejected.ok ? '' : rejected.error).toMatch(/duct pressure/);
  });
});
