import { MVP_CIRCUIT_SCENARIO } from '@b737/scenario-engine';
import { TrainingSession } from '@b737/training-engine';
import type { AircraftCommand } from '@b737/shared';
import { BridgeClient } from '../net/wsClient.js';
import { StateInterpolator } from '../net/interpolation.js';
import { useSessionStore, useSettingsStore, useSimStore } from './stores.js';
import { audioEngine } from '../audio/audioEngine.js';
import { speakEntry } from '../audio/tts.js';

/**
 * Application wiring outside React: bridge client, interpolation buffer and
 * the deterministic training session all live here as module singletons; the
 * stores mirror just enough for the UI to re-render.
 */

const BRIDGE_URL =
  (import.meta.env.VITE_BRIDGE_URL as string | undefined) ?? 'ws://127.0.0.1:8737/ws';

export const interpolator = new StateInterpolator(120);

let session = new TrainingSession(MVP_CIRCUIT_SCENARIO, { mode: 'guided' });
let spokenCount = 0;

export function getSession(): TrainingSession {
  return session;
}

export function resetSession(): void {
  const mode = useSettingsStore.getState().mode;
  session = new TrainingSession(MVP_CIRCUIT_SCENARIO, { mode });
  spokenCount = 0;
  client.resetScenario(MVP_CIRCUIT_SCENARIO.initialState);
  useSessionStore.getState().setShowDebrief(false);
  useSessionStore.getState().setPaused(false);
  useSessionStore.getState().bump(session.version, session.phaseId);
}

export const client = new BridgeClient(BRIDGE_URL, {
  onConnectionChange: (c) => useSimStore.getState().setConnection(c),
  onWelcome: ({ backendMode, stateRateHz }) =>
    useSimStore.getState().setWelcome(backendMode, stateRateHz),
  onBackendStatus: (status) => useSimStore.getState().setBackendStatus(status),
  onCommandAck: (_seq, ok, error) => {
    if (!ok && error) useSettingsStore.getState().setLastCommandRejection(error);
  },
  onState: (state, seq) => {
    interpolator.push(state);
    useSimStore.getState().setStateSample(state, seq);
    session.mode = useSettingsStore.getState().mode;
    session.update(state);
    audioEngine.update(state);
    const store = useSessionStore.getState();
    if (store.version !== session.version) {
      store.bump(session.version, session.phaseId);
      // speak any new FO/ATC lines (optional, offline Web Speech)
      if (useSettingsStore.getState().ttsEnabled) {
        for (; spokenCount < session.transcript.length; spokenCount++) {
          const entry = session.transcript[spokenCount]!;
          if (entry.speaker === 'first_officer' || entry.speaker === 'atc') speakEntry(entry);
        }
      } else {
        spokenCount = session.transcript.length;
      }
      if (session.complete && !store.showDebrief) store.setShowDebrief(true);
    }
  },
  onProtocolError: (message) => console.warn('[bridge protocol]', message),
});

/** Send a validated command to the bridge (single entry point for the UI). */
export function sendCommand(command: AircraftCommand): void {
  client.sendCommand(command);
  if (command.type === 'set_control_axis') {
    session.notifyAxisInput(command.axis, command.valueNorm);
  }
}

export function startConnection(): void {
  client.connect();
}
