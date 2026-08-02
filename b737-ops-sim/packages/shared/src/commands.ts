import { z } from 'zod';
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
});
export type ScenarioInitialState = z.infer<typeof ScenarioInitialStateSchema>;
