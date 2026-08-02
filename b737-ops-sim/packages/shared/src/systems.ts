import { z } from 'zod';

/**
 * Aircraft systems state (spec §22 Phase 4).
 *
 * NON_CERTIFIED_APPROXIMATION — the structure follows 737-class systems at the
 * depth a procedure trainer needs (what is powered, what is pressurised, what
 * is running) and deliberately stops short of load analysis, real pressures or
 * certified logic. Every value here is produced by a backend and consumed by
 * the UI/scenarios; nothing derives systems state locally.
 */

export const SWITCH_POSITIONS = ['off', 'on', 'auto'] as const;
export const SwitchPositionSchema = z.enum(SWITCH_POSITIONS);
export type SwitchPosition = (typeof SWITCH_POSITIONS)[number];

/** Overhead switches the crew can operate (spec §9 registry-driven). */
export const SYSTEM_SWITCHES = [
  'battery',
  'standby_power',
  'apu_master',
  'apu_start',
  'gen1',
  'gen2',
  'apu_gen',
  'external_power',
  'fuel_pump_left',
  'fuel_pump_right',
  'fuel_pump_center',
  'hyd_pump_eng1',
  'hyd_pump_eng2',
  'hyd_pump_elec1',
  'hyd_pump_elec2',
  'bleed_eng1',
  'bleed_eng2',
  'bleed_apu',
  'isolation_valve',
  'pack_left',
  'pack_right',
  'anti_ice_eng1',
  'anti_ice_eng2',
  'anti_ice_wing',
  'irs_left',
  'irs_right',
  'start_lever_left',
  'start_lever_right',
] as const;
export const SystemSwitchSchema = z.enum(SYSTEM_SWITCHES);
export type SystemSwitch = (typeof SYSTEM_SWITCHES)[number];

/** Engine start selector positions (737-style). */
export const ENGINE_START_MODES = ['off', 'ground', 'continuous', 'flight'] as const;
export const EngineStartModeSchema = z.enum(ENGINE_START_MODES);
export type EngineStartMode = (typeof ENGINE_START_MODES)[number];

export const ApuStateSchema = z.enum(['off', 'starting', 'running', 'shutting_down']);
export type ApuState = z.infer<typeof ApuStateSchema>;

export const IrsStateSchema = z.enum(['off', 'aligning', 'aligned', 'fault']);
export type IrsState = z.infer<typeof IrsStateSchema>;

export const AnnunciationSeveritySchema = z.enum(['advisory', 'caution', 'warning']);
export type AnnunciationSeverity = z.infer<typeof AnnunciationSeveritySchema>;

export const AnnunciationSchema = z.object({
  /** Stable id, e.g. "hyd_a_low_pressure". */
  id: z.string(),
  /** Text as it appears on the annunciator panel. */
  text: z.string(),
  severity: AnnunciationSeveritySchema,
});
export type Annunciation = z.infer<typeof AnnunciationSchema>;

export const EngineSystemsSchema = z.object({
  running: z.boolean(),
  n2Pct: z.number(),
  startValveOpen: z.boolean(),
  startMode: EngineStartModeSchema,
  oilPressurePsi: z.number(),
  /** Fuel is being introduced (start lever / cutoff open). */
  fuelValveOpen: z.boolean(),
});

export const SystemsStateSchema = z.object({
  electrical: z.object({
    batterySwitchOn: z.boolean(),
    standbyPowerOn: z.boolean(),
    externalPowerAvailable: z.boolean(),
    externalPowerOn: z.boolean(),
    apuGenOn: z.boolean(),
    gen1On: z.boolean(),
    gen2On: z.boolean(),
    /** DC battery bus — the first thing the battery switch brings up. */
    dcBusPowered: z.boolean(),
    /** AC transfer buses; most consumers need these. */
    acBus1Powered: z.boolean(),
    acBus2Powered: z.boolean(),
  }),
  apu: z.object({
    state: ApuStateSchema,
    n1Pct: z.number(),
    egtC: z.number(),
    bleedOn: z.boolean(),
    genAvailable: z.boolean(),
  }),
  pneumatic: z.object({
    ductPressurePsi: z.number(),
    bleed1On: z.boolean(),
    bleed2On: z.boolean(),
    isolationValveOpen: z.boolean(),
    packLeftOn: z.boolean(),
    packRightOn: z.boolean(),
  }),
  fuel: z.object({
    pumpLeftOn: z.boolean(),
    pumpRightOn: z.boolean(),
    pumpCenterOn: z.boolean(),
    /** Fuel is available at the engines (a pump running on a powered bus). */
    pressurised: z.boolean(),
    leftLb: z.number(),
    rightLb: z.number(),
    centerLb: z.number(),
  }),
  hydraulic: z.object({
    systemAPressurePsi: z.number(),
    systemBPressurePsi: z.number(),
    engPump1On: z.boolean(),
    engPump2On: z.boolean(),
    elecPump1On: z.boolean(),
    elecPump2On: z.boolean(),
  }),
  iceProtection: z.object({
    engine1On: z.boolean(),
    engine2On: z.boolean(),
    wingOn: z.boolean(),
  }),
  irs: z.object({
    leftState: IrsStateSchema,
    rightState: IrsStateSchema,
    /** 0..1 alignment progress of the slower unit. */
    alignProgress: z.number(),
  }),
  engines: z.object({ left: EngineSystemsSchema, right: EngineSystemsSchema }),
  annunciations: z.array(AnnunciationSchema),
  masterCaution: z.boolean(),
  masterWarning: z.boolean(),
});
export type SystemsState = z.infer<typeof SystemsStateSchema>;

