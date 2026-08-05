import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { validateImportedAssets } from '../src/convert.js';

const REQUIRED_FILES = [
  'Models/cockpit.ac',
  'Models/flightdesk.ac',
  'Models/pedestal.ac',
  'Models/pedals.ac',
  'Models/yoke/yoke.ac',
  'Models/Overhead/Overhead.ac',
  'Models/OH-panel/OH-panel.ac',
  'Models/Instruments/autopilot-panel.ac',
  'Models/seats/cockpitseat.ac',
  'Models/seats/cockpitseat2.ac',
  'Models/cockpit.xml',
  'Sounds/Wind.wav',
  'Sounds/FL2070/cfm11a.wav',
  'Sounds/FL2070/cfm14a.wav',
];

let fixtureDir: string | undefined;

function makeFixture(omit?: string): string {
  fixtureDir = mkdtempSync(join(tmpdir(), 'b737-assets-'));
  for (const path of REQUIRED_FILES) {
    if (path === omit) continue;
    const abs = join(fixtureDir, path);
    mkdirSync(dirname(abs), { recursive: true });
    writeFileSync(abs, 'fixture');
  }
  return fixtureDir;
}

afterEach(() => {
  if (fixtureDir) rmSync(fixtureDir, { recursive: true, force: true });
  fixtureDir = undefined;
});

describe('imported asset validation', () => {
  it('accepts the complete required input set', () => {
    expect(() => validateImportedAssets(makeFixture())).not.toThrow();
  });

  it('rejects a missing required model', () => {
    expect(() => validateImportedAssets(makeFixture('Models/cockpit.ac'))).toThrow(
      /required model\/binding missing.*Models\/cockpit\.ac/,
    );
  });

  it('rejects a missing required runtime sound', () => {
    expect(() => validateImportedAssets(makeFixture('Sounds/Wind.wav'))).toThrow(
      /required runtime sound missing.*Wind\.wav/,
    );
  });
});
