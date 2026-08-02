import {
  AircraftStateSchema,
  flapDetentToNorm,
  flapNormToNearestDetent,
  normalizeDeg360,
  type AircraftCommand,
  type AircraftState,
  type AutobrakeSetting,
  type BackendStatus,
  type CommandResult,
  type ScenarioInitialState,
} from '@b737/shared';
import { WebSocket } from 'ws';
import type { FlightBackend } from '../backend.js';
import type { FgCommandEntry, PropertyMap } from './propertyMap.js';

/**
 * FlightBackend speaking FlightGear's built-in httpd WebSocket property
 * interface (launch FlightGear with `--httpd=<port>`; endpoint
 * `ws://host:port/PropertyListener`).
 *
 * Wire semantics (FlightGear "Phi" interface):
 *   → {"command":"addListener","node":"/position/altitude-ft"}
 *   → {"command":"get","node":"/position/altitude-ft"}
 *   → {"command":"set","node":"/controls/flight/flaps","value":0.375}
 *   ← {"path":"/position/altitude-ft","value":13.2, ...}
 *
 * All FG property paths come from the versioned property map
 * (config/flightgear/737-800-property-map.json) — none are hardcoded here.
 */

export interface FlightGearBackendOptions {
  host: string;
  httpPort: number;
  propertyMap: PropertyMap;
  /** Rate at which assembled AircraftState samples are published. */
  stateRateHz?: number;
  reconnectDelayMs?: number;
  /** Consider the connection stale after this long without any FG message. */
  staleAfterMs?: number;
  log?: (level: 'info' | 'warn' | 'error', msg: string) => void;
}

type FgValue = number | boolean | string;

export class FlightGearBackend implements FlightBackend {
  private readonly opts: Required<Omit<FlightGearBackendOptions, 'log'>> & {
    log: (level: 'info' | 'warn' | 'error', msg: string) => void;
  };
  private ws: WebSocket | null = null;
  private cache = new Map<string, FgValue>();
  private listeners = new Set<(state: AircraftState) => void>();
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private lastMessageAtMs: number | null = null;
  private lastStateAtMs: number | null = null;
  private wantConnected = false;
  private simStartMs: number | null = null;
  /**
   * Monotonic socket id. Handlers belonging to a superseded socket must not
   * mutate `ws`/`cache`, otherwise a late close event from the previous
   * attempt tears down the connection that replaced it (R-04).
   */
  private generation = 0;
  /** State keys the property map does not mark `optional`. */
  private readonly requiredKeys: string[];
  private loggedInvalidState = false;

  constructor(options: FlightGearBackendOptions) {
    this.opts = {
      host: options.host,
      httpPort: options.httpPort,
      propertyMap: options.propertyMap,
      stateRateHz: options.stateRateHz ?? 30,
      reconnectDelayMs: options.reconnectDelayMs ?? 2000,
      staleAfterMs: options.staleAfterMs ?? 3000,
      log: options.log ?? (() => undefined),
    };
    this.requiredKeys = Object.entries(this.opts.propertyMap.state)
      .filter(([, entry]) => entry.optional !== true)
      .map(([key]) => key);
  }

  get url(): string {
    return `ws://${this.opts.host}:${this.opts.httpPort}/PropertyListener`;
  }

  /**
   * Idempotent. The backend owns reconnection: `connect()` resolves once the
   * first attempt has been made, whether or not it succeeded, and keeps
   * retrying in the background. Callers watch `getStatus()`; they must not run
   * a competing retry loop (R-04).
   */
  async connect(): Promise<void> {
    this.wantConnected = true;
    if (!this.publishTimer) {
      this.publishTimer = setInterval(() => this.publish(), 1000 / this.opts.stateRateHz);
    }
    await this.attempt();
  }

  private async attempt(): Promise<void> {
    if (!this.wantConnected) return;
    const readyState = this.ws?.readyState;
    if (readyState === WebSocket.OPEN || readyState === WebSocket.CONNECTING) return;
    try {
      await this.openSocket();
    } catch (err) {
      this.opts.log('warn', `FlightGear connect failed: ${String(err)}`);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (!this.wantConnected || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.attempt();
    }, this.opts.reconnectDelayMs);
  }

