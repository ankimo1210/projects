import { clamp, angleDiffDeg, type AircraftState, type VSpeeds } from '@b737/shared';

/**
 * Primary Flight Display (spec §10 PFD MVP). Pure SVG derived entirely from
 * aircraft state — every element is data-driven, nothing is decorative.
 */

const W = 480;
const H = 440;
const ADI_CX = 240;
const ADI_CY = 190;
const ADI_R = 108;
const PX_PER_DEG_PITCH = 5.2;

interface PfdProps {
  state: AircraftState;
  vSpeeds: VSpeeds;
}

export function Pfd({ state, vSpeeds }: PfdProps): JSX.Element {
  const { pitchDeg, rollDeg, headingDegMag } = state.attitude;
  const ias = state.speeds.iasKt;
  const alt = state.position.altitudeFtMsl;
  const vs = state.speeds.verticalSpeedFpm;
  const ra = state.position.radioAltitudeFt;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="pfd" data-testid="pfd">
      <rect width={W} height={H} fill="#101114" />
      <FmaRow state={state} />
      <AttitudeIndicator pitchDeg={pitchDeg} rollDeg={rollDeg} state={state} />
      <SpeedTape iasKt={ias} vSpeeds={vSpeeds} selSpeedKt={state.mcp.selSpeedKt} wow={state.weightOnWheels} />
      <AltitudeTape altFt={alt} selAltFt={state.mcp.selAltitudeFt} />
      <VsIndicator vsFpm={vs} />
      <HeadingStrip headingDeg={headingDegMag} selHeadingDeg={state.mcp.selHeadingDeg} />
      {ra < 2500 && (
        <text x={ADI_CX} y={ADI_CY + 82} textAnchor="middle" className="pfd-ra">
          {Math.round(ra)}
        </text>
      )}
    </svg>
  );
}

function FmaRow({ state }: { state: AircraftState }): JSX.Element {
  const ap = state.mcp.autopilotEngaged;
  return (
    <g className="pfd-fma">
      <text x={120} y={18} textAnchor="middle" fill="#39d353">
        {ap ? 'SPD' : ''}
      </text>
      <text x={240} y={18} textAnchor="middle" fill="#39d353">
        {ap ? 'HDG SEL' : state.mcp.flightDirectorOn ? 'FD' : ''}
      </text>
      <text x={360} y={18} textAnchor="middle" fill="#39d353">
        {ap ? 'ALT/VS' : ''}
      </text>
      <text x={240} y={38} textAnchor="middle" fill={ap ? '#39d353' : '#888'} fontSize={15}>
        {ap ? 'CMD' : state.mcp.flightDirectorOn ? 'FD ONLY' : 'MANUAL'}
      </text>
    </g>
  );
}

