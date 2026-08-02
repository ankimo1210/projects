import { beforeEach, describe, expect, it } from 'vitest';
import { MockFlightModel } from '@b737/flightgear-adapter';
import { MVP_CIRCUIT_SCENARIO } from '@b737/scenario-engine';
import { clamp, type AircraftCommand, type AircraftState } from '@b737/shared';
import { TrainingSession } from '../src/trainingSession.js';
import { resetTranscriptIds } from '../src/transcript.js';

/**
 * Golden vertical-slice test (spec §21): a scripted pilot flies the complete
 * MVP circuit against the deterministic mock flight model while the training
 * session observes real state. Proves takeoff/climb/approach/touchdown/exit
 * detection, FO callouts, ATC flow and debrief generation end to end.
 */

const DT = 0.2; // scripted-pilot decision + physics batch interval (s)

class ScriptedPilot {
  throttle = 0;
  targetIasKt = 230;
  intercepting = false;
  onGlideslope = false;
  flareStarted = false;
  landed = false;

  constructor(
    private model: MockFlightModel,
    private session: TrainingSession,
  ) {}

  cmd(command: AircraftCommand): void {
    const result = this.model.applyCommand(command);
    if (!result.ok) throw new Error(`${command.type} rejected: ${result.error}`);
  }

  /** Answer every unanswered transcript prompt with its correct option. */
  answerPrompts(): void {
    for (const entry of this.session.transcript) {
      if (entry.expectedResponse && !entry.responseResult) {
        const correct = entry.expectedResponse.options.find((o) => o.correct)!;
        this.session.respond(entry.id, correct.id);
        // React to ATC targets like a pilot: dial MCP from the instruction text.
      }
    }
  }