// ------------------------------------------------------------ default states

/** Everything off: the aeroplane as it is found at the gate overnight. */
export function coldAndDarkSystems(): SystemsState {
  return {
    electrical: {
      batterySwitchOn: false,
      standbyPowerOn: false,
      externalPowerAvailable: true,
      externalPowerOn: false,
      apuGenOn: false,
      gen1On: false,
      gen2On: false,
      dcBusPowered: false,
      acBus1Powered: false,
      acBus2Powered: false,
    },
    apu: { state: 'off', n1Pct: 0, egtC: 15, bleedOn: false, genAvailable: false },
    pneumatic: {
      ductPressurePsi: 0,
      bleed1On: false,
      bleed2On: false,
      isolationValveOpen: true,
      packLeftOn: false,
      packRightOn: false,
    },
    fuel: {
      pumpLeftOn: false,
      pumpRightOn: false,
      pumpCenterOn: false,
      pressurised: false,
      leftLb: 8000,
      rightLb: 8000,
      centerLb: 0,
    },
    hydraulic: {
      systemAPressurePsi: 0,
      systemBPressurePsi: 0,
      engPump1On: false,
      engPump2On: false,
      elecPump1On: false,
      elecPump2On: false,
    },
    iceProtection: { engine1On: false, engine2On: false, wingOn: false },
    irs: { leftState: 'off', rightState: 'off', alignProgress: 0 },
    engines: {
      left: {
        running: false,
        n2Pct: 0,
        startValveOpen: false,
        startMode: 'off',
        oilPressurePsi: 0,
        fuelValveOpen: false,
      },
      right: {
        running: false,
        n2Pct: 0,
        startValveOpen: false,
        startMode: 'off',
        oilPressurePsi: 0,
        fuelValveOpen: false,
      },
    },
    annunciations: [],
    masterCaution: false,
    masterWarning: false,
  };
}

/**
 * Both engines running, buses powered, systems configured — the state every
 * scenario that does not start cold and dark begins in.
 */
export function enginesRunningSystems(): SystemsState {
  const s = coldAndDarkSystems();
  s.electrical = {
    ...s.electrical,
    batterySwitchOn: true,
    standbyPowerOn: true,
    externalPowerOn: false,
    gen1On: true,
    gen2On: true,
    dcBusPowered: true,
    acBus1Powered: true,
    acBus2Powered: true,
  };
  s.pneumatic = {
    ...s.pneumatic,
    bleed1On: true,
    bleed2On: true,
    packLeftOn: true,
    packRightOn: true,
    ductPressurePsi: 32,
  };
  s.fuel = { ...s.fuel, pumpLeftOn: true, pumpRightOn: true, pressurised: true };
  s.hydraulic = {
    ...s.hydraulic,
    engPump1On: true,
    engPump2On: true,
    systemAPressurePsi: 3000,
    systemBPressurePsi: 3000,
  };
  s.irs = { leftState: 'aligned', rightState: 'aligned', alignProgress: 1 };
  s.engines = {
    left: {
      running: true,
      n2Pct: 62,
      startValveOpen: false,
      startMode: 'off',
      oilPressurePsi: 45,
      fuelValveOpen: true,
    },
    right: {
      running: true,
      n2Pct: 62,
      startValveOpen: false,
      startMode: 'off',
      oilPressurePsi: 45,
      fuelValveOpen: true,
    },
  };
  return s;
}
