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
