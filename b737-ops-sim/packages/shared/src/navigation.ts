import { z } from 'zod';
import { bearingDeg, distanceM, toLocalEnuM } from './geo.js';
import { KSFO_28R, runwayPointToLatLon } from './airports.js';
import { degToRad, normalizeDeg360, NM_TO_M } from './units.js';

/**
 * Navigation data and route model (spec §22 Phase 5).
 *
 * NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED. The waypoints and procedures
 * below are invented around the KSFO 28R datum so a route can be flown in the
 * mock world. They share names with nothing real and MUST NOT be used for
 * navigation. In FlightGear mode the scenery and navaids are FlightGear's;
 * this data drives the trainer's own route logic.
 */

export const WaypointSchema = z.object({
  id: z.string(),
  latDeg: z.number(),
  lonDeg: z.number(),
  /** Altitude constraint in feet MSL, null when the leg has none. */
  altitudeFt: z.number().nullable(),
  /** Speed constraint in knots, null when the leg has none. */
  speedKt: z.number().nullable(),
});
export type Waypoint = z.infer<typeof WaypointSchema>;

export const RouteLegSchema = z.object({
  waypoint: WaypointSchema,
  /** Great-circle course from the previous fix, degrees true. */
  courseDegTrue: z.number(),
  /** Leg length in nautical miles. */
  distanceNm: z.number(),
});
export type RouteLeg = z.infer<typeof RouteLegSchema>;

export const ProcedureKindSchema = z.enum(['sid', 'star', 'approach_transition']);
export type ProcedureKind = z.infer<typeof ProcedureKindSchema>;

export interface Procedure {
  id: string;
  kind: ProcedureKind;
  runwayId: string;
  /** Fix ids, in order. */
  waypointIds: string[];
  description: string;
}

/** Author a fix in runway coordinates so it lines up with the runway datum. */
function fix(
  id: string,
  alongNm: number,
  crossNm: number,
  altitudeFt: number | null = null,
  speedKt: number | null = null,
): Waypoint {
  const p = runwayPointToLatLon(KSFO_28R, alongNm * NM_TO_M, crossNm * NM_TO_M);
  return { id, latDeg: p.latDeg, lonDeg: p.lonDeg, altitudeFt, speedKt };
}

/**
 * Fixes for the trainer's own departure and arrival. `along` is measured from
 * the 28R threshold along the runway course, `cross` to the right of it.
 */
export const WAYPOINTS: Record<string, Waypoint> = Object.fromEntries(
  [
    // --- departure (straight ahead, then a right turn out over the bay) ---
    fix('SFOUT', 4, 0, 2000, 210),
    fix('BAYNE', 8, 5, 4000, 250),
    fix('WESTB', 10, 14, 6000, null),
    // --- arrival: south-east, then a base leg back onto the ILS ---
    fix('SOUTA', -2, 16, 5000, 250),
    fix('MIDBA', -8, 10, 3000, 210),
    fix('FINAL', -12, 0, 2000, 180),
    // --- final approach fix, on the localizer ---
    fix('FAFXX', -6, 0, 1900, 160),
  ].map((w) => [w.id, w]),
);

export const PROCEDURES: Procedure[] = [
  {
    id: 'SFOUT1',
    kind: 'sid',
    runwayId: '28R',
    waypointIds: ['SFOUT', 'BAYNE', 'WESTB'],
    description: 'Runway 28R departure: runway heading to SFOUT, then right toward the bay.',
  },
  {
    id: 'BAYIN1',
    kind: 'star',
    runwayId: '28R',
    waypointIds: ['SOUTA', 'MIDBA', 'FINAL'],
    description: 'Arrival from the south-east onto the 28R final approach course.',
  },
  {
    id: 'ILS28R',
    kind: 'approach_transition',
    runwayId: '28R',
    waypointIds: ['FAFXX'],
    description: 'Final approach fix for the ILS 28R.',
  },
];

export function getProcedure(id: string): Procedure | undefined {
  return PROCEDURES.find((p) => p.id === id);
}

export function getWaypoint(id: string): Waypoint | undefined {
  return WAYPOINTS[id];
}

/**
 * Build a leg list from an ordered fix list, starting at a position (usually
 * the departure runway). Courses and distances are computed, not authored.
 */
export function buildRoute(
  fromLatDeg: number,
  fromLonDeg: number,
  waypointIds: string[],
): RouteLeg[] {
  const legs: RouteLeg[] = [];
  let prevLat = fromLatDeg;
  let prevLon = fromLonDeg;
  for (const id of waypointIds) {
    const wp = WAYPOINTS[id];
    if (!wp) continue;
    legs.push({
      waypoint: wp,
      courseDegTrue: bearingDeg(prevLat, prevLon, wp.latDeg, wp.lonDeg),
      distanceNm: distanceM(prevLat, prevLon, wp.latDeg, wp.lonDeg) / NM_TO_M,
    });
    prevLat = wp.latDeg;
    prevLon = wp.lonDeg;
  }
  return legs;
}

