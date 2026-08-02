/**
 * Runway / ILS reference data used by the mock backend, scenario engine and
 * the 3D world.
 *
 * NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED
 * Values below are plausible approximations of published data, adequate for a
 * self-consistent simulation datum. They are NOT navigation data. In
 * FlightGear mode, position/ILS deviations come from FlightGear itself; this
 * datum is only the mock-mode world reference and scenario geometry source.
 */

import { fromLocalEnuM, toLocalEnuM } from './geo.js';
import { degToRad, FT_TO_M } from './units.js';

export interface RunwayData {
  airportIcao: string;
  runwayId: string;
  /** Landing/takeoff threshold (the end you cross first on approach). */
  thresholdLatDeg: number;
  thresholdLonDeg: number;
  headingDegTrue: number;
  headingDegMag: number;
  /** Magnetic variation, east positive. mag = true - variation. */
  magneticVariationDeg: number;
  lengthFt: number;
  widthFt: number;
  elevationFtMsl: number;
  ils: {
    freqMhz: number;
    glideslopeDeg: number;
    thresholdCrossingHeightFt: number;
    /** Full-scale localizer deflection (2 dots), degrees off centerline. */
    locFullScaleDeg: number;
    /** Full-scale glideslope deflection (2 dots), degrees off glidepath. */
    gsFullScaleDeg: number;
  };
}

/** KSFO 28R — FlightGear's default airport, shared by both backends. */
export const KSFO_28R: RunwayData = {
  airportIcao: 'KSFO',
  runwayId: '28R',
  thresholdLatDeg: 37.6132,
  thresholdLonDeg: -122.3572,
  headingDegTrue: 297.9,
  headingDegMag: 284.4,
  magneticVariationDeg: 13.5,
  lengthFt: 11870,
  widthFt: 200,
  elevationFtMsl: 13,
  ils: {
    freqMhz: 111.7,
    glideslopeDeg: 3.0,
    thresholdCrossingHeightFt: 55,
    locFullScaleDeg: 2.5,
    gsFullScaleDeg: 0.7,
  },
};

export const RUNWAYS: Record<string, RunwayData> = {
  'KSFO/28R': KSFO_28R,
};

export function getRunway(airportIcao: string, runwayId: string): RunwayData | undefined {
  return RUNWAYS[`${airportIcao}/${runwayId}`];
}

// ------------------------------------------------------------- runway geometry

/** Position expressed in the runway's own frame. */
export interface RunwayPosition {
  /** Metres along the centerline from the threshold; + = toward the far end. */
  alongM: number;
  /** Metres from the centerline; + = right of the landing direction. */
  crossM: number;
  /** Inside the paved surface (threshold..far end, within half the width). */
  onSurface: boolean;
}

/**
 * Runway-frame coordinates of a geodetic position. Scenario logic (runway
 * entry, exit, incursion) must be geometric — "slow and on the ground" is not
 * the same thing as "clear of the runway" (R-08).
 */
export function runwayPosition(runway: RunwayData, latDeg: number, lonDeg: number): RunwayPosition {
  const { eastM, northM } = toLocalEnuM(
    runway.thresholdLatDeg,
    runway.thresholdLonDeg,
    latDeg,
    lonDeg,
  );
  const hdgRad = degToRad(runway.headingDegTrue);
  // Runway axis unit vector in ENU is (sin h, cos h); the cross axis is its
  // right-hand normal (cos h, -sin h).
  const alongM = eastM * Math.sin(hdgRad) + northM * Math.cos(hdgRad);
  const crossM = eastM * Math.cos(hdgRad) - northM * Math.sin(hdgRad);
  const lengthM = runway.lengthFt * FT_TO_M;
  const halfWidthM = (runway.widthFt * FT_TO_M) / 2;
  const onSurface =
    alongM >= -RUNWAY_END_MARGIN_M &&
    alongM <= lengthM + RUNWAY_END_MARGIN_M &&
    Math.abs(crossM) <= halfWidthM;
  return { alongM, crossM, onSurface };
}

/** Displaced-threshold/overrun tolerance treated as "still on the runway". */
const RUNWAY_END_MARGIN_M = 30;

/** Inverse of {@link runwayPosition} — authoring ground layouts in runway coordinates. */
export function runwayPointToLatLon(
  runway: RunwayData,
  alongM: number,
  crossM: number,
): { latDeg: number; lonDeg: number } {
  const hdgRad = degToRad(runway.headingDegTrue);
  const eastM = alongM * Math.sin(hdgRad) + crossM * Math.cos(hdgRad);
  const northM = alongM * Math.cos(hdgRad) - crossM * Math.sin(hdgRad);
  return fromLocalEnuM(runway.thresholdLatDeg, runway.thresholdLonDeg, eastM, northM);
}

/**
 * Lateral distance from the centerline at which a runway holding position sits.
 * NON_CERTIFIED_APPROXIMATION — representative of an ICAO code-E holding
 * position, not surveyed data.
 */
export const HOLD_SHORT_OFFSET_M = 45;

/**
 * Signed distance to the runway's holding position: positive = still short of
 * it, negative = inside the protected area. Only meaningful abeam the runway.
 */
export function distanceToHoldShortM(pos: RunwayPosition): number {
  return Math.abs(pos.crossM) - HOLD_SHORT_OFFSET_M;
}

/** Inside the runway protected area (past the holding position). */
export function isPastHoldShort(runway: RunwayData, pos: RunwayPosition): boolean {
  const lengthM = runway.lengthFt * FT_TO_M;
  const abeam = pos.alongM > -RUNWAY_END_MARGIN_M && pos.alongM < lengthM + RUNWAY_END_MARGIN_M;
  return abeam && distanceToHoldShortM(pos) < 0;
}
