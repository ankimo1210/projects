import { create } from 'zustand';
import type { AircraftState, BackendStatus } from '@b737/shared';
import type { ConnectionState } from '../net/wsClient.js';
import type { TrainingMode } from '@b737/training-engine';

/** Live simulation feed (updated per state message, ~30 Hz). */
interface SimStore {
  connection: ConnectionState;
  backendMode: string | null;
  backendStatus: BackendStatus | null;
  stateRateHz: number;
  latest: AircraftState | null;
  seq: number;
  setConnection: (c: ConnectionState) => void;
  setWelcome: (mode: string, rateHz: number) => void;
  setBackendStatus: (s: BackendStatus) => void;
  setStateSample: (s: AircraftState, seq: number) => void;
}

export const useSimStore = create<SimStore>((set) => ({
  connection: 'disconnected',
  backendMode: null,
  backendStatus: null,
  stateRateHz: 0,
  latest: null,
  seq: 0,
  setConnection: (connection) => set({ connection }),
  setWelcome: (backendMode, stateRateHz) => set({ backendMode, stateRateHz }),
  setBackendStatus: (backendStatus) => set({ backendStatus }),
  setStateSample: (latest, seq) => set({ latest, seq }),
}));

/** Training session mirror: bump `version` to re-render session consumers. */
interface SessionStore {
  version: number;
  phaseId: string;
  paused: boolean;
  showDebrief: boolean;
  bump: (version: number, phaseId: string) => void;
  setPaused: (paused: boolean) => void;
  setShowDebrief: (show: boolean) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  version: 0,
  phaseId: 'before_takeoff',
  paused: false,
  showDebrief: false,
  bump: (version, phaseId) => set({ version, phaseId }),
  setPaused: (paused) => set({ paused }),
  setShowDebrief: (showDebrief) => set({ showDebrief }),
}));

/** User settings + UI chrome state. */
interface SettingsStore {
  mode: TrainingMode;
  soundEnabled: boolean;
  ttsEnabled: boolean;
  showDiagnostics: boolean;
  panelsCollapsed: boolean;
  /** Overhead/systems panel visible (spec §22 Phase 4). */
  showOverhead: boolean;
  toggleOverhead: () => void;
  lastCommandRejection: string | null;
  setMode: (m: TrainingMode) => void;
  setSoundEnabled: (v: boolean) => void;
  setTtsEnabled: (v: boolean) => void;
  toggleDiagnostics: () => void;
  togglePanels: () => void;
  setLastCommandRejection: (msg: string | null) => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  mode: 'guided',
  soundEnabled: false,
  ttsEnabled: false,
  showDiagnostics: false,
  panelsCollapsed: false,
  showOverhead: false,
  toggleOverhead: () => set((s) => ({ showOverhead: !s.showOverhead })),
  lastCommandRejection: null,
  setMode: (mode) => set({ mode }),
  setSoundEnabled: (soundEnabled) => set({ soundEnabled }),
  setTtsEnabled: (ttsEnabled) => set({ ttsEnabled }),
  toggleDiagnostics: () => set((s) => ({ showDiagnostics: !s.showDiagnostics })),
  togglePanels: () => set((s) => ({ panelsCollapsed: !s.panelsCollapsed })),
  setLastCommandRejection: (lastCommandRejection) => set({ lastCommandRejection }),
}));