function AttitudeIndicator({
  pitchDeg,
  rollDeg,
  state,
}: {
  pitchDeg: number;
  rollDeg: number;
  state: AircraftState;
}): JSX.Element {
  const pitchPx = pitchDeg * PX_PER_DEG_PITCH;
  const ladder: JSX.Element[] = [];
  for (let p = -30; p <= 30; p += 10) {
    if (p === 0) continue;
    const y = -p * PX_PER_DEG_PITCH;
    const w = Math.abs(p) % 20 === 0 ? 60 : 36;
    ladder.push(
      <g key={p}>
        <line x1={-w} y1={y} x2={w} y2={y} stroke="#fff" strokeWidth={2} />
        <text x={-w - 16} y={y + 5} fill="#fff" fontSize={13} textAnchor="middle">
          {Math.abs(p)}
        </text>
        <text x={w + 16} y={y + 5} fill="#fff" fontSize={13} textAnchor="middle">
          {Math.abs(p)}
        </text>
      </g>,
    );
  }

  const fd = computeFlightDirector(state);
  const loc = state.nav.locDeviationDots;
  const gs = state.nav.gsDeviationDots;

  return (
    <g transform={`translate(${ADI_CX} ${ADI_CY})`}>
      <clipPath id="adiClip">
        <circle r={ADI_R} />
      </clipPath>
      <g clipPath="url(#adiClip)">
        <g transform={`rotate(${-rollDeg})`}>
          <g transform={`translate(0 ${pitchPx})`}>
            <rect x={-260} y={-500} width={520} height={500} fill="#2f6fd0" />
            <rect x={-260} y={0} width={520} height={500} fill="#8a5a2a" />
            <line x1={-260} y1={0} x2={260} y2={0} stroke="#fff" strokeWidth={2.5} />
            {ladder}
          </g>
        </g>
      </g>
      {/* roll pointer */}
      <g transform={`rotate(${-rollDeg})`}>
        <polygon points="0,-98 -7,-84 7,-84" fill="#fff" />
      </g>
      <polygon points={`0,${-ADI_R + 2} -8,${-ADI_R + 16} 8,${-ADI_R + 16}`} fill="#ffd21f" />
      {/* aircraft symbol */}
      <rect x={-70} y={-3} width={34} height={6} fill="#111" stroke="#ffd21f" strokeWidth={2} />
      <rect x={36} y={-3} width={34} height={6} fill="#111" stroke="#ffd21f" strokeWidth={2} />
      <rect x={-4} y={-4} width={8} height={8} fill="#111" stroke="#ffd21f" strokeWidth={2} />
      {/* flight director bars */}
      {state.mcp.flightDirectorOn && fd && (
        <g>
          <line
            x1={-46}
            y1={clamp(-fd.pitchErrDeg * PX_PER_DEG_PITCH, -60, 60)}
            x2={46}
            y2={clamp(-fd.pitchErrDeg * PX_PER_DEG_PITCH, -60, 60)}
            stroke="#ff3ec8"
            strokeWidth={4}
          />
          <line
            x1={clamp(fd.rollErrDeg * 2.2, -60, 60)}
            y1={-46}
            x2={clamp(fd.rollErrDeg * 2.2, -60, 60)}
            y2={46}
            stroke="#ff3ec8"
            strokeWidth={4}
          />
        </g>
      )}
      {/* localizer scale (bottom) */}
      <g transform={`translate(0 ${ADI_R + 14})`}>
        {[-2, -1, 1, 2].map((d) => (
          <circle key={d} cx={d * 28} cy={0} r={3} fill="none" stroke="#ccc" />
        ))}
        <line x1={0} y1={-6} x2={0} y2={6} stroke="#ccc" strokeWidth={2} />
        {loc !== null && (
          <polygon
            points={`${clamp(loc, -2.5, 2.5) * 28},-7 ${clamp(loc, -2.5, 2.5) * 28 + 7},0 ${clamp(loc, -2.5, 2.5) * 28},7 ${clamp(loc, -2.5, 2.5) * 28 - 7},0`}
            fill="#ff3ec8"
          />
        )}
      </g>
      {/* glideslope scale (right) */}
      <g transform={`translate(${ADI_R + 14} 0)`}>
        {[-2, -1, 1, 2].map((d) => (
          <circle key={d} cx={0} cy={d * 28} r={3} fill="none" stroke="#ccc" />
        ))}
        <line x1={-6} y1={0} x2={6} y2={0} stroke="#ccc" strokeWidth={2} />
        {gs !== null && (
          <polygon
            points={`-7,${clamp(-gs, -2.5, 2.5) * 28} 0,${clamp(-gs, -2.5, 2.5) * 28 - 7} 7,${clamp(-gs, -2.5, 2.5) * 28} 0,${clamp(-gs, -2.5, 2.5) * 28 + 7}`}
            fill="#ff3ec8"
          />
        )}
      </g>
    </g>
  );
}

/** Simple FD guidance mirroring the MCP targets (client display only). */
function computeFlightDirector(
  state: AircraftState,
): { pitchErrDeg: number; rollErrDeg: number } | null {
  if (state.weightOnWheels && state.speeds.iasKt < 60) return null;
  const hdgErr = angleDiffDeg(state.attitude.headingDegMag, state.mcp.selHeadingDeg);
  const targetBank = clamp(hdgErr * 1.2, -25, 25);
  const rollErrDeg = targetBank - state.attitude.rollDeg;
  const altErr = state.position.altitudeFtMsl - state.mcp.selAltitudeFt;
  const targetVs =
    Math.abs(altErr) < 400
      ? clamp(-altErr * 4, -1000, 1000)
      : altErr < 0
        ? Math.max(state.mcp.selVerticalSpeedFpm, 1500)
        : Math.min(-Math.abs(state.mcp.selVerticalSpeedFpm) || -1200, -700);
  const vsErr = targetVs - state.speeds.verticalSpeedFpm;
  return { pitchErrDeg: clamp(-vsErr * 0.004, -10, 10), rollErrDeg };
}

