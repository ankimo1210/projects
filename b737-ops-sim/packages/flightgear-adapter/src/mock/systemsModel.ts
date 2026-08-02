import {
  clamp,
  coldAndDarkSystems,
  enginesRunningSystems,
  type Annunciation,
  type CommandResult,
  type EngineStartMode,
  type SystemsState,
  type SystemSwitch,
} from '@b737/shared';

/**
 * Deterministic 737-class systems model (spec §22 Phase 4).
 *
 * NON_CERTIFIED_APPROXIMATION — every timing, pressure and threshold below is
 * a plausible training value, not FCOM data. The model is a dependency graph
 * evaluated each physics step: sources power buses, buses drive pumps and
 * valves, and consumers ask whether they are powered or pressurised. Interlocks
 * (no start without duct pressure, no generator without a running engine) are
 * consequences of that graph rather than special cases.
 */

// --- electrical ---
const APU_START_SEC = 25;
const APU_SHUTDOWN_SEC = 12;
const APU_EGT_PEAK_C = 620;
const APU_EGT_RUN_C = 420;

// --- pneumatic ---
const APU_BLEED_PSI = 35;
const ENGINE_BLEED_PSI = 32;
/** A pack takes this much off the duct; two packs on APU bleed starve a start. */
const PACK_DEMAND_PSI = 8;
const ANTI_ICE_DEMAND_PSI = 3;
/** Minimum duct pressure that will motor a starter. */
const START_MIN_DUCT_PSI = 25;

// --- engine start ---
const STARTER_N2_LIMIT_PCT = 30;
const STARTER_N2_RATE_PCT_PER_SEC = 4.5;
const LIGHT_OFF_N2_PCT = 25;
const IDLE_N2_PCT = 62;
const SPOOL_N2_RATE_PCT_PER_SEC = 6;
/** Starter cut-out: the start valve closes and the selector springs back. */
const START_CUTOUT_N2_PCT = 56;
const RUNNING_N2_PCT = 50;
const N2_DECAY_PCT_PER_SEC = 8;

// --- hydraulic ---
const HYD_NOMINAL_PSI = 3000;
const HYD_RISE_PSI_PER_SEC = 900;
const HYD_DECAY_PSI_PER_SEC = 600;
/** Below this the surfaces the system drives stop moving (spec §22 D6). */
export const HYD_MIN_OPERATING_PSI = 1500;

// --- IRS ---
/**
 * Real alignment is several minutes; a training session cannot wait, so this
 * is compressed. Marked NON_CERTIFIED_APPROXIMATION in SYSTEMS_MODEL.md.
 */
const IRS_ALIGN_SEC = 60;

export type SystemsStartMode = 'cold_and_dark' | 'running';

export interface SystemsStepContext {
  onGround: boolean;
  /** Simulated time, used only for logging-free determinism checks. */
  dtSec: number;
}

export class MockSystemsModel {
  private s: SystemsState;
  private apuTimerSec = 0;
  private apuMasterOn = false;
  private apuStartRequested = false;
  /** Latched until the crew presses master caution/warning reset. */
  private acknowledgedIds = new Set<string>();
  /** Last known air/ground state, so switch interlocks see the real world. */
  private lastOnGround = true;

  constructor(mode: SystemsStartMode = 'running') {
    this.s = mode === 'running' ? enginesRunningSystems() : coldAndDarkSystems();
    this.apuMasterOn = false;
  }

  reset(mode: SystemsStartMode): void {
    this.s = mode === 'running' ? enginesRunningSystems() : coldAndDarkSystems();
    this.apuTimerSec = 0;
    this.apuMasterOn = false;
    this.apuStartRequested = false;
    this.acknowledgedIds.clear();
  }

  get state(): SystemsState {
    return this.s;
  }

  /** True when the surfaces driven by hydraulics can move (gear, flaps, spoilers). */
  get hydraulicsAvailable(): boolean {
    return (
      this.s.hydraulic.systemAPressurePsi >= HYD_MIN_OPERATING_PSI ||
      this.s.hydraulic.systemBPressurePsi >= HYD_MIN_OPERATING_PSI
    );
  }

  /** Either engine turning and burning. */
  engineRunning(engine: 'left' | 'right'): boolean {
    return this.s.engines[engine].running;
  }

  // ------------------------------------------------------------------ commands

  applySwitch(id: SystemSwitch, on: boolean): CommandResult {
    const result = this.applySwitchInner(id, on);
    // Buses, ducts and fuel pressure follow a switch immediately: the next
    // command must see the world the crew just created, not the one from the
    // previous physics tick.
    this.refreshInstantaneous();
    return result;
  }

