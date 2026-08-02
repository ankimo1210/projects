import { describe, expect, it } from 'vitest';
import {
  KSFO_28R,
  PROCEDURES,
  WAYPOINTS,
  buildRoute,
  getProcedure,
  headingForTrack,
  runwayPointToLatLon,
  trackLeg,
} from '../src/index.js';

/** Route model (M5 T1): courses, cross-track sign and sequencing. */

const from = { latDeg: KSFO_28R.thresholdLatDeg, lonDeg: KSFO_28R.thresholdLonDeg };

describe('procedures', () => {
  it('reference waypoints that exist', () => {
    for (const proc of PROCEDURES) {
      for (const id of proc.waypointIds) {
        expect(WAYPOINTS[id], `${proc.id} references unknown ${id}`).toBeDefined();
      }
    }
  });

  it('resolves a SID and a STAR for 28R', () => {
    expect(getProcedure('SFOUT1')?.kind).toBe('sid');
    expect(getProcedure('BAYIN1')?.kind).toBe('star');
    expect(getProcedure('NOPE')).toBeUndefined();
  });
});

describe('buildRoute', () => {
  it('computes courses and distances between fixes', () => {
    const legs = buildRoute(from.latDeg, from.lonDeg, ['SFOUT', 'BAYNE', 'WESTB']);
    expect(legs).toHaveLength(3);
    // the first leg runs straight out along the runway course
    expect(legs[0]!.courseDegTrue).toBeCloseTo(KSFO_28R.headingDegTrue, 0);
    expect(legs[0]!.distanceNm).toBeCloseTo(4, 1);
    for (const leg of legs) expect(leg.distanceNm).toBeGreaterThan(0);
  });

  it('skips unknown fixes rather than inventing them', () => {
    expect(buildRoute(from.latDeg, from.lonDeg, ['SFOUT', 'NOPE'])).toHaveLength(1);
  });
});

describe('trackLeg', () => {
  const legs = buildRoute(from.latDeg, from.lonDeg, ['SFOUT']);
  const leg = legs[0]!;

  it('is on course on the leg centreline', () => {
    const mid = runwayPointToLatLon(KSFO_28R, 2 * 1852, 0);
    const t = trackLeg(leg, from, mid);
    expect(Math.abs(t.crossTrackNm)).toBeLessThan(0.05);
    expect(t.desiredTrackDegTrue).toBeCloseTo(leg.courseDegTrue, 0);
    expect(t.sequenced).toBe(false);
  });

  it('reports positive cross-track to the right of course and steers back left', () => {
    const right = runwayPointToLatLon(KSFO_28R, 2 * 1852, 1852); // 1 NM right
    const t = trackLeg(leg, from, right);
    expect(t.crossTrackNm).toBeGreaterThan(0.8);
    // desired track must be left of the leg course
    const delta = ((t.desiredTrackDegTrue - leg.courseDegTrue + 540) % 360) - 180;
    expect(delta).toBeLessThan(0);
  });

  it('sequences once the fix is behind', () => {
    const past = runwayPointToLatLon(KSFO_28R, 6 * 1852, 0);
    expect(trackLeg(leg, from, past).sequenced).toBe(true);
  });
});

describe('headingForTrack', () => {
  it('is the track itself with no wind', () => {
    expect(headingForTrack(270, 150, 0, 0)).toBeCloseTo(270, 3);
  });

  it('crabs into a crosswind', () => {
    // wind from the north (360) while tracking west (270): crab to the right
    const heading = headingForTrack(270, 150, 360, 30);
    expect(heading).toBeGreaterThan(270);
    expect(heading).toBeLessThan(300);
  });
});
