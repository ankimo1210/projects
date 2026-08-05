import { describe, expect, it } from 'vitest';
import { coldAndDarkSystems } from '@b737/shared';
import { makeTestAircraftState } from '@b737/shared/testing';
import { COLD_AND_DARK_SCENARIO, MVP_CIRCUIT_SCENARIO } from '@b737/scenario-engine';
import { TrainingSession } from '@b737/training-engine';
import { deriveGuidance } from '../src/cockpit/guidance.js';

describe('beginner mission guidance', () => {
  it('shows live progress for every flight-control direction', () => {
    const session = new TrainingSession(MVP_CIRCUIT_SCENARIO);
    session.update(makeTestAircraftState());

    const initial = deriveGuidance(session);
    expect(initial.target).toBe('cockpit');
    expect(initial.metrics).toHaveLength(6);
    expect(initial.metrics.every((metric) => metric.tone === 'warn')).toBe(true);

    for (const value of [-1, 1]) {
      session.notifyAxisInput('roll', value);
      session.notifyAxisInput('pitch', value);
      session.notifyAxisInput('yaw', value);
    }

    const complete = deriveGuidance(session);
    expect(complete.metrics.every((metric) => metric.tone === 'good')).toBe(true);
    expect(complete.metrics.every((metric) => metric.value === '✓ DONE')).toBe(true);
  });

  it('prioritises a pending radio readback over the checklist', () => {
    const session = new TrainingSession(MVP_CIRCUIT_SCENARIO);
    session.update(makeTestAircraftState());
    session.requestTakeoffClearance();

    const guidance = deriveGuidance(session);

    expect(guidance.target).toBe('radio');
    expect(guidance.title).toContain('ATC');
    expect(guidance.success).toContain('✓ readback');
  });

  it('points at the first cold-and-dark switch', () => {
    const session = new TrainingSession(COLD_AND_DARK_SCENARIO);
    session.update(makeTestAircraftState({ systems: coldAndDarkSystems() }));

    const guidance = deriveGuidance(session);

    expect(session.activeChecklistId).toBe('preflight');
    expect(guidance.controlId).toBe('system:battery');
    expect(guidance.target).toBe('systems');
  });

  it('moves from a verified battery to standby power one objective at a time', () => {
    const session = new TrainingSession(COLD_AND_DARK_SCENARIO);
    const systems = coldAndDarkSystems();
    systems.electrical.batterySwitchOn = true;
    systems.electrical.dcBusPowered = true;
    session.update(makeTestAircraftState({ systems }));
    session.answerChecklistItem('preflight');

    const guidance = deriveGuidance(session);

    expect(session.phaseId).toBe('power_on');
    expect(guidance.title).toContain('Standby power');
    expect(guidance.controlId).toBe('system:standby_power');
  });
});