  private refreshInstantaneous(): void {
    this.stepElectrical({ onGround: this.lastOnGround, dtSec: 0 });
    this.stepPneumatic();
    this.stepFuel();
  }

  private applySwitchInner(id: SystemSwitch, on: boolean): CommandResult {
    const e = this.s.electrical;
    switch (id) {
      case 'battery':
        e.batterySwitchOn = on;
        return { ok: true };
      case 'standby_power':
        e.standbyPowerOn = on;
        return { ok: true };
      case 'external_power':
        if (on && !e.externalPowerAvailable) {
          return { ok: false, error: 'external power is not available here' };
        }
        e.externalPowerOn = on;
        return { ok: true };
      case 'apu_master':
        this.apuMasterOn = on;
        if (!on) this.apuStartRequested = false;
        return { ok: true };
      case 'apu_start':
        if (on) {
          if (!this.apuMasterOn) return { ok: false, error: 'APU master switch is off' };
          if (!e.dcBusPowered) return { ok: false, error: 'no DC power for the APU starter' };
          if (this.s.apu.state === 'running') return { ok: false, error: 'APU is already running' };
          this.apuStartRequested = true;
        }
        return { ok: true };
      case 'apu_gen':
        if (on && !this.s.apu.genAvailable) return { ok: false, error: 'APU generator not ready' };
        e.apuGenOn = on;
        return { ok: true };
      case 'gen1':
        if (on && !this.s.engines.left.running)
          return { ok: false, error: 'engine 1 is not running' };
        e.gen1On = on;
        return { ok: true };
      case 'gen2':
        if (on && !this.s.engines.right.running) {
          return { ok: false, error: 'engine 2 is not running' };
        }
        e.gen2On = on;
        return { ok: true };
      case 'fuel_pump_left':
        this.s.fuel.pumpLeftOn = on;
        return { ok: true };
      case 'fuel_pump_right':
        this.s.fuel.pumpRightOn = on;
        return { ok: true };
      case 'fuel_pump_center':
        this.s.fuel.pumpCenterOn = on;
        return { ok: true };
      case 'hyd_pump_eng1':
        this.s.hydraulic.engPump1On = on;
        return { ok: true };
      case 'hyd_pump_eng2':
        this.s.hydraulic.engPump2On = on;
        return { ok: true };
      case 'hyd_pump_elec1':
        this.s.hydraulic.elecPump1On = on;
        return { ok: true };
      case 'hyd_pump_elec2':
        this.s.hydraulic.elecPump2On = on;
        return { ok: true };
      case 'bleed_eng1':
        this.s.pneumatic.bleed1On = on;
        return { ok: true };
      case 'bleed_eng2':
        this.s.pneumatic.bleed2On = on;
        return { ok: true };
      case 'bleed_apu':
        this.s.apu.bleedOn = on;
        return { ok: true };
      case 'isolation_valve':
        this.s.pneumatic.isolationValveOpen = on;
        return { ok: true };
      case 'pack_left':
        this.s.pneumatic.packLeftOn = on;
        return { ok: true };
      case 'pack_right':
        this.s.pneumatic.packRightOn = on;
        return { ok: true };
      case 'anti_ice_eng1':
        this.s.iceProtection.engine1On = on;
        return { ok: true };
      case 'anti_ice_eng2':
        this.s.iceProtection.engine2On = on;
        return { ok: true };
      case 'anti_ice_wing':
        this.s.iceProtection.wingOn = on;
        return { ok: true };
      case 'irs_left':
        this.s.irs.leftState = on
          ? this.s.irs.leftState === 'aligned'
            ? 'aligned'
            : 'aligning'
          : 'off';
        return { ok: true };
      case 'irs_right':
        this.s.irs.rightState = on
          ? this.s.irs.rightState === 'aligned'
            ? 'aligned'
            : 'aligning'
          : 'off';
        return { ok: true };
      case 'start_lever_left':
      case 'start_lever_right': {
        const engine = id === 'start_lever_left' ? 'left' : 'right';
        if (on && !this.s.fuel.pressurised) {
          return { ok: false, error: 'no fuel pressure — switch a fuel pump on first' };
        }
        this.s.engines[engine].fuelValveOpen = on;
        if (!on) this.s.engines[engine].running = false;
        return { ok: true };
      }
    }
  }

