import { useState } from 'react';
import { getSession } from '../state/connection.js';
import { useSessionStore, useSettingsStore } from '../state/stores.js';
import { deriveGuidance } from '../cockpit/guidance.js';

/** Checklist workflow + phase + training guidance (spec §14/§15/§19). */
export function ChecklistPanel(): JSX.Element {
  useSessionStore((s) => s.version); // re-render on session changes
  const mode = useSettingsStore((s) => s.mode);
  const session = getSession();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeId = selectedId ?? session.activeChecklistId ?? session.scenario.checklists[0]!.id;
  const run = session.runtime.checklistRuns.get(activeId);
  const guidance = deriveGuidance(session);
  const phase = session.scenario.phases.find((p) => p.id === session.phaseId);

  return (
    <div className="panel checklist-panel" data-testid="checklist-panel">
      <div className="panel-head">
        <span className="phase-chip" data-testid="phase-chip">
          {phase?.title ?? session.phaseId}
        </span>
        <div className="checklist-tabs">
          {session.scenario.checklists.map((c) => {
            const r = session.runtime.checklistRuns.get(c.id)!;
            return (
              <button
                key={c.id}
                type="button"
                className={`tab ${activeId === c.id ? 'active' : ''} ${r.complete ? 'done' : ''}`}
                onClick={() => setSelectedId(c.id)}
              >
                {c.title}
                {r.complete ? ' ✓' : ''}
              </button>
            );
          })}
        </div>
      </div>

      {mode !== 'evaluation' && (
        <div className="guidance" data-testid="guidance">
          {guidance.text}
        </div>
      )}

      {run && (
        <ul className="checklist-items">
          {run.items.map((item) => (
            <li key={item.definition.id} className={`ci ci-${item.status}`}>
              <span className="ci-challenge">{item.definition.challenge}</span>
              <span className="ci-dots" />
              <span className="ci-response">
                {item.dynamicResponseValue ?? item.definition.response ?? '—'}
              </span>
              {item.status === 'completed' && <span className="ci-check">✓</span>}
              {item.status === 'active' && (
                <button
                  type="button"
                  className="ci-answer"
                  data-testid={`checklist-answer-${item.definition.id}`}
                  onClick={() => session.answerChecklistItem(activeId)}
                >
                  Verify
                </button>
              )}
              {item.status === 'failed' && (
                <span className="ci-fail" title={item.failureMessage ?? ''}>
                  ✗ {item.failureMessage}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {run?.complete && <div className="checklist-complete">Checklist complete</div>}
    </div>
  );
}
