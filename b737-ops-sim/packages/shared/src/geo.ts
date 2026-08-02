import { degToRad, radToDeg, normalizeDeg360 } from './units.js';

export const EARTH_RADIUS_M = 6371000;

/** Great-circle distance in meters (haversine). */
export function distanceM(
  lat1Deg: number,
  lon1Deg: number,
  lat2Deg: number,
  lon2Deg: number,
): number {
  const φ1 = degToRad(lat1Deg);
  const φ2 = degToRad(lat2Deg);
  const dφ = degToRad(lat2Deg - lat1Deg);
  const dλ = degToRad(lon2Deg - lon1Deg);
  const a = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
}

/** Initial great-circle bearing from point 1 to point 2, degrees true [0, 360). */
export function bearingDeg(
  lat1Deg: number,
  lon1Deg: number,
  lat2Deg: number,
  lon2Deg: number,
): number {
  const φ1 = degToRad(lat1Deg);
  const φ2 = degToRad(lat2Deg);
  const dλ = degToRad(lon2Deg - lon1Deg);
  const y = Math.sin(dλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(dλ);
  return normalizeDeg360(radToDeg(Math.atan2(y, x)));
}

/** Destination point given start, bearing (deg true) and distance (m). */
export function destinationPoint(
  latDeg: number,
  lonDeg: number,
  bearingDegTrue: number,
  distM: number,
): { latDeg: number; lonDeg: number } {
  const δ = distM / EARTH_RADIUS_M;
  const θ = degToRad(bearingDegTrue);
  const φ1 = degToRad(latDeg);
  const λ1 = degToRad(lonDeg);
  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 =
    λ1 +
    Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
  return { latDeg: radToDeg(φ2), lonDeg: normalizeDeg360(radToDeg(λ2) + 180) - 180 };
}

/**
 * Equirectangular projection to a local East/North frame (meters) around an
 * origin. Accurate enough (<0.1% error) within ~50 km of the origin, which is
 * all this simulator needs around a single airport.
 */
export function toLocalEnuM(
  originLatDeg: number,
  originLonDeg: number,
  latDeg: number,
  lonDeg: number,
): { eastM: number; northM: number } {
  const northM = degToRad(latDeg - originLatDeg) * EARTH_RADIUS_M;
  const eastM = degToRad(lonDeg - originLonDeg) * EARTH_RADIUS_M * Math.cos(degToRad(originLatDeg));
  return { eastM, northM };
}

/** Inverse of {@link toLocalEnuM}. */
export function fromLocalEnuM(
  originLatDeg: number,
  originLonDeg: number,
  eastM: number,
  northM: number,
): { latDeg: number; lonDeg: number } {
  const latDeg = originLatDeg + radToDeg(northM / EARTH_RADIUS_M);
  const lonDeg =
    originLonDeg + radToDeg(eastM / (EARTH_RADIUS_M * Math.cos(degToRad(originLatDeg))));
  return { latDeg, lonDeg };
}