  private openSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      const generation = ++this.generation;
      const isCurrent = (): boolean => this.generation === generation;
      const ws = new WebSocket(this.url);
      this.ws = ws;
      const onOpenError = (err: Error) => reject(err);
      ws.once('error', onOpenError);
      ws.on('open', () => {
        ws.removeListener('error', onOpenError);
        if (!isCurrent()) {
          ws.close();
          resolve();
          return;
        }
        this.opts.log('info', `connected to FlightGear at ${this.url}`);
        this.lastMessageAtMs = Date.now();
        if (this.simStartMs === null) this.simStartMs = Date.now();
        for (const entry of Object.values(this.opts.propertyMap.state)) {
          ws.send(JSON.stringify({ command: 'addListener', node: entry.fgProp }));
          ws.send(JSON.stringify({ command: 'get', node: entry.fgProp }));
        }
        ws.on('error', (err) => this.opts.log('error', `FlightGear socket error: ${err.message}`));
        resolve();
      });
      ws.on('message', (data) => {
        if (!isCurrent()) return;
        this.lastMessageAtMs = Date.now();
        try {
          const msg = JSON.parse(String(data)) as { path?: string; value?: FgValue };
          if (typeof msg.path === 'string' && msg.value !== undefined) {
            this.cache.set(msg.path, msg.value);
          }
        } catch {
          // Non-JSON frames from FG are ignored.
        }
      });
      ws.on('close', () => {
        if (!isCurrent()) return;
        this.opts.log('warn', 'FlightGear socket closed');
        this.ws = null;
        // Values from the previous session must never be mixed into a new one
        // or re-published with fresh timestamps (R-05).
        this.cache.clear();
        this.lastMessageAtMs = null;
        this.scheduleReconnect();
      });
    });
  }

  async disconnect(): Promise<void> {
    this.wantConnected = false;
    // Retire every in-flight socket: their handlers become no-ops.
    this.generation += 1;
    if (this.publishTimer) clearInterval(this.publishTimer);
    this.publishTimer = null;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.ws?.close();
    this.ws = null;
    this.cache.clear();
    this.lastMessageAtMs = null;
  }

  /** State keys whose FG property has not arrived yet. */
  private missingRequired(): string[] {
    return this.requiredKeys.filter((key) => {
      const entry = this.opts.propertyMap.state[key];
      return entry === undefined || !this.cache.has(entry.fgProp);
    });
  }

  private isStale(): boolean {
    return (
      this.lastMessageAtMs === null || Date.now() - this.lastMessageAtMs > this.opts.staleAfterMs
    );
  }

  getStatus(): BackendStatus {
    const stale = this.isStale();
    const socketOpen = this.ws?.readyState === WebSocket.OPEN;
    const missing = socketOpen ? this.missingRequired() : [];
    const streaming = socketOpen && !stale && missing.length === 0;
    return {
      mode: 'flightgear',
      connected: streaming,
      detail: !socketOpen
        ? `not connected to ${this.url}`
        : stale
          ? 'socket open but no recent data (is the sim paused or crashed?)'
          : missing.length > 0
            ? `waiting for ${missing.length} property/ies (first: ${missing[0]})`
            : `streaming from ${this.url}`,
      lastStateAgeMs: this.lastStateAtMs === null ? null : Date.now() - this.lastStateAtMs,
      stateRateHz: this.opts.stateRateHz,
    };
  }

  subscribe(listener: (state: AircraftState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  sendCommand(command: AircraftCommand): Promise<CommandResult> {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return Promise.resolve({ ok: false, error: 'FlightGear not connected' });
    }
    const writes = this.commandToWrites(command);
    if ('error' in writes) return Promise.resolve({ ok: false, error: writes.error });
    for (const { node, value } of writes.writes) {
      ws.send(JSON.stringify({ command: 'set', node, value }));
    }
    return Promise.resolve({ ok: true });
  }

  /** Resolve command → FG property writes using the versioned map. */
  private commandToWrites(
    command: AircraftCommand,
  ): { writes: { node: string; value: FgValue }[] } | { error: string } {
    const cmds = this.opts.propertyMap.commands;
    const lookup = (key: string): FgCommandEntry | undefined => cmds[key];
    const simple = (
      key: string,
      value: FgValue,
    ): { writes: { node: string; value: FgValue }[] } | { error: string } => {
      const entry = lookup(key);
      if (!entry) return { error: `no property mapping for command '${key}'` };
      const scaled =
        typeof value === 'number' && entry.scale !== undefined ? value * entry.scale : value;
      return { writes: entry.fgProps.map((node) => ({ node, value: scaled })) };
    };
    switch (command.type) {
      case 'set_control_axis':
        return simple(`set_control_axis.${command.axis}`, command.valueNorm);
      case 'set_throttle':
        return simple('set_throttle', command.valueNorm);
      case 'set_brakes':
        return simple('set_brakes', command.valueNorm);
      case 'set_parking_brake':
        return simple('set_parking_brake', command.engaged);
      case 'set_flaps':
        return simple('set_flaps', flapDetentToNorm(command.detent as never));
      case 'set_gear':
        return simple('set_gear', command.down);
      case 'set_speedbrake':
        return simple('set_speedbrake', command.leverNorm);
      case 'set_speedbrake_armed':
        return simple('set_speedbrake_armed', command.armed);
      case 'set_reverse_thrust':
        return simple('set_reverse_thrust', command.leverNorm);
      case 'set_autobrake':
        return simple('set_autobrake', autobrakeToFgValue(command.setting));
      case 'set_mcp_speed':
        return simple('set_mcp_speed', command.speedKt);
      case 'set_mcp_heading':
        return simple('set_mcp_heading', normalizeDeg360(command.headingDeg));
      case 'set_mcp_altitude':
        return simple('set_mcp_altitude', command.altitudeFt);
      case 'set_mcp_vertical_speed':
        return simple('set_mcp_vertical_speed', command.verticalSpeedFpm);
      case 'set_autopilot':
        return simple('set_autopilot', command.engaged);
      case 'set_flight_director':
        return simple('set_flight_director', command.on);
      case 'set_ap_approach_mode':
        return simple('set_ap_approach_mode', command.armed);
      case 'set_toga':
        return simple('set_toga', command.engaged);
      case 'set_light':
        return simple(`set_light.${command.light}`, command.on);
    }
  }

  /**
   * Scenario reset over the property interface is unreliable (repositioning a
   * running FlightGear requires fgcommands not exposed here). We set what we
   * safely can and direct the user to the launch script for a clean restart.
   */
  /** Uses FlightGear's freeze properties when mapped in the property map. */
  setPaused(paused: boolean): Promise<CommandResult> {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return Promise.resolve({ ok: false, error: 'FlightGear not connected' });
    }
    const entry = this.opts.propertyMap.commands['set_paused'];
    if (!entry) return Promise.resolve({ ok: false, error: 'set_paused not mapped' });
    for (const node of entry.fgProps) {
      ws.send(JSON.stringify({ command: 'set', node, value: paused }));
    }
    return Promise.resolve({ ok: true });
  }

  resetScenario(config: ScenarioInitialState): Promise<void> {
    this.opts.log(
      'warn',
      `FlightGear resetScenario is best-effort; restart FlightGear with scripts/launch-flightgear.ps1 for a clean ${config.airportIcao} ${config.runwayId} start`,
    );
    void this.sendCommand({ type: 'set_flaps', detent: config.flapDetent as never });
    void this.sendCommand({ type: 'set_parking_brake', engaged: config.parkingBrakeSet });
    return Promise.resolve();
  }

  // ------------------------------------------------------------ state assembly

  private num(stateKey: string, fallback = 0): number {
    const entry = this.opts.propertyMap.state[stateKey];
    if (!entry) return fallback;
    const raw = this.cache.get(entry.fgProp);
    if (raw === undefined || raw === null) return fallback;
    const n = typeof raw === 'boolean' ? (raw ? 1 : 0) : Number(raw);
    if (Number.isNaN(n)) return fallback;
    return entry.scale !== undefined ? n * entry.scale : n;
  }

  private numOrNull(stateKey: string): number | null {
    const entry = this.opts.propertyMap.state[stateKey];
    if (!entry) return null;
    const raw = this.cache.get(entry.fgProp);
    if (raw === undefined || raw === null) return null;
    const n = typeof raw === 'boolean' ? (raw ? 1 : 0) : Number(raw);
    if (Number.isNaN(n)) return null;
    return entry.scale !== undefined ? n * entry.scale : n;
  }

  private bool(stateKey: string, fallback = false): boolean {
    const entry = this.opts.propertyMap.state[stateKey];
    if (!entry) return fallback;
    const raw = this.cache.get(entry.fgProp);
    if (raw === undefined || raw === null) return fallback;
    if (typeof raw === 'boolean') return raw;
    if (typeof raw === 'number') return raw !== 0;
    return raw === 'true' || raw === '1';
  }

  private publish(): void {
    // A partially-populated or stale cache must never be dressed up as a fresh
    // sample: publishing 0-filled defaults with an advancing timestamp is worse
    // than publishing nothing (R-05).
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    if (this.isStale()) return;
    if (this.missingRequired().length > 0) return;
    const now = Date.now();
    const flapsActualNorm = this.num('controls.flapsActualNorm');
    const locInRange = this.bool('nav.locInRange');
    const gsInRange = this.bool('nav.gsInRange');
    // Prefer FlightGear's own simulation clock; fall back to wall clock only
    // when the map has no sim-time property (older maps).
    const fgSimTimeSec = this.numOrNull('sim.simTimeSec');
    const state: AircraftState = {
      timestampMs: now,
      simTimeSec: fgSimTimeSec ?? (this.simStartMs === null ? 0 : (now - this.simStartMs) / 1000),
      position: {
        latDeg: this.num('position.latDeg'),
        lonDeg: this.num('position.lonDeg'),
        altitudeFtMsl: this.num('position.altitudeFtMsl'),
        radioAltitudeFt: Math.max(0, this.num('position.radioAltitudeFt')),
      },
      attitude: {
        pitchDeg: this.num('attitude.pitchDeg'),
        rollDeg: this.num('attitude.rollDeg'),
        headingDegMag: normalizeDeg360(this.num('attitude.headingDegMag')),
        groundTrackDegMag: normalizeDeg360(this.num('attitude.groundTrackDegMag')),
        aoaDeg: this.numOrNull('attitude.aoaDeg'),
      },
      speeds: {
        iasKt: this.num('speeds.iasKt'),
        gsKt: this.num('speeds.gsKt'),
        verticalSpeedFpm: this.num('speeds.verticalSpeedFpm'),
      },
      weightOnWheels: this.bool('weightOnWheels', true),
      engines: {
        left: {
          n1Pct: this.num('engines.left.n1Pct'),
          throttleLeverNorm: this.num('engines.left.throttleLeverNorm'),
          reverserNorm: this.num('engines.left.reverserNorm'),
        },
        right: {
          n1Pct: this.num('engines.right.n1Pct'),
          throttleLeverNorm: this.num('engines.right.throttleLeverNorm'),
          reverserNorm: this.num('engines.right.reverserNorm'),
        },
      },
      controls: {
        flapHandleDetent: flapNormToNearestDetent(this.num('controls.flapHandleNorm')),
        flapsActualNorm,
        gearLeverDown: this.bool('controls.gearLeverDown', true),
        gearPositionNorm: this.num('controls.gearPositionNorm', 1),
        speedbrakeLeverNorm: this.num('controls.speedbrakeLeverNorm'),
        speedbrakeArmed: this.bool('controls.speedbrakeArmed'),
        spoilersDeployedNorm: this.num('controls.spoilersDeployedNorm'),
        parkingBrakeSet: this.bool('controls.parkingBrakeSet'),
        brakeNorm: Math.max(
          this.num('controls.brakeLeftNorm'),
          this.num('controls.brakeRightNorm'),
        ),
        autobrake: fgValueToAutobrake(this.num('controls.autobrakeRaw', 0)),
      },
      mcp: {
        selSpeedKt: this.num('mcp.selSpeedKt'),
        selHeadingDeg: this.num('mcp.selHeadingDeg'),
        selAltitudeFt: this.num('mcp.selAltitudeFt'),
        selVerticalSpeedFpm: this.num('mcp.selVerticalSpeedFpm'),
        autopilotEngaged: this.bool('mcp.autopilotEngaged'),
        flightDirectorOn: this.bool('mcp.flightDirectorOn'),
        approachArmed: this.bool('mcp.approachArmed'),
        // Mode annunciation is aircraft-specific; FlightGear mode reports null
        // unless the property map provides it (spec §22 Phase 3, D2).
        rollMode: null,
        pitchMode: null,
      },
      nav: {
        ilsTuned: locInRange || gsInRange,
        locDeviationDots: locInRange ? this.num('nav.locDeviationDots') : null,
        gsDeviationDots: gsInRange ? this.num('nav.gsDeviationDots') : null,
      },
      lights: {
        landing: this.bool('lights.landing'),
        taxi: this.bool('lights.taxi'),
        strobe: this.bool('lights.strobe'),
        beacon: this.bool('lights.beacon'),
      },
      airport: { icao: null, runwayId: null },
    };
    const validated = AircraftStateSchema.safeParse(state);
    if (!validated.success) {
      if (!this.loggedInvalidState) {
        this.loggedInvalidState = true;
        this.opts.log(
          'error',
          `assembled FlightGear state failed schema validation (check the property map): ${validated.error.message}`,
        );
      }
      return;
    }
    this.loggedInvalidState = false;
    this.lastStateAtMs = now;
    for (const l of this.listeners) l(validated.data);
  }
}

/**
 * Autobrake mapping. FG 737 models commonly use an integer step
 * (-1=RTO, 0=OFF, 1..3, 4=MAX) — verify per aircraft (see property map notes).
 */
function autobrakeToFgValue(setting: AutobrakeSetting): number {
  switch (setting) {
    case 'RTO':
      return -1;
    case 'OFF':
      return 0;
    case '1':
      return 1;
    case '2':
      return 2;
    case '3':
      return 3;
    case 'MAX':
      return 4;
  }
}

function fgValueToAutobrake(v: number): AutobrakeSetting {
  if (v <= -1) return 'RTO';
  if (v >= 4) return 'MAX';
  if (v >= 1) return String(Math.round(v)) as AutobrakeSetting;
  return 'OFF';
}
