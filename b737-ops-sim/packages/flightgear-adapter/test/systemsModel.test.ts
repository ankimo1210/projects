import { describe, expect, it } from 'vitest';
import { MockSystemsModel } from '../src/mock/systemsModel.js';

/**
 * Systems model (M4 T2/T3/T4). Every assertion here is a procedure the crew
 * can get wrong: no APU start without DC power, no engine start without duct
 * pressure, no generator without a running engine.
 */

const GROUND = { onGround: true, dtSec: 1 / 60 };

/** Run the model forward in 1/60 s steps. */
function run(m: MockSystemsModel, seconds: number): void {
  for (let i = 0; i < Math.round(seconds * 60); i++) m.step(1 / 60, GROUND);
}

function coldAndDark(): MockSystemsModel {
  return new MockSystemsModel('cold_and_dark');
}

describe('electrical', () => {
  it('starts with nothing powered', () => {
    const m = coldAndDark();
    run(m, 1);
    expect(m.state.electrical.dcBusPowered).toBe(false);
    expect(m.state.electrical.acBus1Powered).toBe(false);
  });

  it('battery brings up the DC bus but no AC', () => {
    const m = coldAndDark();
    m.applySwitch('battery', true);
    run(m, 1);
    expect(m.state.electrical.dcBusPowered).toBe(true);
    expect(m.state.electrical.acBus1Powered).toBe(false);
    expect(m.state.annunciations.map((a) => a.id)).toContain('elec_no_ac');
  });

  it('external power feeds the AC buses on the ground', () => {
    const m = coldAndDark();
    m.applySwitch('battery', true);
    m.applySwitch('external_power', true);
    run(m, 1);
    expect(m.state.electrical.acBus1Powered).toBe(true);
  });

  it('refuses a generator while its engine is not running', () => {
    const m = coldAndDark();
    const res = m.applySwitch('gen1', true);
    expect(res.ok).toBe(false);
    expect(res.ok ? '' : res.error).toMatch(/engine 1/);
  });
});

describe('APU', () => {
  it('will not start without DC power', () => {
    const m = coldAndDark();
    m.applySwitch('apu_master', true);
    const res = m.applySwitch('apu_start', true);
    expect(res.ok).toBe(false);
    expect(res.ok ? '' : res.error).toMatch(/DC power/);
  });

  it('starts on the battery and offers its generator', () => {
    const m = coldAndDark();
    m.applySwitch('battery', true);
    m.applySwitch('apu_master', true);
    expect(m.applySwitch('apu_start', true).ok).toBe(true);
    run(m, 10);
    expect(m.state.apu.state).toBe('starting');
    expect(m.state.apu.n1Pct).toBeGreaterThan(20);
    run(m, 20);
    expect(m.state.apu.state).toBe('running');
    expect(m.state.apu.genAvailable).toBe(true);

    expect(m.applySwitch('apu_gen', true).ok).toBe(true);
    run(m, 1);
    expect(m.state.electrical.acBus1Powered).toBe(true);
    expect(m.state.annunciations.map((a) => a.id)).not.toContain('elec_no_ac');
  });

  it('shuts down when the master switch goes off', () => {
    const m = poweredWithApu();
    m.applySwitch('apu_master', false);
    run(m, 15);
    expect(m.state.apu.state).toBe('off');
    expect(m.state.electrical.acBus1Powered).toBe(false);
  });
});

describe('engine start', () => {
  it('refuses without duct pressure', () => {
    const m = poweredWithApu(); // APU running but bleed off
    const res = m.setEngineStart('left', 'ground');
    expect(res.ok).toBe(false);
    expect(res.ok ? '' : res.error).toMatch(/duct pressure/);
  });

  it('refuses the start lever without fuel pressure', () => {
    const m = poweredWithApu();
    const res = m.applySwitch('start_lever_left', true);
    expect(res.ok).toBe(false);
    expect(res.ok ? '' : res.error).toMatch(/fuel pressure/);
  });

  it('is starved by the packs on APU bleed alone', () => {
    const m = poweredWithApu();
    m.applySwitch('bleed_apu', true);
    m.applySwitch('pack_left', true);
    m.applySwitch('pack_right', true);
    run(m, 1);
    expect(m.state.pneumatic.ductPressurePsi).toBeLessThan(25);
    expect(m.setEngineStart('left', 'ground').ok).toBe(false);
  });

  it('runs the full start sequence and the selector springs back', () => {
    const m = readyToStart();
    expect(m.setEngineStart('left', 'ground').ok).toBe(true);
    run(m, 3);
    expect(m.state.engines.left.startValveOpen).toBe(true);
    expect(m.state.engines.left.n2Pct).toBeGreaterThan(5);

    // motoring only: no light-off until the start lever is raised
    run(m, 5);
    expect(m.state.engines.left.running).toBe(false);
    expect(m.state.engines.left.n2Pct).toBeLessThanOrEqual(31);

    expect(m.applySwitch('start_lever_left', true).ok).toBe(true);
    run(m, 10);
    const eng = m.state.engines.left;
    expect(eng.running).toBe(true);
    expect(eng.n2Pct).toBeGreaterThan(55);
    expect(eng.startMode).toBe('off'); // starter cut-out
    expect(eng.startValveOpen).toBe(false);
    expect(eng.oilPressurePsi).toBeGreaterThan(20);
  });

  it('flames out when the start lever is cut', () => {
    const m = enginesRunning();
    m.applySwitch('start_lever_left', false);
    run(m, 2);
    expect(m.state.engines.left.running).toBe(false);
    expect(m.state.engines.left.n2Pct).toBeLessThan(60);
  });
});

