import { MVP_CIRCUIT_SCENARIO } from '@b737/scenario-engine';
import { TrainingSession } from '@b737/training-engine';
import type { AircraftCommand } from '@b737/shared';
import { BridgeClient } from '../net/wsClient.js';
import { StateInterpolator } from '../net/interpolation.js';
import { useSessionStore, useSettingsStore, useSimStore } from './stores.js';
import { audioEngine } from '../audio/audioEngine.js';
import { speakEntry } from '../audio/tts.js';
import { controlTargets } from '../input/controlTargets.js';

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

/**
 * Reset the flight. The training session is only replaced once the BACKEND has
 * confirmed the reset — otherwise a reset issued while disconnected silently
 * detached the session from the aircraft (R-16).
 */
export async function resetSession(): Promise<boolean> {
  const ack = await client.resetScenario(MVP_CIRCUIT_SCENARIO.initialState);
  if (!ack.ok) {
    useSettingsStore.getState().setLastCommandRejection(ack.error ?? 'scenario reset failed');
    return false;
  }
  const mode = useSettingsStore.getState().mode;
  session = new TrainingSession(MVP_CIRCUIT_SCENARIO, { mode });
  spokenCount = 0;
  controlTargets.reset();
  useSessionStore.getState().setShowDebrief(false);
  useSessionStore.getState().setPaused(false);
  useSessionStore.getState().bump(session.version, session.phaseId);
  return true;
}

/** Pause/resume, committed to the UI only after the bridge confirms (R-16). */
export async function setPaused(paused: boolean): Promise<boolean> {
  const ack = await client.setPaused(paused);
  if (!ack.ok) {
    useSettingsStore.getState().setLastCommandRejection(ack.error ?? 'pause failed');
    return false;
  }
  useSessionStore.getState().setPaused(paused);
  return true;
}

export const client = new BridgeClient(BRIDGE_URL, {
  onConnectionChange: (c) => useSimStore.getState().setConnection(c),
  onWelcome: ({ backendMode, stateRateHz }) =>
    useSimStore.getState().setWelcome(backendMode, stateRateHz),
  onBackendStatus: (status) => useSimStore.getState().setBackendStatus(status),
  onCommandAck: (seq, ok, error) => {
    // a successful command clears a stale rejection banner
    if (ok) useSettingsStore.getState().setLastCommandRejection(null);
    else if (error) useSettingsStore.getState().setLastCommandRejection(error);
    const axis = pendingAxisCommands.get(seq);
    if (axis) {
      pendingAxisCommands.delete(seq);
      if (ok) session.notifyAxisInput(axis.axis, axis.valueNorm);
    }
  },
  onState: (state, seq) => {
    interpolator.push(state);
    controlTargets.observe(state);
    useSimStore.getState().setStateSample(state, seq);
    session.mode = useSettingsStore.getState().mode;
    session.update(state);
    audioEngine.update(state);
    const store = useSessionStore.getState();
    if (store.version !== session.version) {
      store.bump(session.version, session.phaseId);
      // voice new FO/ATC lines: GPWS altitude callouts use the real samples
      // when available; everything else uses offline Web Speech (optional)
      const ttsEnabled = useSettingsStore.getState().ttsEnabled;
      for (; spokenCount < session.transcript.length; spokenCount++) {
        const entry = session.transcript[spokenCount]!;
        const calloutAlt = entry.relatedEventId?.match(/^callout:ra_(\d+)$/);
        if (calloutAlt && audioEngine.playAltitudeCallout(Number(calloutAlt[1]))) continue;
        if (ttsEnabled && (entry.speaker === 'first_officer' || entry.speaker === 'atc')) {
          speakEntry(entry);
        }
      }
      if (session.complete && !store.showDebrief) store.setShowDebrief(true);
    }
  },
  onProtocolError: (message) => console.warn('[bridge protocol]', message),
});

/** Send a validated command to the bridge (single entry point for the UI). */
export function sendCommand(command: AircraftCommand): void {
  const seq = client.sendCommand(command);
  if (command.type === 'set_control_axis') {
    // The flight-control check counts deflections the AIRCRAFT accepted, not
    // keystrokes the bridge may have rate-limited away (R-18).
    pendingAxisCommands.set(seq, { axis: command.axis, valueNorm: command.valueNorm });
    if (pendingAxisCommands.size > 200) {
      const oldest = pendingAxisCommands.keys().next().value;
      if (oldest !== undefined) pendingAxisCommands.delete(oldest);
    }
  }
}

const pendingAxisCommands = new Map<
  number,
  { axis: 'pitch' | 'roll' | 'yaw'; valueNorm: number }
>();

/**
 * Send a command and play its cockpit sound only if the aircraft accepted it —
 * a gear lever that is locked on the ground must not click (review note).
 */
export type ClickSound = 'click' | 'lever' | 'rotary' | 'flap_lever' | 'gear_lever';

export function sendCommandWithSound(command: AircraftCommand, sound: ClickSound): void {
  void client.sendCommandAcked(command).then((ack) => {
    if (ack.ok) audioEngine.click(sound);
  });
}

export function startConnection(): void {
  client.connect();
}