  setEngineStart(engine: 'left' | 'right', mode: EngineStartMode): CommandResult {
    this.refreshInstantaneous();
    const eng = this.s.engines[engine];
    if (mode === 'ground') {
      if (eng.running) return { ok: false, error: 'engine is already running' };
      if (this.s.pneumatic.ductPressurePsi < START_MIN_DUCT_PSI) {
        return {
          ok: false,
          error: 'not enough duct pressure to motor the starter (APU bleed on, packs off?)',
        };
      }
    }
    eng.startMode = mode;
    return { ok: true };
  }

  /**
   * Fail an engine (spec §22 Phase 5): the fuel valve shuts and the engine
   * spools down, exactly as if the crew had cut the start lever — so every
   * consequence (generator, hydraulics, bleed) follows the same graph.
   */
  failEngine(engine: 'left' | 'right'): void {
    const eng = this.s.engines[engine];
    eng.running = false;
    eng.fuelValveOpen = false;
    eng.startMode = 'off';
    eng.startValveOpen = false;
    this.refreshInstantaneous();
  }

  /** Master caution/warning recall: acknowledges everything currently active. */
  resetMasterCaution(): CommandResult {
    for (const a of this.s.annunciations) this.acknowledgedIds.add(a.id);
    this.s.masterCaution = false;
    this.s.masterWarning = false;
    return { ok: true };
  }

  // --------------------------------------------------------------------- step

  step(dt: number, ctx: SystemsStepContext): void {
    this.lastOnGround = ctx.onGround;
    this.stepElectrical(ctx);
    this.stepApu(dt);
    this.stepPneumatic();
    this.stepFuel();
    this.stepEngines(dt);
    this.stepHydraulic(dt);
    this.stepIrs(dt);
    // Electrical again: a generator that just came on line should power the
    // buses in the same tick the engine started.
    this.stepElectrical(ctx);
    this.stepAnnunciations(ctx);
  }

  private stepElectrical(ctx: SystemsStepContext): void {
    const e = this.s.electrical;
    e.dcBusPowered = e.batterySwitchOn || e.standbyPowerOn;
    const apuGen = e.apuGenOn && this.s.apu.state === 'running';
    const gen1 = e.gen1On && this.s.engines.left.running;
    const gen2 = e.gen2On && this.s.engines.right.running;
    const ext = e.externalPowerOn && e.externalPowerAvailable && ctx.onGround;
    // Simplification (documented): any AC source powers both transfer buses.
    const anyAc = apuGen || gen1 || gen2 || ext;
    e.acBus1Powered = anyAc;
    e.acBus2Powered = anyAc;
    if (!this.s.engines.left.running) e.gen1On = e.gen1On && false;
    if (!this.s.engines.right.running) e.gen2On = e.gen2On && false;
    if (this.s.apu.state !== 'running') e.apuGenOn = false;
  }

  private stepApu(dt: number): void {
    const apu = this.s.apu;
    switch (apu.state) {
      case 'off':
        if (this.apuStartRequested && this.apuMasterOn && this.s.electrical.dcBusPowered) {
          apu.state = 'starting';
          this.apuTimerSec = 0;
          this.apuStartRequested = false;
        } else {
          apu.n1Pct = Math.max(0, apu.n1Pct - 20 * dt);
          apu.egtC = Math.max(15, apu.egtC - 40 * dt);
        }
        break;
      case 'starting': {
        this.apuTimerSec += dt;
        const p = clamp(this.apuTimerSec / APU_START_SEC, 0, 1);
        apu.n1Pct = p * 100;
        // EGT peaks partway through the start, then settles.
        apu.egtC = 15 + APU_EGT_PEAK_C * Math.sin(Math.PI * Math.min(1, p * 0.9));
        if (!this.apuMasterOn) apu.state = 'shutting_down';
        else if (p >= 1) {
          apu.state = 'running';
          apu.egtC = APU_EGT_RUN_C;
        }
        break;
      }
      case 'running':
        apu.n1Pct = 100;
        apu.egtC = APU_EGT_RUN_C;
        if (!this.apuMasterOn) {
          apu.state = 'shutting_down';
          this.apuTimerSec = 0;
        }
        break;
      case 'shutting_down':
        this.apuTimerSec += dt;
        apu.n1Pct = Math.max(0, 100 * (1 - this.apuTimerSec / APU_SHUTDOWN_SEC));
        apu.egtC = Math.max(15, apu.egtC - 30 * dt);
        if (apu.n1Pct <= 0) apu.state = 'off';
        break;
    }
    apu.genAvailable = apu.state === 'running';
    if (apu.state !== 'running') apu.bleedOn = apu.bleedOn && false;
  }

