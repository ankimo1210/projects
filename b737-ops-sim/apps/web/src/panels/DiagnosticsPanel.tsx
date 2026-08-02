import { client, getSession } from '../state/connection.js';
import { useSessionStore, useSettingsStore, useSimStore } from '../state/stores.js';

/** Developer diagnostics (spec §19) — hidden by default, toggled via ` or ⚙. */
export function DiagnosticsPanel(): JSX.Element | null {
  const show = useSettingsStore((s) => s.showDiagnostics);
  const sim = useSimStore();
  useSessionStore((s) => s.version);
  const session = getSession();
  if (!show) return null;

  const d = client.diagnostics;
  const s = sim.latest;
  const activeChecklist = session.activeChecklistId
    ? session.runtime.checklistRuns.get(session.activeChecklistId)
    : null;
  const recentEvents = session.runtime.events.slice(-8);

  return (
    <aside className="diagnostics" data-testid="diagnostics">
      <h4>Diagnostics</h4>
      <table>
        <tbody>
          <Row k="connection" v={`${sim.connection} (${sim.backendMode ?? '-'})`} />
          <Row k="backend" v={sim.backendStatus?.detail ?? '-'} />
          <Row
            k="state rate"
            v={`${d.updatesPerSecond.toFixed(1)}/s (cfg ${sim.stateRateHz} Hz)`}
          />
          <Row k="ws latency" v={d.latencyMs === null ? '-' : `${d.latencyMs} ms`} />
          <Row k="state seq" v={`${d.lastStateSeq} (gaps ${d.droppedSeqGaps})`} />
          <Row k="last cmd" v={`${d.lastCommand ?? '-'} → ${d.lastCommandResult ?? '-'}`} />
          <Row k="phase" v={session.phaseId} />
          <Row k="checklist item" v={activeChecklist?.activeItem?.definition.challenge ?? '-'} />
          <Row
            k="position"
            v={s ? `${s.position.latDeg.toFixed(5)}, ${s.position.lonDeg.toFixed(5)}` : '-'}
          />
          <Row
            k="state"
            v={
              s
                ? `${s.speeds.iasKt.toFixed(0)}kt ${s.position.altitudeFtMsl.toFixed(0)}ft ${s.speeds.verticalSpeedFpm.toFixed(0)}fpm`
                : '-'
            }
          />
          <Row
            k="ils"
            v={
              s
                ? `loc ${s.nav.locDeviationDots?.toFixed(2) ?? 'null'} gs ${s.nav.gsDeviationDots?.toFixed(2) ?? 'null'}`
                : '-'
            }
          />
        </tbody>
      </table>
      <h5>Recent rule events</h5>
      <ul>
        {recentEvents.map((e, i) => (
          <li key={i}>
            [{e.simTimeSec.toFixed(0)}s] {e.kind}: {e.id}
          </li>
        ))}
      </ul>
    </aside>
  );
}

function Row({ k, v }: { k: string; v: string }): JSX.Element {
  return (
    <tr>
      <td>{k}</td>
      <td>{v}</td>
    </tr>
  );
}