  control(s: AircraftState): void {
    const phase = this.session.phaseId;
    const ra = s.position.radioAltitudeFt;
    const vs = this.session.fo.vSpeeds;

    // Follow ATC assignments on the MCP (what the user does with the knobs).
    const tgtHdg = this.session.runtime.getFlag('atcTargetHeadingDeg');
    if (typeof tgtHdg === 'number' && !this.intercepting) {
      this.cmd({ type: 'set_mcp_heading', headingDeg: tgtHdg });
    }
    const tgtAlt = this.session.runtime.getFlag('atcTargetAltitudeFt');
    if (typeof tgtAlt === 'number' && !this.onGlideslope) {
      this.cmd({ type: 'set_mcp_altitude', altitudeFt: tgtAlt });
      if (tgtAlt < s.position.altitudeFtMsl - 300) {
        this.cmd({ type: 'set_mcp_vertical_speed', verticalSpeedFpm: -1000 });
      }
    }

    // --- speed hold via throttle (no autothrottle in M1) ---
    if (!s.weightOnWheels && !this.flareStarted) {
      this.throttle = clamp(this.throttle + (this.targetIasKt - s.speeds.iasKt) * 0.003, 0, 1);
      this.cmd({ type: 'set_throttle', valueNorm: this.throttle });
    }

    if (phase === 'takeoff_roll' || phase === 'line_up' || phase === 'rotation') {
      if (s.weightOnWheels && s.speeds.iasKt >= vs.vrKt) {
        this.cmd({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.55 });
      } else if (!s.weightOnWheels) {
        this.holdPitch(s, 13);
      }
    }

    if (phase === 'initial_climb') {
      // gear up after the positive-rate exchange
      if (!s.weightOnWheels && ra > 80 && s.controls.gearLeverDown) {
        this.cmd({ type: 'set_gear', down: false });
      }
      if (ra > 500 && !s.mcp.autopilotEngaged) {
        this.holdPitch(s, 12);
        if (ra > 600) {
          this.cmd({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
          this.cmd({ type: 'set_autopilot', engaged: true });
          this.targetIasKt = 210;
        }
      } else if (!s.mcp.autopilotEngaged) {
        this.holdPitch(s, 13);
      }
      // slow down + first approach flaps once on the base assignment (1,800 ft)
      if (typeof tgtAlt === 'number' && tgtAlt < 2500) {
        this.targetIasKt = 175;
        if (s.controls.flapHandleDetent < 15 && s.speeds.iasKt < 195) {
          this.cmd({ type: 'set_flaps', detent: 15 });
        }
      }
    }

    if (phase === 'approach_setup') {
      // fully configure BEFORE glideslope capture, then track the localizer
      this.targetIasKt = vs.vappKt;
      if (s.controls.flapHandleDetent < 15 && s.speeds.iasKt < 195) {
        this.cmd({ type: 'set_flaps', detent: 15 });
      }
      if (s.speeds.iasKt < 180 && !s.controls.gearLeverDown) {
        this.cmd({ type: 'set_gear', down: true });
        this.cmd({ type: 'set_speedbrake_armed', armed: true });
        this.cmd({ type: 'set_autobrake', setting: '3' });
      }
      if (s.controls.flapHandleDetent < 30 && s.speeds.iasKt < 172 && s.controls.gearLeverDown) {
        this.cmd({ type: 'set_flaps', detent: 30 });
      }
      const loc = s.nav.locDeviationDots;
      if (loc !== null && Math.abs(loc) < 1.6) this.intercepting = true;
      if (this.intercepting) {
        const hdg = 284.4 + clamp((loc ?? 0) * 12, -35, 35);
        this.cmd({ type: 'set_mcp_heading', headingDeg: ((hdg % 360) + 360) % 360 });
      }
      const gs = s.nav.gsDeviationDots;
      if (!this.onGlideslope && gs !== null && gs < 0.3) {
        this.onGlideslope = true;
        this.cmd({ type: 'set_mcp_altitude', altitudeFt: 0 });
      }
      if (this.onGlideslope && gs !== null) {
        const vsCmd = clamp(700 - gs * 350, 300, 1200);
        this.cmd({ type: 'set_mcp_vertical_speed', verticalSpeedFpm: -vsCmd });
      }
    }

    if (phase === 'final_approach') {
      this.targetIasKt = vs.vappKt;
      if (s.controls.flapHandleDetent < 30 && s.speeds.iasKt < 172) {
        this.cmd({ type: 'set_flaps', detent: 30 });
        this.cmd({ type: 'set_gear', down: true });
        this.cmd({ type: 'set_speedbrake_armed', armed: true });
        this.cmd({ type: 'set_autobrake', setting: '3' });
      }
      const loc = s.nav.locDeviationDots;
      if (loc !== null) {
        const gain = ra < 500 ? 8 : 12;
        const hdg = 284.4 + clamp(loc * gain, -30, 30);
        this.cmd({ type: 'set_mcp_heading', headingDeg: ((hdg % 360) + 360) % 360 });
      }
      const gs = s.nav.gsDeviationDots;
      if (gs !== null) {
        const vsCmd = clamp(700 - gs * 350, 300, ra < 1200 ? 1000 : 1200);
        this.cmd({ type: 'set_mcp_vertical_speed', verticalSpeedFpm: -vsCmd });
      }
      const checklist = this.session.runtime.checklistRuns.get('landing')!;
      if (
        !checklist.complete &&
        s.controls.flapHandleDetent >= 30 &&
        s.controls.gearPositionNorm > 0.99 &&
        s.controls.speedbrakeArmed
      ) {
        this.session.answerChecklistItem('landing');
      }
    }

    if ((phase === 'final_approach' || phase === 'landing') && ra < 40 && !this.landed) {
      if (!this.flareStarted) {
        this.flareStarted = true;
        this.cmd({ type: 'set_autopilot', engaged: false });
        this.throttle = 0;
        this.cmd({ type: 'set_throttle', valueNorm: 0 });
      }
      // gentle flare: shallow the path without ballooning, wings level
      this.holdPitch(s, 4);
      this.cmd({
        type: 'set_control_axis',
        axis: 'roll',
        valueNorm: clamp(-s.attitude.rollDeg * 0.08, -0.3, 0.3),
      });
    }

    if (s.weightOnWheels && this.flareStarted && !this.landed) {
      this.landed = true;
      this.cmd({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0 });
      this.cmd({ type: 'set_reverse_thrust', leverNorm: 1 });
    }

    // Rollout: stow reverse, then steer right and taxi clear of the pavement.
    // The scenario only leaves this phase on real runway geometry (R-08).
    if (phase === 'rollout') {
      this.cmd({ type: 'set_reverse_thrust', leverNorm: 0 });
      this.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 1 });
      this.cmd({ type: 'set_throttle', valueNorm: s.speeds.gsKt < 12 ? 0.3 : 0 });
    }

    if (phase === 'runway_exit') {
      this.cmd({ type: 'set_control_axis', axis: 'yaw', valueNorm: 0 });
      this.cmd({ type: 'set_throttle', valueNorm: 0 });
      this.cmd({ type: 'set_brakes', valueNorm: 0.3 });
      this.cmd({ type: 'set_reverse_thrust', leverNorm: 0 });
      const checklist = this.session.runtime.checklistRuns.get('after_landing')!;
      if (!checklist.complete) {
        this.cmd({ type: 'set_speedbrake', leverNorm: 0 });
        this.cmd({ type: 'set_flaps', detent: 0 });
        this.cmd({ type: 'set_autobrake', setting: 'OFF' });
        this.cmd({ type: 'set_light', light: 'strobe', on: false });
        this.cmd({ type: 'set_light', light: 'landing', on: false });
        this.cmd({ type: 'set_light', light: 'taxi', on: true });
        this.session.answerChecklistItem('after_landing');
      }
    }
  }

  private holdPitch(s: AircraftState, targetDeg: number): void {
    this.cmd({
      type: 'set_control_axis',
      axis: 'pitch',
      valueNorm: clamp((targetDeg - s.attitude.pitchDeg) * 0.2, -0.6, 0.7),
    });
  }
}