/** Where the aircraft is relative to the active leg. */
export interface LegTracking {
  /** Nautical miles to the active waypoint. */
  distanceToWaypointNm: number;
  /** Cross-track error in NM; positive = right of course. */
  crossTrackNm: number;
  /** Course to steer to regain and follow the leg, degrees true. */
  desiredTrackDegTrue: number;
  /** The waypoint is behind the aircraft: sequence to the next leg. */
  sequenced: boolean;
}

/** Maximum intercept angle when regaining the course. */
const MAX_INTERCEPT_DEG = 35;
/** Cross-track error that commands the full intercept angle. */
const FULL_INTERCEPT_NM = 1.5;

/**
 * Track the active leg. `previous` is the leg start (the last fix, or the
 * departure point for the first leg).
 */
export function trackLeg(
  leg: RouteLeg,
  previous: { latDeg: number; lonDeg: number },
  aircraft: { latDeg: number; lonDeg: number },
): LegTracking {
  const wp = leg.waypoint;
  const distanceToWaypointNm =
    distanceM(aircraft.latDeg, aircraft.lonDeg, wp.latDeg, wp.lonDeg) / NM_TO_M;

  // Cross-track from the leg's great-circle approximated in a local ENU frame.
  const a = toLocalEnuM(previous.latDeg, previous.lonDeg, aircraft.latDeg, aircraft.lonDeg);
  const b = toLocalEnuM(previous.latDeg, previous.lonDeg, wp.latDeg, wp.lonDeg);
  const legLen = Math.hypot(b.eastM, b.northM);
  const ux = legLen > 0 ? b.eastM / legLen : 0;
  const uy = legLen > 0 ? b.northM / legLen : 0;
  const alongM = a.eastM * ux + a.northM * uy;
  // Right of course is the leg direction rotated -90°: (uy, -ux).
  const crossM = a.eastM * uy - a.northM * ux;
  const crossTrackNm = crossM / NM_TO_M;

  const interceptDeg =
    -Math.sign(crossTrackNm) *
    Math.min(MAX_INTERCEPT_DEG, (Math.abs(crossTrackNm) / FULL_INTERCEPT_NM) * MAX_INTERCEPT_DEG);
  return {
    distanceToWaypointNm,
    crossTrackNm,
    desiredTrackDegTrue: normalizeDeg360(leg.courseDegTrue + interceptDeg),
    // Sequence when the aircraft has passed abeam the fix.
    sequenced: alongM > legLen || distanceToWaypointNm < WAYPOINT_SEQUENCE_NM,
  };
}

/** Distance at which a fix counts as reached. */
export const WAYPOINT_SEQUENCE_NM = 0.6;

/** Great-circle course between two fixes, for display. */
export function courseBetween(a: Waypoint, b: Waypoint): number {
  return normalizeDeg360(bearingDeg(a.latDeg, a.lonDeg, b.latDeg, b.lonDeg));
}

/** Wind triangle: the heading that makes good a desired track. */
export function headingForTrack(
  desiredTrackDegTrue: number,
  trueAirspeedKt: number,
  windFromDegTrue: number,
  windSpeedKt: number,
): number {
  if (trueAirspeedKt <= 1) return desiredTrackDegTrue;
  const windToRad = degToRad(normalizeDeg360(windFromDegTrue + 180));
  const trackRad = degToRad(desiredTrackDegTrue);
  // Component of the wind perpendicular to the desired track.
  const crossWind = windSpeedKt * Math.sin(windToRad - trackRad);
  const wcaDeg =
    (Math.asin(Math.max(-1, Math.min(1, -crossWind / trueAirspeedKt))) * 180) / Math.PI;
  return normalizeDeg360(desiredTrackDegTrue + wcaDeg);
}

export const FmsStateSchema = z.object({
  /** Loaded route id, null when no route is loaded. */
  routeId: z.string().nullable(),
  legs: z.array(RouteLegSchema),
  activeLegIndex: z.number().int(),
  /** LNAV selected on the MCP. */
  lnavArmed: z.boolean(),
  distanceToWaypointNm: z.number().nullable(),
  crossTrackNm: z.number().nullable(),
  desiredTrackDegTrue: z.number().nullable(),
});
export type FmsState = z.infer<typeof FmsStateSchema>;

export function emptyFmsState(): FmsState {
  return {
    routeId: null,
    legs: [],
    activeLegIndex: 0,
    lnavArmed: false,
    distanceToWaypointNm: null,
    crossTrackNm: null,
    desiredTrackDegTrue: null,
  };
}