  private stepPneumatic(): void {
    const p = this.s.pneumatic;
    const apuBleed = this.s.apu.bleedOn && this.s.apu.state === 'running' ? APU_BLEED_PSI : 0;
    const eng1Bleed = p.bleed1On && this.s.engines.left.running ? ENGINE_BLEED_PSI : 0;
    const eng2Bleed = p.bleed2On && this.s.engines.right.running ? ENGINE_BLEED_PSI : 0;
    let supply = Math.max(apuBleed, eng1Bleed, eng2Bleed);
    // Consumers take from the duct: this is why the packs must be off for an
    // APU-bleed engine start.
    if (p.packLeftOn) supply -= PACK_DEMAND_PSI;
    if (p.packRightOn) supply -= PACK_DEMAND_PSI;
    if (this.s.iceProtection.engine1On) supply -= ANTI_ICE_DEMAND_PSI;
    if (this.s.iceProtection.engine2On) supply -= ANTI_ICE_DEMAND_PSI;
    if (this.s.iceProtection.wingOn) supply -= ANTI_ICE_DEMAND_PSI * 2;
    p.ductPressurePsi = Math.max(0, supply);
  }

  private stepFuel(): void {
    const f = this.s.fuel;
    const acPowered = this.s.electrical.acBus1Powered || this.s.electrical.acBus2Powered;
    const anyPump =
      (f.pumpLeftOn && f.leftLb > 0) ||
      (f.pumpRightOn && f.rightLb > 0) ||
      (f.pumpCenterOn && f.centerLb > 0);
    f.pressurised = acPowered && anyPump;
    if (!f.pressurised) {
      // Suction feed keeps a running engine alive; it just is not "pressurised".
      return;
    }
  }

  private stepEngines(dt: number): void {
    for (const side of ['left', 'right'] as const) {
      const eng = this.s.engines[side];
      const canMotor =
        eng.startMode === 'ground' &&
        !eng.running &&
        this.s.pneumatic.ductPressurePsi >= START_MIN_DUCT_PSI;
      eng.startValveOpen = canMotor;

      // Starter cut-out is independent of whether the engine has lit: at
      // cut-out N2 the valve closes and the selector springs back to OFF.
      if (eng.startMode === 'ground' && eng.n2Pct >= START_CUTOUT_N2_PCT) {
        eng.startMode = 'off';
        eng.startValveOpen = false;
      }

      if (eng.running) {
        eng.n2Pct = Math.min(IDLE_N2_PCT, eng.n2Pct + SPOOL_N2_RATE_PCT_PER_SEC * dt);
        eng.oilPressurePsi = 45;
        if (!eng.fuelValveOpen) eng.running = false;
      } else if (canMotor) {
        const lightOff = eng.fuelValveOpen && eng.n2Pct >= LIGHT_OFF_N2_PCT;
        const limit = lightOff ? IDLE_N2_PCT : STARTER_N2_LIMIT_PCT;
        const rate = lightOff ? SPOOL_N2_RATE_PCT_PER_SEC : STARTER_N2_RATE_PCT_PER_SEC;
        eng.n2Pct = Math.min(limit, eng.n2Pct + rate * dt);
        eng.oilPressurePsi = eng.n2Pct * 0.5;
        if (eng.n2Pct >= RUNNING_N2_PCT && eng.fuelValveOpen) eng.running = true;
      } else if (eng.fuelValveOpen && eng.n2Pct >= LIGHT_OFF_N2_PCT) {
        // Lit off but the starter has cut out: the engine accelerates to idle
        // on its own.
        eng.n2Pct = Math.min(IDLE_N2_PCT, eng.n2Pct + SPOOL_N2_RATE_PCT_PER_SEC * dt);
        eng.oilPressurePsi = eng.n2Pct * 0.5;
        if (eng.n2Pct >= RUNNING_N2_PCT) eng.running = true;
      } else {
        eng.n2Pct = Math.max(0, eng.n2Pct - N2_DECAY_PCT_PER_SEC * dt);
        eng.oilPressurePsi = eng.n2Pct * 0.5;
      }
    }
  }

  private stepHydraulic(dt: number): void {
    const h = this.s.hydraulic;
    const ac = this.s.electrical.acBus1Powered || this.s.electrical.acBus2Powered;
    // System A: engine 1 pump + electric pump 2. System B: engine 2 + electric 1.
    const aSource = (h.engPump1On && this.s.engines.left.running) || (h.elecPump2On && ac);
    const bSource = (h.engPump2On && this.s.engines.right.running) || (h.elecPump1On && ac);
    h.systemAPressurePsi = rampTo(h.systemAPressurePsi, aSource ? HYD_NOMINAL_PSI : 0, dt);
    h.systemBPressurePsi = rampTo(h.systemBPressurePsi, bSource ? HYD_NOMINAL_PSI : 0, dt);
  }

