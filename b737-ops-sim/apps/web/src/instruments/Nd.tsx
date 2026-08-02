import { useState } from 'react';
import {
  FT_TO_M,
  KSFO_28R,
  NM_TO_M,
  angleDiffDeg,
  degToRad,
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

export function Nd({ state }: { state: AircraftState }): JSX.Element {
  const [rangeNm, setRangeNm] = useState(10);
  const hdg = state.attitude.headingDegMag;
  const pxPerM = R / (rangeNm * NM_TO_M);

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
          RNG {rangeNm} NM
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
