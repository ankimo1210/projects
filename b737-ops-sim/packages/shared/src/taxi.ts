import { toLocalEnuM } from './geo.js';
import { KSFO_28R, runwayPointToLatLon, type RunwayData } from './airports.js';

/**
 * Ground movement layout (spec §22 Phase 3 taxi operations).
 *
 * NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED. The network below is a
 * plausible, self-consistent taxi layout for the mock world, authored in the
 * runway's own frame so it lines up exactly with the runway datum. It is NOT
 * survey data and must not be used for real-world navigation. In FlightGear
 * mode the scenery is FlightGear's; this network is still the source for
 * scenario logic, so treat a mismatch as a reason to re-author it.
 */

export interface TaxiNode {
  id: string;
  latDeg: number;
  lonDeg: number;
}

export interface TaxiSegment {
  id: string;
  /** Taxiway designator spoken by ATC ("A", "E1"). */
  label: string;
  fromNodeId: string;
  toNodeId: string;
  widthM: number;
}

export interface TaxiStand {
  id: string;
  nodeId: string;
  /** Nose heading when parked. */
  headingDegTrue: number;
}

export interface TaxiNetwork {
  airportIcao: string;
  /** Runway this layout is authored against. */
  runwayId: string;
  nodes: Record<string, TaxiNode>;
  segments: TaxiSegment[];
  stands: TaxiStand[];
}

/** Where a position sits relative to the taxi network. */
export interface TaxiPosition {
  /** Nearest segment, or null when nothing is within `maxOffsetM`. */
  segmentId: string | null;
  label: string | null;
  /** Metres from that segment's centerline. */
  offsetM: number;
  /** Metres travelled along the segment from its `from` node. */
  alongM: number;
  /** Within the paved half-width of the nearest segment. */
  onSurface: boolean;
}

const TAXIWAY_WIDTH_M = 23;
const APRON_WIDTH_M = 60;

/** Author a node in runway coordinates (metres along / right of 28R). */
function node(id: string, runway: RunwayData, alongM: number, crossM: number): TaxiNode {
  const { latDeg, lonDeg } = runwayPointToLatLon(runway, alongM, crossM);
  return { id, latDeg, lonDeg };
}

/**
 * KSFO 28R ground layout used by the mock world:
 *
 *   stand S1 ── apron ── A1 ─ A2 ─ A3 ─ A4      (taxiway A, parallel, right side)
 *                         │           │
 *                    entry C1     exit E1
 *                         │           │
 *   ===== runway 28R ===========================
 */
export const KSFO_TAXI: TaxiNetwork = (() => {
  const rwy = KSFO_28R;
  const A_CROSS_M = 90; // parallel taxiway offset, right of the landing direction
  const nodes: TaxiNode[] = [
    node('A1', rwy, 40, A_CROSS_M), // abeam the threshold: runway entry point
    node('A2', rwy, 700, A_CROSS_M),
    node('A3', rwy, 1900, A_CROSS_M), // abeam the high-speed exit
    node('A4', rwy, 2900, A_CROSS_M),
    node('R1', rwy, 40, 0), // runway centerline at the entry
    node('X1', rwy, 1900, 0), // runway centerline at the exit
    node('S1', rwy, 350, 210), // stand
    node('P1', rwy, 350, A_CROSS_M), // apron entry on taxiway A
  ];
  return {
    airportIcao: rwy.airportIcao,
    runwayId: rwy.runwayId,
    nodes: Object.fromEntries(nodes.map((n) => [n.id, n])),
    segments: [
      { id: 'A_1_2', label: 'A', fromNodeId: 'A1', toNodeId: 'A2', widthM: TAXIWAY_WIDTH_M },
      { id: 'A_2_3', label: 'A', fromNodeId: 'A2', toNodeId: 'A3', widthM: TAXIWAY_WIDTH_M },
      { id: 'A_3_4', label: 'A', fromNodeId: 'A3', toNodeId: 'A4', widthM: TAXIWAY_WIDTH_M },
      { id: 'C1', label: 'C1', fromNodeId: 'A1', toNodeId: 'R1', widthM: TAXIWAY_WIDTH_M },
      { id: 'E1', label: 'E1', fromNodeId: 'X1', toNodeId: 'A3', widthM: TAXIWAY_WIDTH_M },
      { id: 'APRON', label: 'apron', fromNodeId: 'P1', toNodeId: 'S1', widthM: APRON_WIDTH_M },
      { id: 'A_1_P', label: 'A', fromNodeId: 'A1', toNodeId: 'P1', widthM: TAXIWAY_WIDTH_M },
    ],
    stands: [{ id: 'S1', nodeId: 'S1', headingDegTrue: rwy.headingDegTrue }],
  };
})();

export function getTaxiNetwork(airportIcao: string, runwayId: string): TaxiNetwork | undefined {
  return KSFO_TAXI.airportIcao === airportIcao && KSFO_TAXI.runwayId === runwayId
    ? KSFO_TAXI
    : undefined;
}

/** Nearest taxi segment to a position, with the offsets scenario rules need. */
export function taxiPosition(network: TaxiNetwork, latDeg: number, lonDeg: number): TaxiPosition {
  let best: TaxiPosition = {
    segmentId: null,
    label: null,
    offsetM: Number.POSITIVE_INFINITY,
    alongM: 0,
    onSurface: false,
  };
  for (const segment of network.segments) {
    const from = network.nodes[segment.fromNodeId];
    const to = network.nodes[segment.toNodeId];
    if (!from || !to) continue;
    const a = toLocalEnuM(from.latDeg, from.lonDeg, latDeg, lonDeg);
    const b = toLocalEnuM(from.latDeg, from.lonDeg, to.latDeg, to.lonDeg);
    const lenSq = b.eastM * b.eastM + b.northM * b.northM;
    if (lenSq === 0) continue;
    const t = Math.max(0, Math.min(1, (a.eastM * b.eastM + a.northM * b.northM) / lenSq));
    const projE = b.eastM * t;
    const projN = b.northM * t;
    const offsetM = Math.hypot(a.eastM - projE, a.northM - projN);
    if (offsetM >= best.offsetM) continue;
    best = {
      segmentId: segment.id,
      label: segment.label,
      offsetM,
      alongM: Math.sqrt(lenSq) * t,
      onSurface: offsetM <= segment.widthM / 2,
    };
  }
  return best;
}

/** Straight-line distance to a stand, for "parked" detection. */
export function distanceToStandM(
  network: TaxiNetwork,
  standId: string,
  latDeg: number,
  lonDeg: number,
): number | null {
  const stand = network.stands.find((s) => s.id === standId);
  const standNode = stand ? network.nodes[stand.nodeId] : undefined;
  if (!standNode) return null;
  const d = toLocalEnuM(standNode.latDeg, standNode.lonDeg, latDeg, lonDeg);
  return Math.hypot(d.eastM, d.northM);
}
