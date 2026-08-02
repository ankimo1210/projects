import { audioEngine } from '../audio/audioEngine.js';
import { getSession, resetSession, setPaused as setPausedAcked } from '../state/connection.js';
import { useSessionStore, useSettingsStore, useSimStore } from '../state/stores.js';
import type { TrainingMode } from '@b737/training-engine';

/** Bottom status bar: backend, scenario, pause/reset/debrief (spec §19). */
export function StatusBar(): JSX.Element {
  const connection = useSimStore((s) => s.connection);
  const backendMode = useSimStore((s) => s.backendMode);
  const backendStatus = useSimStore((s) => s.backendStatus);
  const latest = useSimStore((s) => s.latest);
  const paused = useSessionStore((s) => s.paused);
  const setShowDebrief = useSessionStore((s) => s.setShowDebrief);
  useSessionStore((s) => s.version);
  const settings = useSettingsStore();
  const session = getSession();

  const connClass =
    connection === 'connected' && (backendStatus?.connected ?? true)
      ? 'ok'
      : connection === 'connecting'
        ? 'warn'
        : 'bad';

  return (
    <footer className="status-bar" data-testid="status-bar">
      <span className={`conn conn-${connClass}`} data-testid="conn-status">
        ●{' '}
        {connection === 'connected'
          ? `${backendMode ?? '?'} backend`
          : connection === 'connecting'
            ? 'connecting…'
            : 'DISCONNECTED'}
      </span>
      <span className="scenario-name">{session.scenario.title}</span>
      <span data-testid="sim-time">t+{latest ? Math.floor(latest.simTimeSec) : 0}s</span>

      <select
        aria-label="training mode"
        value={settings.mode}
        onChange={(e) => settings.setMode(e.target.value as TrainingMode)}
        data-testid="mode-select"
      >
        <option value="guided">Guided</option>
        <option value="assisted">Assisted</option>
        <option value="evaluation">Evaluation</option>
      </select>

      <button
        type="button"
        onClick={() => {
          if (settings.soundEnabled) {
            audioEngine.stop();
            settings.setSoundEnabled(false);
          } else {
            audioEngine.start();
            settings.setSoundEnabled(true);
          }
        }}
      >
        {settings.soundEnabled ? '🔊' : '🔇'}
      </button>

      <button type="button" data-testid="pause-btn" onClick={() => void setPausedAcked(!paused)}>
        {paused ? '▶ Resume' : '⏸ Pause'}
      </button>
      <button type="button" data-testid="reset-btn" onClick={() => void resetSession()}>
        ↺ Reset
      </button>
      <button type="button" data-testid="debrief-btn" onClick={() => setShowDebrief(true)}>
        Debrief
      </button>
      <button
        type="button"
        title="diagnostics (backquote)"
        onClick={() => settings.toggleDiagnostics()}
      >
        ⚙
      </button>
      {settings.lastCommandRejection && (
        <span className="cmd-rejection" data-testid="cmd-rejection">
          ⚠ {settings.lastCommandRejection}
        </span>
      )}
      <span className="disclaimer">NOT A CERTIFIED TRAINING DEVICE — hobby simulation</span>
    </footer>
  );
}
