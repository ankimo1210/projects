import { lazy, Suspense, useEffect } from 'react';
import { vSpeedsForWeight } from '@b737/shared';
import { Pfd } from './instruments/Pfd.js';
import { Nd } from './instruments/Nd.js';
import { EngineDisplay } from './instruments/EngineDisplay.js';
import { Mcp } from './instruments/Mcp.js';
import { ControlsPanel } from './cockpit/ControlsPanel.js';
import { ChecklistPanel } from './panels/ChecklistPanel.js';
import { TranscriptPanel } from './panels/TranscriptPanel.js';
import { StatusBar } from './panels/StatusBar.js';
import { DebriefView } from './panels/DebriefView.js';
import { DiagnosticsPanel } from './panels/DiagnosticsPanel.js';
import { OverheadPanel } from './panels/OverheadPanel.js';
import { FmsPanel } from './panels/FmsPanel.js';
import { MissionCoach } from './panels/MissionCoach.js';
import { deriveGuidance } from './cockpit/guidance.js';
import { getSession } from './state/connection.js';
import { useSessionStore, useSettingsStore, useSimStore } from './state/stores.js';

const CockpitScene = lazy(async () => {
  const module = await import('./sim3d/CockpitScene.js');
  return { default: module.CockpitScene };
});

export function App(): JSX.Element {
  const state = useSimStore((s) => s.latest);
  const connection = useSimStore((s) => s.connection);
  useSessionStore((s) => s.version);
  const panelsCollapsed = useSettingsStore((s) => s.panelsCollapsed);
  const showOverhead = useSettingsStore((s) => s.showOverhead);
  const togglePanels = useSettingsStore((s) => s.togglePanels);
  const toggleDiagnostics = useSettingsStore((s) => s.toggleDiagnostics);
  const session = getSession();
  const guidance = deriveGuidance(session);
  const vSpeeds = vSpeedsForWeight(session.scenario.initialState.grossWeightLb);

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.code === 'Backquote') toggleDiagnostics();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleDiagnostics]);

  return (
    <div className="app">
      <main className="sim-area">
        <Suspense fallback={<div className="scene-loading">Loading 3D cockpit…</div>}>
          <CockpitScene />
        </Suspense>
        <MissionCoach guidance={guidance} />
        {connection !== 'connected' && (
          <div className="disconnect-overlay" data-testid="disconnect-overlay">
            <div>
              <h2>
                {connection === 'connecting' ? 'Connecting to bridge…' : 'Bridge disconnected'}
              </h2>
              <p>
                Start it with <code>pnpm dev</code> (mock) — see README. Reconnecting automatically…
              </p>
            </div>
          </div>
        )}
        <DiagnosticsPanel />
        <button
          type="button"
          className="collapse-btn"
          onClick={togglePanels}
          title="collapse/expand lower panels"
        >
          {panelsCollapsed ? '▲ panels' : '▼ panels'}
        </button>
      </main>

      {state && (
        <section className="instrument-row" data-testid="instrument-row">
          <Pfd state={state} vSpeeds={vSpeeds} />
          <Nd state={state} />
          <EngineDisplay state={state} />
          <div className="right-stack">
            <Mcp state={state} />
            <ControlsPanel state={state} guidedControlId={guidance.controlId} />
          </div>
        </section>
      )}

      {!panelsCollapsed && (
        <section className={`lower-panels ${showOverhead ? 'with-overhead' : ''}`}>
          <ChecklistPanel />
          <TranscriptPanel />
          {showOverhead && state && (
            <OverheadPanel state={state} guidedControlId={guidance.controlId} />
          )}
          {showOverhead && state && <FmsPanel state={state} />}
        </section>
      )}

      <StatusBar />
      <DebriefView />
    </div>
  );
}
