import { z } from 'zod';

/**
 * Canonical aircraft state streamed bridge → browser.
 * Unit conventions are encoded in property names:
 *   Deg (degrees), Ft (feet), Kt (knots), Fpm (feet/min), Pct (0–100),
 *   Norm (0–1 or -1–1 where noted), Ms (unix millis), Sec (seconds).
 * All conversions from backend-native units happen inside the adapter
 * (spec §5: explicit unit boundaries).
 */

/** B737-800 flap lever detents (handle labels). */
export const FLAP_DETENTS = [0, 1, 2, 5, 10, 15, 25, 30, 40] as const;
export type FlapDetent = (typeof FLAP_DETENTS)[number];
export const FlapDetentSchema = z
  .number()
  .refine((v): v is FlapDetent => (FLAP_DETENTS as readonly number[]).includes(v), {
    message: 'not a valid 737-800 flap detent',
  });

/** Handle detent → normalized flap travel (0..1). Linear-by-index approximation. */
export function flapDetentToNorm(detent: FlapDetent): number {
  return FLAP_DETENTS.indexOf(detent) / (FLAP_DETENTS.length - 1);
}

/** Nearest handle detent for a normalized flap position. */
export function flapNormToNearestDetent(norm: number): FlapDetent {
  const idx = Math.round(norm * (FLAP_DETENTS.length - 1));
  return FLAP_DETENTS[Math.min(Math.max(idx, 0), FLAP_DETENTS.length - 1)] as FlapDetent;
}

export const AutobrakeSettingSchema = z.enum(['RTO', 'OFF', '1', '2', '3', 'MAX']);
export type AutobrakeSetting = z.infer<typeof AutobrakeSettingSchema>;

export const EngineStateSchema = z.object({
  n1Pct: z.number(),
  /** Forward-thrust lever position, 0..1. */
  throttleLeverNorm: z.number(),
  /** Reverse-thrust lever position, 0..1 (0 = stowed). */
  reverserNorm: z.number(),
});
export type EngineState = z.infer<typeof EngineStateSchema>;

export const AircraftStateSchema = z.object({
  /** Bridge wall-clock time when this sample was produced. */
  timestampMs: z.number(),
  /** Simulation elapsed time since scenario start. */
  simTimeSec: z.number(),

  position: z.object({
    latDeg: z.number(),
    lonDeg: z.number(),
    altitudeFtMsl: z.number(),
    /** Height above ground; clamped to >= 0. */
    radioAltitudeFt: z.number(),
  }),

  attitude: z.object({
    pitchDeg: z.number(),
    /** Positive = right wing down. */
    rollDeg: z.number(),
    headingDegMag: z.number(),
    groundTrackDegMag: z.number(),
    /** Angle of attack; null when the backend cannot provide it. */
    aoaDeg: z.number().nullable(),
  }),

  speeds: z.object({
    iasKt: z.number(),
    gsKt: z.number(),
    verticalSpeedFpm: z.number(),
  }),

  weightOnWheels: z.boolean(),

  engines: z.object({
    left: EngineStateSchema,
    right: EngineStateSchema,
  }),

  controls: z.object({
    flapHandleDetent: FlapDetentSchema,
    /** Actual surface position, 0..1 of full travel. */
    flapsActualNorm: z.number(),
    gearLeverDown: z.boolean(),
    /** 0 = up & stowed, 1 = down & locked, in-between = in transit. */
    gearPositionNorm: z.number(),
    /** Speed-brake lever, 0 = down, 1 = full up. */
    speedbrakeLeverNorm: z.number(),
    speedbrakeArmed: z.boolean(),
    /** Actual spoiler surface deployment 0..1. */
    spoilersDeployedNorm: z.number(),
    parkingBrakeSet: z.boolean(),
    /** Max of left/right pedal braking, 0..1. */
    brakeNorm: z.number(),
    autobrake: AutobrakeSettingSchema,
  }),

  mcp: z.object({
    selSpeedKt: z.number(),
    selHeadingDeg: z.number(),
    selAltitudeFt: z.number(),
    selVerticalSpeedFpm: z.number(),
    autopilotEngaged: z.boolean(),
    flightDirectorOn: z.boolean(),
  }),

  nav: z.object({
    ilsTuned: z.boolean(),
    /** Localizer deviation in dots; positive = fly right. Null when invalid. */
    locDeviationDots: z.number().nullable(),
    /** Glideslope deviation in dots; positive = fly up. Null when invalid. */
    gsDeviationDots: z.number().nullable(),
  }),

  lights: z.object({
    landing: z.boolean(),
    taxi: z.boolean(),
    strobe: z.boolean(),
    beacon: z.boolean(),
  }),

  airport: z.object({
    icao: z.string().nullable(),
    runwayId: z.string().nullable(),
  }),
});

export type AircraftState = z.infer<typeof AircraftStateSchema>;
