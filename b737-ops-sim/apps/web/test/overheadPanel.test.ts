import { describe, expect, it } from 'vitest';
import { SYSTEM_SWITCHES } from '@b737/shared';
import { MISSING_PANEL_SWITCHES } from '../src/panels/OverheadPanel.js';

/**
 * The overhead panel is the only way to reach most systems (M4 T5): a switch
 * that exists in the schema but not on the panel is unreachable, which is how
 * four cockpit-registry meshes ended up dead in M2 (R-13 note).
 */
describe('overhead panel coverage', () => {
  it('offers every system switch the schema defines', () => {
    expect(MISSING_PANEL_SWITCHES).toEqual([]);
    expect(SYSTEM_SWITCHES.length).toBeGreaterThan(20);
  });
});
