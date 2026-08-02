import { clamp, flapNormToNearestDetent, type AircraftState } from '@b737/shared';

/** Engine/system display: N1 gauges, flaps, gear, spoilers, autobrake. */

export function EngineDisplay({ state }: { state: AircraftState }): JSX.Element {
  const gearNorm = state.controls.gearPositionNorm;
  const gearLabel = gearNorm > 0.99 ? 'DOWN' : gearNorm < 0.01 ? 'UP' : 'TRANSIT';
  const gearColor = gearNorm > 0.99 ? '#39d353' : gearNorm < 0.01 ? '#888' : '#e5484d';
  // surfaces indicated as the nearest handle detent (norm is index-scaled)
  const flapsIndicated = flapNormToNearestDetent(state.controls.flapsActualNorm);

  return (
    <svg viewBox="0 0 300 440" className="eicas" data-testid="eicas">
      <rect width={300} height={440} fill="#101114" />
      <text x={150} y={22} textAnchor="middle" fill="#9ad" fontSize={14}>
        N1
      </text>
      <N1Gauge
        cx={80}
        cy={90}
        n1={state.engines.left.n1Pct}
        rev={state.engines.left.reverserNorm}
      />
      <N1Gauge
        cx={220}
        cy={90}
        n1={state.engines.right.n1Pct}
        rev={state.engines.right.reverserNorm}
      />

      {/* flaps */}
      <text x={70} y={205} fill="#9ad" fontSize={13}>
        FLAPS
      </text>
      <rect x={60} y={215} width={22} height={120} fill="#2c2d31" stroke="#555" />
      <rect
        x={62}
        y={217}
        width={18}
        height={clamp(state.controls.flapsActualNorm, 0, 1) * 116}
        fill="#39d353"
      />
      <text x={95} y={280} fill="#fff" fontSize={16} className="pfd-num">
        {flapsIndicated}
      </text>
      <text x={95} y={300} fill="#888" fontSize={11}>
        handle {state.controls.flapHandleDetent}
      </text>

      {/* gear */}
      <text x={200} y={205} fill="#9ad" fontSize={13}>
        GEAR
      </text>
      <rect
        x={190}
        y={215}
        width={80}
        height={34}
        fill="#1a1b1e"
        stroke={gearColor}
        strokeWidth={2}
      />
      <text x={230} y={238} fill={gearColor} fontSize={16} textAnchor="middle" className="pfd-num">
        {gearLabel}
      </text>

      {/* spoilers / autobrake / parking brake */}
      <text
        x={190}
        y={285}
        fill={state.controls.spoilersDeployedNorm > 0.1 ? '#ffd21f' : '#555'}
        fontSize={13}
      >
        SPEEDBRAKE {state.controls.speedbrakeArmed ? '(ARM)' : ''}
      </text>
      <text x={190} y={310} fill="#9ad" fontSize={13}>
        AUTOBRK {state.controls.autobrake}
      </text>
      <text
        x={190}
        y={335}
        fill={state.controls.parkingBrakeSet ? '#e5484d' : '#555'}
        fontSize={13}
      >
        PARK BRK
      </text>

      {/* wind/status line */}
      <text x={60} y={380} fill="#888" fontSize={12}>
        WOW {state.weightOnWheels ? 'GND' : 'AIR'} · RA {Math.round(state.position.radioAltitudeFt)}{' '}
        ft
      </text>
      <text x={60} y={402} fill="#888" fontSize={12}>
        REV{' '}
        {(
          Math.max(state.engines.left.reverserNorm, state.engines.right.reverserNorm) * 100
        ).toFixed(0)}
        % · BRK {(state.controls.brakeNorm * 100).toFixed(0)}%
      </text>
    </svg>
  );
}

function N1Gauge({
  cx,
  cy,
  n1,
  rev,
}: {
  cx: number;
  cy: number;
  n1: number;
  rev: number;
}): JSX.Element {
  const frac = clamp(n1 / 104, 0, 1);
  const start = -210;
  const sweep = 240;
  const angle = start + frac * sweep;
  const arc = (a: number, r: number): { x: number; y: number } => ({
    x: cx + r * Math.cos((a * Math.PI) / 180),
    y: cy + r * Math.sin((a * Math.PI) / 180),
  });
  const needle = arc(angle, 52);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const a = start + f * sweep;
    const p1 = arc(a, 56);
    const p2 = arc(a, 62);
    return <line key={f} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#aaa" strokeWidth={2} />;
  });
  return (
    <g>
      <circle cx={cx} cy={cy} r={62} fill="#1a1b1e" stroke="#555" />
      {ticks}
      <line x1={cx} y1={cy} x2={needle.x} y2={needle.y} stroke="#39d353" strokeWidth={3.5} />
      <rect x={cx - 34} y={cy + 14} width={68} height={26} fill="#000" stroke="#555" />
      <text x={cx} y={cy + 33} fill="#39d353" fontSize={17} textAnchor="middle" className="pfd-num">
        {n1.toFixed(1)}
      </text>
      {rev > 0.05 && (
        <text x={cx} y={cy - 18} fill="#ffd21f" fontSize={13} textAnchor="middle">
          REV
        </text>
      )}
    </g>
  );
}