describe('full circuit end-to-end (mock model + training session)', () => {
  beforeEach(() => resetTranscriptIds());

  it('flies takeoff → vectors → ILS → landing → exit and produces a debrief', () => {
    const scenario = {
      ...MVP_CIRCUIT_SCENARIO,
      initialState: { ...MVP_CIRCUIT_SCENARIO.initialState, startAt: 'threshold' as const },
    };
    const model = new MockFlightModel(scenario.initialState);
    const session = new TrainingSession(scenario, { mode: 'evaluation' });
    const pilot = new ScriptedPilot(model, session);

    // ---- before takeoff: control check, config, checklist, clearance ----
    session.update(model.snapshot(0));
    // full and free: roll, pitch AND rudder, as the hint asks
    for (const v of [1, -1, 0]) {
      session.notifyAxisInput('roll', v);
      session.notifyAxisInput('pitch', v);
      session.notifyAxisInput('yaw', v);
    }
    pilot.cmd({ type: 'set_autobrake', setting: 'RTO' });
    pilot.cmd({ type: 'set_light', light: 'landing', on: true });
    pilot.cmd({ type: 'set_light', light: 'strobe', on: true });
    model.step(DT);
    session.update(model.snapshot(0));
    for (let i = 0; i < 6; i++) session.answerChecklistItem('before_takeoff');
    expect(session.runtime.checklistRuns.get('before_takeoff')!.complete).toBe(true);

    session.requestTakeoffClearance();
    pilot.answerPrompts();
    expect(session.runtime.getFlag('takeoffClearanceReceived')).toBe(true);

    // ---- roll ----
    pilot.cmd({ type: 'set_parking_brake', engaged: false });
    pilot.cmd({ type: 'set_throttle', valueNorm: 1 });
    pilot.throttle = 1;

    const phasesSeen = new Set<string>([session.phaseId]);
    let simTime = 0;
    const MAX_SIM_SEC = 1000;
    while (!session.complete && simTime < MAX_SIM_SEC) {
      model.step(DT);
      simTime += DT;
      const state = model.snapshot(Date.now());
      session.update(state);
      phasesSeen.add(session.phaseId);
      pilot.control(state);
      pilot.answerPrompts();
    }

    // ---- assertions: phase coverage ----
    for (const phase of [
      'line_up',
      'takeoff_roll',
      'rotation',
      'initial_climb',
      'approach_setup',
      'final_approach',
      'landing',
      'rollout',
      'runway_exit',
      'debrief',
    ]) {
      expect(
        phasesSeen,
        `phase ${phase} was never reached (last=${session.phaseId} t=${simTime})`,
      ).toContain(phase);
    }
    expect(session.complete).toBe(true);

    // ---- FO callouts in order ----
    const foMessages = session.transcript
      .filter((e) => e.speaker === 'first_officer')
      .map((e) => e.message);
    const idx80 = foMessages.indexOf('Eighty knots.');
    const idxV1 = foMessages.indexOf('V1.');
    const idxRot = foMessages.indexOf('Rotate.');
    const idxPos = foMessages.indexOf('Positive rate.');
    expect(idx80).toBeGreaterThanOrEqual(0);
    expect(idxV1).toBeGreaterThan(idx80);
    expect(idxRot).toBeGreaterThan(idxV1);
    expect(idxPos).toBeGreaterThan(idxRot);

    // ---- ATC flow ----
    const atcMessages = session.transcript.filter((e) => e.speaker === 'atc').map((e) => e.message);
    expect(atcMessages.some((m) => m.includes('cleared for takeoff'))).toBe(true);
    expect(atcMessages.some((m) => m.includes('cleared ILS'))).toBe(true);
    expect(atcMessages.some((m) => m.includes('cleared to land'))).toBe(true);
    expect(session.runtime.getFlag('landingClearanceReceived')).toBe(true);

    // ---- milestones ----
    const eventIds = session.runtime.events.map((e) => e.id);
    expect(eventIds).toContain('positive_rate');
    expect(eventIds).toContain('established_on_approach');
    expect(eventIds).toContain('reverse_deployed');
    expect(eventIds).not.toContain('runway_incursion');
    expect(eventIds).not.toContain('landed_without_clearance');

    // ---- debrief ----
    const report = session.debrief();
    expect(report.categories).toHaveLength(6);
    expect(report.metrics['Touchdown sink rate']).toBeDefined();
    expect(report.metrics['Rotation speed']).toBeDefined();
    const findingsDump =
      report.categories
        .filter((c) => c.findings.length > 0)
        .map((c) => `${c.id}=${c.score} [${c.findings.map((f) => f.label).join('; ')}]`)
        .join(' | ') + ` || metrics: ${JSON.stringify(report.metrics)}`;
    expect(['PASS', 'PASS_WITH_DEVIATIONS'], `debrief=${report.overall} ${findingsDump}`).toContain(
      report.overall,
    );
  }, 30000);
});
