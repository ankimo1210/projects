import type { AircraftState } from './aircraftState.js';

/** A structurally complete, mutable state sample for tests. */
export function makeTestAircraftState(overrides: Partial<AircraftState> = {}): AircraftState {
  const base: AircraftState = {
    timestampMs: 1_700_000_000_000,
    simTimeSec: 0,
    position: { latDeg: 37.6132, lonDeg: -122.3572, altitudeFtMsl: 13, radioAltitudeFt: 0 },
    attitude: {
      pitchDeg: 0,
      rollDeg: 0,
      headingDegMag: 284.4,
      groundTrackDegMag: 284.4,
      aoaDeg: null,
    },
    speeds: { iasKt: 0, gsKt: 0, verticalSpeedFpm: 0 },
    weightOnWheels: true,
    engines: {
      left: { n1Pct: 22, throttleLeverNorm: 0, reverserNorm: 0 },
      right: { n1Pct: 22, throttleLeverNorm: 0, reverserNorm: 0 },
    },
    controls: {
      flapHandleDetent: 5,
      flapsActualNorm: 3 / 8,
      gearLeverDown: true,
      gearPositionNorm: 1,
      speedbrakeLeverNorm: 0,
      speedbrakeArmed: false,
      spoilersDeployedNorm: 0,
      parkingBrakeSet: true,
      brakeNorm: 0,
      autobrake: 'OFF',
    },
    mcp: {
      selSpeedKt: 150,
      selHeadingDeg: 284,
      selAltitudeFt: 3000,
      selVerticalSpeedFpm: 0,
      autopilotEngaged: false,
      flightDirectorOn: true,
      approachArmed: false,
      rollMode: null,
      pitchMode: null,
    },
    nav: { ilsTuned: true, locDeviationDots: null, gsDeviationDots: null },
    lights: { landing: false, taxi: false, strobe: false, beacon: true },
    airport: { icao: 'KSFO', runwayId: '28R' },
  };
  return { ...base, ...overrides };
}