  private stepIrs(dt: number): void {
    const irs = this.s.irs;
    const powered = this.s.electrical.dcBusPowered;
    for (const side of ['leftState', 'rightState'] as const) {
      if (irs[side] === 'aligning' && !powered) irs[side] = 'off';
    }
    const aligning = irs.leftState === 'aligning' || irs.rightState === 'aligning';
    if (aligning && powered) {
      irs.alignProgress = clamp(irs.alignProgress + dt / IRS_ALIGN_SEC, 0, 1);
      if (irs.alignProgress >= 1) {
        if (irs.leftState === 'aligning') irs.leftState = 'aligned';
        if (irs.rightState === 'aligning') irs.rightState = 'aligned';
      }
    } else if (irs.leftState === 'off' && irs.rightState === 'off') {
      irs.alignProgress = 0;
    }
  }

  /**
   * Annunciations are derived from state every tick (D5) — nothing is stored
   * except which ones the crew has already acknowledged.
   */
  private stepAnnunciations(ctx: SystemsStepContext): void {
    const a: Annunciation[] = [];
    const e = this.s.electrical;
    const anyEngineRunning = this.s.engines.left.running || this.s.engines.right.running;

    if (!e.acBus1Powered && !e.acBus2Powered && e.dcBusPowered) {
      a.push({ id: 'elec_no_ac', text: 'NO AC POWER', severity: 'caution' });
    }
    if (anyEngineRunning && !e.gen1On && this.s.engines.left.running) {
      a.push({ id: 'gen1_off_bus', text: 'GEN 1 OFF BUS', severity: 'caution' });
    }
    if (anyEngineRunning && !e.gen2On && this.s.engines.right.running) {
      a.push({ id: 'gen2_off_bus', text: 'GEN 2 OFF BUS', severity: 'caution' });
    }
    if (anyEngineRunning && !this.s.fuel.pressurised) {
      a.push({ id: 'fuel_low_pressure', text: 'FUEL LOW PRESSURE', severity: 'caution' });
    }
    if (anyEngineRunning && this.s.hydraulic.systemAPressurePsi < HYD_MIN_OPERATING_PSI) {
      a.push({ id: 'hyd_a_low', text: 'HYD SYS A LOW PRESSURE', severity: 'caution' });
    }
    if (anyEngineRunning && this.s.hydraulic.systemBPressurePsi < HYD_MIN_OPERATING_PSI) {
      a.push({ id: 'hyd_b_low', text: 'HYD SYS B LOW PRESSURE', severity: 'caution' });
    }
    for (const side of ['left', 'right'] as const) {
      const eng = this.s.engines[side];
      if (eng.running && eng.oilPressurePsi < 20) {
        a.push({
          id: `oil_low_${side}`,
          text: `ENG ${side === 'left' ? 1 : 2} LOW OIL PRESSURE`,
          severity: 'warning',
        });
      }
      if (eng.startValveOpen && eng.n2Pct > START_CUTOUT_N2_PCT) {
        a.push({
          id: `start_valve_${side}`,
          text: `ENG ${side === 'left' ? 1 : 2} START VALVE OPEN`,
          severity: 'caution',
        });
      }
    }
    if (this.s.irs.leftState === 'aligning' || this.s.irs.rightState === 'aligning') {
      a.push({ id: 'irs_align', text: 'IRS ALIGN', severity: 'advisory' });
    }
    if (!ctx.onGround && (this.s.irs.leftState === 'off' || this.s.irs.rightState === 'off')) {
      a.push({ id: 'irs_off', text: 'IRS OFF', severity: 'caution' });
    }

    this.s.annunciations = a;
    // A new, unacknowledged item lights the master caution/warning.
    const unacked = a.filter((x) => !this.acknowledgedIds.has(x.id));
    this.s.masterCaution = unacked.some((x) => x.severity === 'caution');
    this.s.masterWarning = unacked.some((x) => x.severity === 'warning');
    // Forget acknowledgements once the condition clears, so it can light again.
    for (const id of [...this.acknowledgedIds]) {
      if (!a.some((x) => x.id === id)) this.acknowledgedIds.delete(id);
    }
  }
}

function rampTo(current: number, target: number, dt: number): number {
  if (current < target) return Math.min(target, current + HYD_RISE_PSI_PER_SEC * dt);
  return Math.max(target, current - HYD_DECAY_PSI_PER_SEC * dt);
}