function SpeedTape({
  iasKt,
  vSpeeds,
  selSpeedKt,
  wow,
}: {
  iasKt: number;
  vSpeeds: VSpeeds;
  selSpeedKt: number;
  wow: boolean;
}): JSX.Element {
  const x = 26;
  const w = 68;
  const cy = ADI_CY;
  const pxPerKt = 2.4;
  const ticks: JSX.Element[] = [];
  const lo = Math.max(0, Math.floor((iasKt - 70) / 10) * 10);
  for (let v = lo; v <= iasKt + 70; v += 10) {
    const y = cy - (v - iasKt) * pxPerKt;
    ticks.push(
      <g key={v}>
        <line x1={x + w - 10} y1={y} x2={x + w} y2={y} stroke="#fff" strokeWidth={1.5} />
        {v % 20 === 0 && (
          <text x={x + w - 14} y={y + 5} fill="#fff" fontSize={14} textAnchor="end">
            {v}
          </text>
        )}
      </g>,
    );
  }
  const bug = (v: number, label: string, color: string): JSX.Element | null => {
    const y = cy - (v - iasKt) * pxPerKt;
    if (y < 30 || y > H - 60) return null;
    return (
      <g key={label}>
        <line x1={x + w} y1={y} x2={x + w + 8} y2={y} stroke={color} strokeWidth={2.5} />
        <text x={x + w + 11} y={y + 4} fill={color} fontSize={11}>
          {label}
        </text>
      </g>
    );
  };
  return (
    <g data-testid="pfd-speed">
      <rect x={x} y={26} width={w} height={H - 86} fill="#2c2d31" />
      <g clipPath="url(#speedClip)">
        <clipPath id="speedClip">
          <rect x={x} y={26} width={w + 40} height={H - 86} />
        </clipPath>
        {ticks}
        {wow || iasKt < 220
          ? [bug(vSpeeds.v1Kt, 'V1', '#39d353'), bug(vSpeeds.vrKt, 'VR', '#39d353'), bug(vSpeeds.v2Kt, 'V2', '#39d353')]
          : null}
        {bug(selSpeedKt, '', '#ff3ec8')}
      </g>
      <rect x={x - 4} y={cy - 16} width={w + 6} height={32} fill="#000" stroke="#fff" />
      <text x={x + w - 12} y={cy + 8} fill="#fff" fontSize={22} textAnchor="end" className="pfd-num">
        {Math.round(iasKt)}
      </text>
      <text x={x + 20} y={20} fill="#ff3ec8" fontSize={14}>
        {Math.round(selSpeedKt)}
      </text>
    </g>
  );
}

function AltitudeTape({ altFt, selAltFt }: { altFt: number; selAltFt: number }): JSX.Element {
  const x = 388;
  const w = 66;
  const cy = ADI_CY;
  const pxPerFt = 0.34;
  const ticks: JSX.Element[] = [];
  const lo = Math.floor((altFt - 450) / 100) * 100;
  for (let v = lo; v <= altFt + 450; v += 100) {
    const y = cy - (v - altFt) * pxPerFt;
    ticks.push(
      <g key={v}>
        <line x1={x} y1={y} x2={x + 8} y2={y} stroke="#fff" strokeWidth={1.5} />
        {v % 200 === 0 && (
          <text x={x + 12} y={y + 5} fill="#fff" fontSize={13}>
            {v}
          </text>
        )}
      </g>,
    );
  }
  const selY = cy - (selAltFt - altFt) * pxPerFt;
  return (
    <g data-testid="pfd-alt">
      <rect x={x} y={26} width={w} height={H - 86} fill="#2c2d31" />
      <g clipPath="url(#altClip)">
        <clipPath id="altClip">
          <rect x={x - 12} y={26} width={w + 12} height={H - 86} />
        </clipPath>
        {ticks}
        {selY > 26 && selY < H - 60 && (
          <polygon
            points={`${x - 2},${selY} ${x - 10},${selY - 8} ${x - 10},${selY + 8}`}
            fill="#ff3ec8"
          />
        )}
      </g>
      <rect x={x - 2} y={cy - 16} width={w + 4} height={32} fill="#000" stroke="#fff" />
      <text x={x + 6} y={cy + 8} fill="#fff" fontSize={22} className="pfd-num">
        {Math.round(altFt)}
      </text>
      <text x={x + 8} y={20} fill="#ff3ec8" fontSize={14}>
        {Math.round(selAltFt)}
      </text>
    </g>
  );
}

