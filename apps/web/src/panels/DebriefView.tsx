import { useMemo } from 'react';
import { getSession } from '../state/connection.js';
import { useSessionStore } from '../state/stores.js';

/** Structured post-flight report (spec §16): transparent per-category scores. */
export function DebriefView(): JSX.Element | null {
  const show = useSessionStore((s) => s.showDebrief);
  const setShow = useSessionStore((s) => s.setShowDebrief);
  const version = useSessionStore((s) => s.version);
  const session = getSession();
  // recompute when the overlay opens or the session advances
  const report = useMemo(() => (show ? session.debrief() : null), [show, version, session]);
  if (!show || !report) return null;

  return (
    <div className="debrief-overlay" data-testid="debrief">
      <div className="debrief-card">
        <div className="debrief-head">
          <h2>Flight Debrief</h2>
          <span className={`overall overall-${report.overall.toLowerCase()}`} data-testid="debrief-overall">
            {report.overall.replaceAll('_', ' ')}
          </span>
          <button type="button" className="debrief-close" onClick={() => setShow(false)}>
            ✕
          </button>
        </div>

        <div className="debrief-grid">
          <section className="debrief-categories">
            {report.categories.map((c) => (
              <div key={c.id} className="cat">
                <div className="cat-head">
                  <span>{c.label}</span>
                  <span className="cat-score">{c.score} / 100</span>
                </div>
                <div className="cat-bar">
                  <div
                    className={`cat-fill ${c.score >= 85 ? 'good' : c.score >= 60 ? 'mid' : 'poor'}`}
                    style={{ width: `${c.score}%` }}
                  />
                </div>
                {c.findings.length > 0 && (
                  <ul className="cat-findings">
                    {c.findings.map((f, i) => (
                      <li key={i}>
                        <b>{f.label}</b> — {f.detail}{' '}
                        <span className="delta">({f.pointsDelta})</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </section>

          <section>
            <h3>Measurements</h3>
            <table className="debrief-metrics">
              <tbody>
                {Object.entries(report.metrics).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h3>Event timeline</h3>
            <ul className="debrief-timeline">
              {report.timeline.map((e, i) => (
                <li key={i} className={`ev ev-${e.severity}`}>
                  <span className="ev-time">{Math.floor(e.simTimeSec / 60)}:{String(Math.floor(e.simTimeSec % 60)).padStart(2, '0')}</span>
                  <span>{e.message}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <p className="disclaimer">
          Scores are training heuristics (NON_CERTIFIED_APPROXIMATION) — not airline or Boeing criteria.
        </p>
      </div>
    </div>
  );
}
