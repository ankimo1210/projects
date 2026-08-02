import { useState } from 'react';
import {
  FT_TO_M,
  HOLD_SHORT_OFFSET_M,
  KSFO_28R,
  NM_TO_M,
  angleDiffDeg,
  degToRad,
  getTaxiNetwork,
  runwayPointToLatLon,
  toLocalEnuM,
  type AircraftState,
} from '@b737/shared';

/**
 * Navigation Display, heading-up (spec §10 ND MVP): compass rose, heading,
 * track, selected-heading bug, runway + extended centerline, range rings.
 */

const W = 480;
const H = 480;
const CX = 240;
const CY = 300;
const R = 210;

/** {latDeg,lonDeg} → ENU metres from the runway threshold, as positional args. */
function enu(p: { latDeg: number; lonDeg: number }): [number, number] {
  const e = toLocalEnuM(KSFO_28R.thresholdLatDeg, KSFO_28R.thresholdLonDeg, p.latDeg, p.lonDeg);
  return [e.eastM, e.northM];
}

export function Nd({ state }: { state: AircraftState }): JSX.Element {
  const [rangeNm, setRangeNm] = useState(10);
  const hdg = state.attitude.headingDegMag;
  // On the ground the interesting features are metres apart, not miles: clamp
  // the range so the taxi layout is actually visible (M3).
  const effectiveRangeNm = state.weightOnWheels ? Math.min(rangeNm, 0.5) : rangeNm;
  const pxPerM = R / (effectiveRangeNm * NM_TO_M);

  // aircraft position in runway-threshold ENU
  const { eastM, northM } = toLocalEnuM(
    KSFO_28R.thresholdLatDeg,
    KSFO_28R.thresholdLonDeg,
    state.position.latDeg,
    state.position.lonDeg,
  );

  // map a world ENU point → screen (heading-up, aircraft at center)
  const headingTrueRad = degToRad(hdg + KSFO_28R.magneticVariationDeg);
  const toScreen = (pEastM: number, pNorthM: number): { x: number; y: number } => {
    const dx = pEastM - eastM;
    const dz = pNorthM - northM;
    // rotate so aircraft heading points up
    const xr = dx * Math.cos(-headingTrueRad) - dz * Math.sin(-headingTrueRad);
    const zr = dx * Math.sin(-headingTrueRad) + dz * Math.cos(-headingTrueRad);
    return { x: CX + xr * pxPerM, y: CY - zr * pxPerM };
  };

  // runway polyline: threshold → stop end (true heading direction)
  const dirE = Math.sin(degToRad(KSFO_28R.headingDegTrue));
  const dirN = Math.cos(degToRad(KSFO_28R.headingDegTrue));
  const lengthM = KSFO_28R.lengthFt * FT_TO_M;
  const thr = toScreen(0, 0);
  const end = toScreen(dirE * lengthM, dirN * lengthM);
  const appStart = toScreen(-dirE * 12 * NM_TO_M, -dirN * 12 * NM_TO_M);

  const roseTicks: JSX.Element[] = [];
  for (let a = 0; a < 360; a += 5) {
    const rel = angleDiffDeg(hdg, a);
    const rad = degToRad(rel - 90);
    const r1 = R - (a % 10 === 0 ? 14 : 8);
    roseTicks.push(
      <line
        key={a}
        x1={CX + r1 * Math.cos(rad)}
        y1={CY + r1 * Math.sin(rad)}
        x2={CX + R * Math.cos(rad)}
        y2={CY + R * Math.sin(rad)}
        stroke="#ccc"
        strokeWidth={a % 30 === 0 ? 2 : 1}
      />,
    );
    if (a % 30 === 0) {
      const rt = R - 28;
      roseTicks.push(
        <text
          key={`t${a}`}
          x={CX + rt * Math.cos(rad)}
          y={CY + rt * Math.sin(rad) + 5}
          fill="#fff"
          fontSize={14}
          textAnchor="middle"
        >
          {a === 0 ? '36' : String(a / 10).padStart(2, '0')}
        </text>,
      );
    }
  }

  const selRel = angleDiffDeg(hdg, state.mcp.selHeadingDeg);
  const selRad = degToRad(selRel - 90);
  // Ground movement awareness (M3): the taxi layout is drawn from the same
  // network the scenario rules use, so what the crew sees is what is judged.
  const network = getTaxiNetwork(state.airport.icao ?? '', state.airport.runwayId ?? '');
  const nodeToScreen = (nodeId: string): { x: number; y: number } | null => {
    const node = network?.nodes[nodeId];
    if (!node) return null;
    const p = toLocalEnuM(
      KSFO_28R.thresholdLatDeg,
      KSFO_28R.thresholdLonDeg,
      node.latDeg,
      node.lonDeg,
    );
    return toScreen(p.eastM, p.northM);
  };
  const taxiLines =
    network && state.weightOnWheels
      ? network.segments.map((seg) => ({
          id: seg.id,
          label: seg.label,
          from: nodeToScreen(seg.fromNodeId),
          to: nodeToScreen(seg.toNodeId),
        }))
      : [];
  // hold-short bar across the runway entry, at the holding position
  const holdShort =
    network && state.weightOnWheels
      ? {
          a: toScreen(...enu(runwayPointToLatLon(KSFO_28R, 40 - 20, HOLD_SHORT_OFFSET_M))),
          b: toScreen(...enu(runwayPointToLatLon(KSFO_28R, 40 + 20, HOLD_SHORT_OFFSET_M))),
        }
      : null;

  // Route ahead (M5): the same legs the autopilot is flying.
  const routePoints = state.fms.legs.map((leg) => {
    const e = toLocalEnuM(
      KSFO_28R.thresholdLatDeg,
      KSFO_28R.thresholdLonDeg,
      leg.waypoint.latDeg,
      leg.waypoint.lonDeg,
    );
    return { id: leg.waypoint.id, ...toScreen(e.eastM, e.northM) };
  });

  const trackRel = angleDiffDeg(hdg, state.attitude.groundTrackDegMag);
  const trackRad = degToRad(trackRel - 90);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="nd" data-testid="nd">
      <rect width={W} height={H} fill="#101114" />
      <clipPath id="ndClip">
        <circle cx={CX} cy={CY} r={R - 2} />
      </clipPath>
      <g clipPath="url(#ndClip)">
        {/* range rings */}
        <circle cx={CX} cy={CY} r={R / 2} fill="none" stroke="#3a3b40" strokeDasharray="3 5" />
        {/* extended centerline + runway */}
        <line
          x1={appStart.x}
          y1={appStart.y}
          x2={thr.x}
          y2={thr.y}
          stroke="#39d353"
          strokeDasharray="8 8"
          strokeWidth={1.5}
        />
        <line x1={thr.x} y1={thr.y} x2={end.x} y2={end.y} stroke="#fff" strokeWidth={6} />
        {/* taxi network (ground only) */}
        {taxiLines.map((seg) =>
          seg.from && seg.to ? (
            <line
              key={seg.id}
              x1={seg.from.x}
              y1={seg.from.y}
              x2={seg.to.x}
              y2={seg.to.y}
              stroke="#7a8798"
              strokeWidth={3}
            />
          ) : null,
        )}
        {holdShort && (
          <line
            x1={holdShort.a.x}
            y1={holdShort.a.y}
            x2={holdShort.b.x}
            y2={holdShort.b.y}
            stroke="#ffb648"
            strokeWidth={3}
            strokeDasharray="4 3"
          />
        )}
        {/* route */}
        {routePoints.length > 0 && (
          <polyline
            points={[`${CX},${CY}`, ...routePoints.map((p) => `${p.x},${p.y}`)].join(' ')}
            fill="none"
            stroke="#ff3ec8"
            strokeWidth={1.5}
            strokeDasharray="6 4"
          />
        )}
        {routePoints.map((p, i) => (
          <g key={p.id}>
            <polygon
              points={`${p.x},${p.y - 5} ${p.x + 5},${p.y} ${p.x},${p.y + 5} ${p.x - 5},${p.y}`}
              fill="none"
              stroke={i === state.fms.activeLegIndex ? '#39d353' : '#ff3ec8'}
              strokeWidth={1.5}
            />
            <text x={p.x + 8} y={p.y + 4} fill="#cbd" fontSize={11}>
              {p.id}
            </text>
          </g>
        ))}
        {/* track line */}
        <line
          x1={CX}
          y1={CY}
          x2={CX + (R - 24) * Math.cos(trackRad)}
          y2={CY + (R - 24) * Math.sin(trackRad)}
          stroke="#39d353"
          strokeWidth={1.5}
        />
      </g>
      {roseTicks}
      {/* selected heading bug */}
      <g
        transform={`translate(${CX + (R + 4) * Math.cos(selRad)} ${CY + (R + 4) * Math.sin(selRad)}) rotate(${selRel})`}
      >
        <polygon points="-9,0 9,0 4,8 -4,8" fill="#ff3ec8" />
      </g>
      {/* aircraft symbol */}
      <polygon points={`${CX},${CY - 12} ${CX - 9},${CY + 10} ${CX + 9},${CY + 10}`} fill="#fff" />
      {/* labels */}
      <text x={CX} y={26} fill="#39d353" fontSize={17} textAnchor="middle" className="pfd-num">
        HDG {String(Math.round(hdg)).padStart(3, '0')}
      </text>
      <text x={40} y={26} fill="#9ad" fontSize={13}>
        GS {Math.round(state.speeds.gsKt)}
      </text>
      <text x={W - 108} y={26} fill="#9ad" fontSize={13}>
        {KSFO_28R.airportIcao} {KSFO_28R.runwayId}
      </text>
      <g className="nd-range">
        <text x={16} y={H - 42} fill="#888" fontSize={12}>
          RNG {effectiveRangeNm} NM
        </text>
        {[5, 10, 20].map((r) => (
          <text
            key={r}
            x={16 + (r === 5 ? 0 : r === 10 ? 34 : 68)}
            y={H - 20}
            fill={rangeNm === r ? '#39d353' : '#777'}
            fontSize={13}
            style={{ cursor: 'pointer' }}
            onClick={() => setRangeNm(r)}
          >
            {r}
          </text>
        ))}
      </g>
    </svg>
  );
}
