import {
  PROTOCOL_VERSION,
  parseServerMessage,
  type AircraftCommand,
  type BackendStatus,
  type ClientMessage,
  type ScenarioInitialState,
} from '@b737/shared';

/**
 * Reconnecting bridge client (spec §6): sequence numbers, command acks,
 * heartbeat latency, stale detection, and a visible connection state.
 */

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export interface WsClientEvents {
  onState: (state: import('@b737/shared').AircraftState, seq: number) => void;
  onConnectionChange: (state: ConnectionState) => void;
  onBackendStatus: (status: BackendStatus) => void;
  onWelcome: (info: { backendMode: string; stateRateHz: number }) => void;
  onCommandAck: (seq: number, ok: boolean, error?: string) => void;
  onProtocolError?: (message: string) => void;
}

export interface WsClientDiagnostics {
  latencyMs: number | null;
  lastStateSeq: number;
  stateRateHz: number;
  droppedSeqGaps: number;
  lastCommand: string | null;
  lastCommandResult: string | null;
  updatesPerSecond: number;
}

const RECONNECT_DELAY_MS = 1500;
const PING_INTERVAL_MS = 2000;
const STALE_AFTER_MS = 3000;

export class BridgeClient {
  private ws: WebSocket | null = null;
  private seq = 0;
  private closed = false;
  private pingTimer: number | null = null;
  private staleTimer: number | null = null;
  private lastMessageAt = 0;
  private stateTimestamps: number[] = [];
  readonly diagnostics: WsClientDiagnostics = {
    latencyMs: null,
    lastStateSeq: 0,
    stateRateHz: 0,
    droppedSeqGaps: 0,
    lastCommand: null,
    lastCommandResult: null,
    updatesPerSecond: 0,
  };
  connectionState: ConnectionState = 'disconnected';

  constructor(
    private readonly url: string,
    private readonly events: WsClientEvents,
  ) {}

  connect(): void {
    this.closed = false;
    this.open();
  }

  private open(): void {
    this.setConnection('connecting');
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.lastMessageAt = performance.now();
      this.send({ t: 'hello', protocolVersion: PROTOCOL_VERSION, clientName: 'b737-web' });
      this.setConnection('connected');
      this.pingTimer = window.setInterval(() => {
        this.send({ t: 'ping', seq: this.nextSeq(), sentAtMs: Date.now() });
      }, PING_INTERVAL_MS);
      this.staleTimer = window.setInterval(() => {
        if (performance.now() - this.lastMessageAt > STALE_AFTER_MS) {
          // no data — treat as disconnected so the UI shows it (spec §6)
          ws.close();
        }
      }, 1000);
    };
    ws.onmessage = (ev) => {
      this.lastMessageAt = performance.now();
      const msg = parseServerMessage(String(ev.data));
      if ('parseError' in msg) {
        this.events.onProtocolError?.(msg.parseError);
        return;
      }
      switch (msg.t) {
        case 'welcome':
          this.events.onWelcome({ backendMode: msg.backendMode, stateRateHz: msg.stateRateHz });
          return;
        case 'state': {
          if (this.diagnostics.lastStateSeq && msg.seq > this.diagnostics.lastStateSeq + 1) {
            this.diagnostics.droppedSeqGaps += 1;
          }
          this.diagnostics.lastStateSeq = msg.seq;
          const now = performance.now();
          this.stateTimestamps.push(now);
          while (this.stateTimestamps.length > 0 && this.stateTimestamps[0]! < now - 2000) {
            this.stateTimestamps.shift();
          }
          this.diagnostics.updatesPerSecond = this.stateTimestamps.length / 2;
          this.events.onState(msg.state, msg.seq);
          return;
        }
        case 'command_ack':
          this.diagnostics.lastCommandResult = msg.result.ok ? 'ok' : msg.result.error;
          this.events.onCommandAck(msg.seq, msg.result.ok, msg.result.ok ? undefined : msg.result.error);
          return;
        case 'pong':
          this.diagnostics.latencyMs = Date.now() - msg.clientSentAtMs;
          return;
        case 'backend_status':
          this.events.onBackendStatus(msg.status);
          return;
        case 'protocol_error':
          this.events.onProtocolError?.(msg.message);
          return;
      }
    };
    ws.onclose = () => {
      this.cleanupTimers();
      this.setConnection('disconnected');
      this.ws = null;
      if (!this.closed) {
        window.setTimeout(() => this.open(), RECONNECT_DELAY_MS);
      }
    };
    ws.onerror = () => {
      // onclose follows; nothing else to do
    };
  }

  close(): void {
    this.closed = true;
    this.cleanupTimers();
    this.ws?.close();
    this.ws = null;
  }

  /** Send a control command; returns its seq (matched by onCommandAck). */
  sendCommand(command: AircraftCommand): number {
    const seq = this.nextSeq();
    this.diagnostics.lastCommand = command.type;
    this.send({ t: 'command', seq, sentAtMs: Date.now(), command });
    return seq;
  }

  resetScenario(config: ScenarioInitialState): number {
    const seq = this.nextSeq();
    this.send({ t: 'reset_scenario', seq, config });
    return seq;
  }

  setPaused(paused: boolean): number {
    const seq = this.nextSeq();
    this.send({ t: 'set_paused', seq, paused });
    return seq;
  }

  private send(message: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private nextSeq(): number {
    this.seq += 1;
    return this.seq;
  }

  private setConnection(state: ConnectionState): void {
    if (this.connectionState === state) return;
    this.connectionState = state;
    this.events.onConnectionChange(state);
  }

  private cleanupTimers(): void {
    if (this.pingTimer !== null) window.clearInterval(this.pingTimer);
    if (this.staleTimer !== null) window.clearInterval(this.staleTimer);
    this.pingTimer = null;
    this.staleTimer = null;
  }
}
