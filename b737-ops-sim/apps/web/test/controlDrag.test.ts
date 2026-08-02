import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import type { AircraftCommand } from '@b737/shared';

/**
 * 3D lever drags (R-14). A pointer stream at display rate used to send one
 * command per pointermove; the bridge rate-limited most of them away and the
 * lever ended up short of where it was released.
 */

const sent: AircraftCommand[] = [];

vi.mock('../src/state/connection.js', () => ({
  sendCommand: (command: AircraftCommand) => sent.push(command),
  sendCommandWithSound: (command: AircraftCommand) => sent.push(command),
}));

vi.mock('../src/state/stores.js', () => ({
  useSimStore: {
    getState: () => ({ latest: makeTestAircraftState() }),
  },
}));

const { beginControlDrag, endControlDrag, updateControlDrag } =
  await import('../src/cockpit/controlActions.js');

describe('control drag coalescing', () => {
  beforeEach(() => {
    sent.length = 0;
    vi.useRealTimers();
  });

  it('collapses a pointer stream into ~20 Hz updates', () => {
    const session = beginControlDrag('throttle')!;
    expect(session).toBeDefined();
    for (let i = 1; i <= 120; i++) updateControlDrag(session, i);
    // 120 pointer samples in well under a second must not be 120 commands
    expect(sent.length).toBeLessThan(10);
  });

  it('always delivers the value the lever was released at', () => {
    const session = beginControlDrag('throttle')!;
    for (let i = 1; i <= 120; i++) updateControlDrag(session, i);
    endControlDrag();
    const last = sent.at(-1);
    expect(last?.type).toBe('set_throttle');
    // 120 px / 220 px-per-unit ≈ 0.545 from a start of 0
    expect(last?.type === 'set_throttle' ? last.valueNorm : 0).toBeCloseTo(120 / 220, 3);
  });

  it('releases exactly once — a repeated pointerup sends nothing more', () => {
    const session = beginControlDrag('speedbrake')!;
    updateControlDrag(session, 40);
    endControlDrag();
    const afterRelease = sent.length;
    expect(sent.at(-1)?.type).toBe('set_speedbrake');
    endControlDrag();
    expect(sent.length).toBe(afterRelease);
  });
});
