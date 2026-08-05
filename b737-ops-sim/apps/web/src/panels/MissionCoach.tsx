import { useEffect, useRef, useState } from 'react';
import type { GuidanceHint } from '../cockpit/guidance.js';
import { getSession } from '../state/connection.js';
import { useSessionStore, useSettingsStore } from '../state/stores.js';

/** Beginner-facing objective HUD: one action, one reason, one success gate. */
export function MissionCoach({ guidance }: { guidance: GuidanceHint }): JSX.Element | null {
  useSessionStore((s) => s.version);
  const mode = useSettingsStore((s) => s.mode);
  const [expanded, setExpanded] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const previousId = useRef(guidance.id);
  const session = getSession();
  const phaseIndex = Math.max(
    0,
    session.scenario.phases.findIndex((phase) => phase.id === session.phaseId),
  );
  const phaseCount = session.scenario.phases.length;
  const phase = session.scenario.phases[phaseIndex];
  const progress = session.complete
    ? 100
    : Math.round((phaseIndex / Math.max(1, phaseCount - 1)) * 100);

  useEffect(() => {
    if (previousId.current === guidance.id) return;
    previousId.current = guidance.id;
    setCelebrating(true);
    setExpanded(false);
    const timer = window.setTimeout(() => setCelebrating(false), 1400);
    return () => window.clearTimeout(timer);
  }, [guidance.id]);

  if (mode === 'evaluation') return null;

  const revealTarget = (): void => {
    const settings = useSettingsStore.getState();
    if (
      settings.panelsCollapsed &&
      ['checklist', 'radio', 'systems', 'fms'].includes(guidance.target)
    ) {
      settings.togglePanels();
    }
    if (['systems', 'fms'].includes(guidance.target) && !settings.showOverhead) {
      settings.toggleOverhead();
    }

    window.setTimeout(() => {
      const selector = targetSelector(guidance);
      const target = document.querySelector<HTMLElement>(selector);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      target.classList.remove('coach-focus');
      // Restart the animation when SHOW ME is pressed repeatedly.
      void target.offsetWidth;
      target.classList.add('coach-focus');
      window.setTimeout(() => target.classList.remove('coach-focus'), 2200);
    }, 80);
  };

  return (
    <aside
      className={`mission-coach ${celebrating ? 'mission-celebrating' : ''}`}
      data-testid="mission-coach"
      aria-live="polite"
    >
      {celebrating && <div className="mission-complete-flash">✓ OBJECTIVE COMPLETE</div>}
      <div className="mission-topline">
        <span className="mission-kicker">NEXT ACTION / 次にやること</span>
        <span className="mission-step">
          PHASE {phaseIndex + 1}/{phaseCount}
        </span>
      </div>
      <div className="mission-progress" aria-label={`scenario progress ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="mission-phase">{phase?.title ?? session.phaseId}</div>
      <h2>{guidance.title}</h2>
      <p className="mission-action">{guidance.text}</p>

      {guidance.metrics.length > 0 && (
        <div className="mission-metrics">
          {guidance.metrics.map((metric) => (
            <span className={`mission-metric metric-${metric.tone ?? 'normal'}`} key={metric.label}>
              <small>{metric.label}</small>
              <strong>{metric.value}</strong>
            </span>
          ))}
        </div>
      )}

      {expanded && (
        <div className="mission-help" data-testid="mission-help">
          <p>
            <strong>WHY</strong> {guidance.detail}
          </p>
          <p>
            <strong>SUCCESS</strong> {guidance.success}
          </p>
        </div>
      )}

      <div className="mission-actions">
        <button type="button" className="mission-show" onClick={revealTarget}>
          ◎ 場所を表示
        </button>
        <button
          type="button"
          className="mission-help-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? '説明を閉じる' : '? なぜ？ / 完了条件'}
        </button>
      </div>
    </aside>
  );
}

function targetSelector(guidance: GuidanceHint): string {
  if (guidance.controlId) return `[data-control-id="${guidance.controlId}"]`;
  switch (guidance.target) {
    case 'checklist':
      return '[data-testid="checklist-panel"]';
    case 'radio':
      return '[data-testid="transcript-panel"]';
    case 'systems':
      return '[data-testid="overhead-panel"]';
    case 'fms':
      return '[data-testid="fms-panel"]';
    case 'debrief':
      return '[data-testid="debrief-btn"]';
    case 'control':
      return '[data-testid="controls-panel"]';
    case 'cockpit':
      return '[data-testid="sim-canvas"]';
    default:
      return '[data-testid="instrument-row"]';
  }
}