function VsIndicator({ vsFpm }: { vsFpm: number }): JSX.Element {
  const x = 462;
  const cy = ADI_CY;
  const v = clamp(vsFpm, -3200, 3200);
  const y = cy - (v / 3200) * 90;
  return (
    <g data-testid="pfd-vs">
      <rect x={x - 4} y={cy - 100} width={20} height={200} fill="#2c2d31" />
      {[-2000, -1000, 1000, 2000].map((m) => (
        <line
          key={m}
          x1={x - 4}
          y1={cy - (m / 3200) * 90}
          x2={x + 2}
          y2={cy - (m / 3200) * 90}
          stroke="#aaa"
        />
      ))}
      <line x1={x - 4} y1={cy} x2={x + 4} y2={cy} stroke="#fff" strokeWidth={2} />
      <line x1={x + 14} y1={cy} x2={x - 2} y2={y} stroke="#fff" strokeWidth={2.5} />
      {Math.abs(vsFpm) > 150 && (
        <text x={x + 8} y={vsFpm > 0 ? cy - 104 : cy + 112} fill="#fff" fontSize={12} textAnchor="end">
          {Math.abs(Math.round(vsFpm / 50) * 50)}
        </text>
      )}
    </g>
  );
}

function HeadingStrip({
  headingDeg,
  selHeadingDeg,
}: {
  headingDeg: number;
  selHeadingDeg: number;
}): JSX.Element {
  const cy = H - 26;
  const pxPerDeg = 3.4;
  const ticks: JSX.Element[] = [];
  const lo = Math.floor((headingDeg - 45) / 5) * 5;
  for (let hRaw = lo; hRaw <= headingDeg + 45; hRaw += 5) {
    const h = ((hRaw % 360) + 360) % 360;
    const xPos = ADI_CX + angleDiffDeg(headingDeg, h) * pxPerDeg * -1 * -1;
    const xx = ADI_CX + angleDiffDeg(headingDeg, hRaw) * pxPerDeg;
    void xPos;
    ticks.push(
      <g key={hRaw}>
        <line x1={xx} y1={cy - 6} x2={xx} y2={cy} stroke="#fff" />
        {h % 30 === 0 && (
          <text x={xx} y={cy - 10} fill="#fff" fontSize={12} textAnchor="middle">
            {h === 0 ? '36' : String(h / 10).padStart(2, '0')}
          </text>
        )}
      </g>,
    );
  }
  const selX = ADI_CX + clamp(angleDiffDeg(headingDeg, selHeadingDeg), -44, 44) * pxPerDeg;
  return (
    <g data-testid="pfd-hdg">
      <rect x={ADI_CX - 155} y={cy - 26} width={310} height={32} fill="#2c2d31" />
      <g clipPath="url(#hdgClip)">
        <clipPath id="hdgClip">
          <rect x={ADI_CX - 152} y={cy - 26} width={304} height={32} />
        </clipPath>
        {ticks}
        <polygon points={`${selX - 7},${cy + 4} ${selX + 7},${cy + 4} ${selX},${cy - 4}`} fill="#ff3ec8" />
      </g>
      <polygon points={`${ADI_CX - 6},${cy - 28} ${ADI_CX + 6},${cy - 28} ${ADI_CX},${cy - 20}`} fill="#fff" />
      <text x={ADI_CX} y={cy - 32} fill="#39d353" fontSize={15} textAnchor="middle" className="pfd-num">
        {String(Math.round(headingDeg)).padStart(3, '0')}
      </text>
    </g>
  );
}
