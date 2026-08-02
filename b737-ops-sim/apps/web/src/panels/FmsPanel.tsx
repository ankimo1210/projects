import { PROCEDURES, type AircraftState } from '@b737/shared';
import { sendCommand } from '../state/connection.js';

/**
 * Route / FMS panel (spec §22 Phase 5 T8). Load a procedure, arm LNAV, see the
 * legs and go direct to a fix. Everything shown comes from BACKEND fms state.
 */
export function FmsPanel({ state }: { state: AircraftState }): JSX.Element {
  const fms = state.fms;
  const sid = PROCEDURES.find((p) => p.kind === 'sid');
  const star = PROCEDURES.find((p) => p.kind === 'star');
  const approach = PROCEDURES.find((p) => p.kind === 'approach_transition');

  return (
    <div className="panel fms-panel" data-testid="fms-panel">
      <div className="panel-head">
        <span>Route</span>
        <span className="fms-route-id" data-testid="fms-route">
          {fms.routeId ?? 'no route'}
        </span>
        <button
          type="button"
          className={`ctl-btn ${fms.lnavArmed ? 'lit' : ''}`}
          data-testid="lnav-btn"
          title="LNAV follows the active leg"
          onClick={() => sendCommand({ type: 'set_lnav', armed: !fms.lnavArmed })}
        >
          LNAV
        </button>
      </div>

      <div className="fms-actions">
        <button
          type="button"
          data-testid="load-route"
          className="ctl-btn"
          onClick={() =>
            sendCommand({
              type: 'load_route',
              sidId: sid?.id ?? null,
              starId: star?.id ?? null,
              approachId: approach?.id ?? null,
            })
          }
        >
          Load {sid?.id} / {star?.id}
        </button>
        <span className="fms-readout" data-testid="fms-readout">
          {fms.distanceToWaypointNm === null
            ? '—'
            : `${fms.distanceToWaypointNm.toFixed(1)} NM · xtk ${(fms.crossTrackNm ?? 0).toFixed(2)} NM`}
        </span>
      </div>

      <ul className="fms-legs">
        {fms.legs.map((leg, i) => (
          <li
            key={leg.waypoint.id}
            className={`fms-leg ${i === fms.activeLegIndex ? 'active' : ''} ${
              i < fms.activeLegIndex ? 'passed' : ''
            }`}
          >
            <span className="fms-wp">{leg.waypoint.id}</span>
            <span className="fms-crs">{leg.courseDegTrue.toFixed(0)}°T</span>
            <span className="fms-dist">{leg.distanceNm.toFixed(1)} NM</span>
            <span className="fms-cstr">
              {leg.waypoint.altitudeFt ? `${leg.waypoint.altitudeFt} ft` : ''}
              {leg.waypoint.speedKt ? ` / ${leg.waypoint.speedKt} kt` : ''}
            </span>
            <button
              type="button"
              className="fms-direct"
              data-testid={`direct-${leg.waypoint.id}`}
              onClick={() => sendCommand({ type: 'direct_to', waypointId: leg.waypoint.id })}
            >
              DIR
            </button>
          </li>
        ))}
        {fms.legs.length === 0 && <li className="fms-empty">Load a route to fly LNAV.</li>}
      </ul>

      <div className="fms-weather" data-testid="weather-readout">
        Wind {String(Math.round(state.weather.windDirDeg)).padStart(3, '0')}/
        {state.weather.windSpeedKt.toFixed(0)}
        {state.weather.gustKt > 1
          ? `G${(state.weather.windSpeedKt + state.weather.gustKt).toFixed(0)}`
          : ''}
        {' · '}vis {(state.weather.visibilityM / 1000).toFixed(1)} km
        {state.weather.turbulence > 0.05
          ? ` · turb ${(state.weather.turbulence * 100).toFixed(0)}%`
          : ''}
        {state.activeFailures.length > 0 && (
          <span className="fms-failures"> · FAIL: {state.activeFailures.join(', ')}</span>
        )}
      </div>
    </div>
  );
}
