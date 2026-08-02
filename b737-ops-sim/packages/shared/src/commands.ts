import { z } from 'zod';
import { EngineStartModeSchema, FailureKindSchema, SystemSwitchSchema } from './systems.js';
import { AutobrakeSettingSchema, FlapDetentSchema } from './aircraftState.js';

/**
 * Typed control commands browser → bridge → backend (spec §5).
 * The bridge validates every command against these schemas before it may
 * reach a backend; the browser never talks to FlightGear directly.
 */

const norm01 = z.number().min(0).max(1);
const normPm1 = z.number().min(-1).max(1);

export const AircraftCommandSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('set_control_axis'),
    axis: z.enum(['pitch', 'roll', 'yaw']),
    /** -1..1; pitch +1 = full aft (nose up), roll +1 = right, yaw +1 = right. */
    valueNorm: normPm1,
  }),
  z.object({ type: z.literal('set_throttle'), valueNorm: norm01 }),
  z.object({ type: z.literal('set_brakes'), valueNorm: norm01 }),
  z.object({ type: z.literal('set_parking_brake'), engaged: z.boolean() }),
  z.object({ type: z.literal('set_flaps'), detent: FlapDetentSchema }),
  z.object({ type: z.literal('set_gear'), down: z.boolean() }),
  z.object({ type: z.literal('set_speedbrake'), leverNorm: norm01 }),
  z.object({ type: z.literal('set_speedbrake_armed'), armed: z.boolean() }),
  z.object({ type: z.literal('set_reverse_thrust'), leverNorm: norm01 }),
  z.object({ type: z.literal('set_autobrake'), setting: AutobrakeSettingSchema }),
  z.object({ type: z.literal('set_mcp_speed'), speedKt: z.number().min(100).max(340) }),
  z.object({ type: z.literal('set_mcp_heading'), headingDeg: z.number().min(0).max(360) }),
  z.object({ type: z.literal('set_mcp_altitude'), altitudeFt: z.number().min(0).max(41000) }),
  z.object({
    type: z.literal('set_mcp_vertical_speed'),
    verticalSpeedFpm: z.number().min(-8000).max(8000),
  }),
  z.object({ type: z.literal('set_autopilot'), engaged: z.boolean() }),
  z.object({ type: z.literal('set_flight_director'), on: z.boolean() }),
  /** Arm the approach: the autopilot captures LOC then G/S on its own. */
  z.object({ type: z.literal('set_ap_approach_mode'), armed: z.boolean() }),
  /** Take-off / go-around: go-around thrust and pitch, autopilot disengaged. */
  z.object({ type: z.literal('set_toga'), engaged: z.boolean() }),
  /** Overhead-panel switch (spec §22 Phase 4); ids listed in systems.ts. */
  z.object({
    type: z.literal('set_system_switch'),
    switch: SystemSwitchSchema,
    on: z.boolean(),
  }),
  z.object({
    type: z.literal('set_engine_start'),
    engine: z.enum(['left', 'right']),
    mode: EngineStartModeSchema,
  }),
  /** Master caution / warning recall. */
  z.object({ type: z.literal('reset_master_caution') }),
  /** Load a route (spec §22 Phase 5). Procedure ids come from navigation.ts. */
  z.object({
    type: z.literal('load_route'),
    sidId: z.string().nullable(),
    starId: z.string().nullable(),
    approachId: z.string().nullable(),
  }),
  z.object({ type: z.literal('direct_to'), waypointId: z.string() }),
  z.object({ type: z.literal('set_lnav'), armed: z.boolean() }),
  /** Inject a failure — used by scenarios and by the instructor. */
  z.object({ type: z.literal('inject_failure'), failure: FailureKindSchema }),
  z.object({ type: z.literal('clear_failures') }),
  z.object({
    type: z.literal('set_light'),
    light: z.enum(['landing', 'taxi', 'strobe', 'beacon']),
    on: z.boolean(),
  }),
]);

export type AircraftCommand = z.infer<typeof AircraftCommandSchema>;
export type AircraftCommandType = AircraftCommand['type'];

export const CommandResultSchema = z.discriminatedUnion('ok', [
  z.object({ ok: z.literal(true) }),
  z.object({ ok: z.literal(false), error: z.string() }),
]);
export type CommandResult = z.infer<typeof CommandResultSchema>;

/** Initial conditions a backend must honor on scenario (re)start. */
export const ScenarioInitialStateSchema = z.object({
  /** Seed for all stochastic elements — fixed seed ⇒ reproducible session. */
  seed: z.number().int(),
  airportIcao: z.string(),
  runwayId: z.string(),
  /**
   * `stand` starts parked on the ramp (taxi scenarios), `holding_point` short
   * of the runway, `threshold` lined up, `final_approach` established inbound.
   */
  startAt: z.enum(['stand', 'holding_point', 'threshold', 'final_approach']),
  flapDetent: FlapDetentSchema,
  parkingBrakeSet: z.boolean(),
  /** NON_CERTIFIED_APPROXIMATION: default MVP weight 145,000 lb. */
  grossWeightLb: z.number().min(90000).max(174000),
  windDirDeg: z.number().min(0).max(360),
  windSpeedKt: z.number().min(0).max(40),
  /** Start with every system off (spec §22 Phase 4). Only valid at a stand. */
  coldAndDark: z.boolean().optional(),
  /** Weather beyond the surface wind (spec §22 Phase 5). */
  weather: z
    .object({
      /** Wind at 3,000 ft and above; the surface wind is interpolated below. */
      windAloftDirDeg: z.number().min(0).max(360),
      windAloftSpeedKt: z.number().min(0).max(120),
      /** Peak gust above the steady wind, in knots. */
      gustKt: z.number().min(0).max(40),
      visibilityM: z.number().min(50).max(20000),
      /** 0..1; perturbs attitude and airspeed, seeded so runs reproduce. */
      turbulence: z.number().min(0).max(1),
    })
    .optional(),
  /** Failures armed at scenario start (spec §22 Phase 5). */
  failures: z.array(FailureKindSchema).optional(),
});
export type ScenarioInitialState = z.infer<typeof ScenarioInitialStateSchema>;