describe('hydraulics', () => {
  it('are unpressurised cold and dark and pressurise with an electric pump', () => {
    const m = poweredWithApu();
    expect(m.hydraulicsAvailable).toBe(false);
    m.applySwitch('hyd_pump_elec1', true);
    run(m, 6);
    expect(m.state.hydraulic.systemBPressurePsi).toBeGreaterThan(2500);
    expect(m.hydraulicsAvailable).toBe(true);
  });

  it('bleed down when the source goes away', () => {
    const m = poweredWithApu();
    m.applySwitch('hyd_pump_elec1', true);
    run(m, 6);
    m.applySwitch('hyd_pump_elec1', false);
    run(m, 8);
    expect(m.state.hydraulic.systemBPressurePsi).toBe(0);
    expect(m.hydraulicsAvailable).toBe(false);
  });
});

describe('IRS', () => {
  it('aligns over time and only with power', () => {
    const m = coldAndDark();
    m.applySwitch('irs_left', true);
    run(m, 5);
    expect(m.state.irs.leftState).toBe('off'); // no power, no alignment

    m.applySwitch('battery', true);
    m.applySwitch('irs_left', true);
    m.applySwitch('irs_right', true);
    run(m, 30);
    expect(m.state.irs.leftState).toBe('aligning');
    expect(m.state.irs.alignProgress).toBeGreaterThan(0.4);
    run(m, 35);
    expect(m.state.irs.leftState).toBe('aligned');
    expect(m.state.irs.rightState).toBe('aligned');
  });
});

describe('annunciations', () => {
  it('latch the master caution until it is reset, and re-arm when it returns', () => {
    const m = coldAndDark();
    m.applySwitch('battery', true);
    run(m, 1);
    expect(m.state.masterCaution).toBe(true);

    m.resetMasterCaution();
    run(m, 1);
    expect(m.state.masterCaution).toBe(false);
    // the condition is still displayed, just acknowledged
    expect(m.state.annunciations.map((a) => a.id)).toContain('elec_no_ac');

    // clear the condition, then cause it again: the light must come back
    m.applySwitch('external_power', true);
    run(m, 1);
    expect(m.state.annunciations.map((a) => a.id)).not.toContain('elec_no_ac');
    m.applySwitch('external_power', false);
    run(m, 1);
    expect(m.state.masterCaution).toBe(true);
  });

  it('warns about low oil pressure only on a running engine', () => {
    const m = enginesRunning();
    run(m, 1);
    expect(m.state.annunciations.some((a) => a.id.startsWith('oil_low'))).toBe(false);
    expect(m.state.masterWarning).toBe(false);
  });
});

// ---------------------------------------------------------------- fixtures

function poweredWithApu(): MockSystemsModel {
  const m = coldAndDark();
  m.applySwitch('battery', true);
  m.applySwitch('apu_master', true);
  m.applySwitch('apu_start', true);
  run(m, 30);
  m.applySwitch('apu_gen', true);
  run(m, 1);
  return m;
}

function readyToStart(): MockSystemsModel {
  const m = poweredWithApu();
  m.applySwitch('bleed_apu', true);
  m.applySwitch('fuel_pump_left', true);
  m.applySwitch('fuel_pump_right', true);
  run(m, 1);
  return m;
}

function enginesRunning(): MockSystemsModel {
  const m = new MockSystemsModel('running');
  run(m, 1);
  return m;
}
