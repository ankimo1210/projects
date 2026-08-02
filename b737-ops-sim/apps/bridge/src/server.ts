import cors from '@fastify/cors';
import websocket from '@fastify/websocket';
import Fastify, { type FastifyInstance } from 'fastify';
import type { WebSocket } from 'ws';
import {
  PROTOCOL_VERSION,
  parseClientMessage,
  type AircraftState,
  type ServerMessage,
} from '@b737/shared';
import type { FlightBackend } from '@b737/flightgear-adapter';
import { AXIS_COMMAND_TYPES, TokenBucket } from './rateLimiter.js';

export interface BridgeOptions {
  backend: FlightBackend;
  stateRateHz: number;
  logLevel?: string;
  /** Pretty logs for interactive dev; JSON otherwise. */
  prettyLogs?: boolean;
}

interface ClientSession {
  socket: WebSocket;
  stateSeq: number;
  saidHello: boolean;
  axisBucket: TokenBucket;
  discreteBucket: TokenBucket;
  lastCommand: string | null;
  lastCommandResult: string | null;
}

/**
 * The bridge is the only process allowed to talk to a flight backend
 * (spec §2): every browser command is schema-validated and rate-limited here
 * before it can reach FlightGear or the mock model.
 */
export async function buildBridge(options: BridgeOptions): Promise<FastifyInstance> {
  const app = Fastify({
    logger: {
      level: options.logLevel ?? 'info',
      ...(options.prettyLogs
        ? { transport: { target: 'pino-pretty', options: { translateTime: 'HH:MM:ss' } } }
        : {}),
    },
  });
  await app.register(cors, { origin: true });
  await app.register(websocket, { options: { maxPayload: 64 * 1024 } });

  const sessions = new Set<ClientSession>();
  let lastState: AircraftState | null = null;

  const unsubscribe = options.backend.subscribe((state) => {
    lastState = state;
    for (const session of sessions) {
      if (session.socket.readyState !== session.socket.OPEN) continue;
      session.stateSeq += 1;
      send(session.socket, { t: 'state', seq: session.stateSeq, state });
    }
  });

  const statusTimer = setInterval(() => {
    const status = options.backend.getStatus();
    for (const session of sessions) {
      if (session.socket.readyState !== session.socket.OPEN) continue;
      send(session.socket, { t: 'backend_status', status });
    }
  }, 1000);

  app.addHook('onClose', async () => {
    clearInterval(statusTimer);
    unsubscribe();
    await options.backend.disconnect();
  });

  app.get('/health', async () => ({ ok: true }));

  app.get('/status', async () => ({
    backend: options.backend.getStatus(),
    clients: sessions.size,
    protocolVersion: PROTOCOL_VERSION,
    uptimeSec: process.uptime(),
  }));

  app.get('/ws', { websocket: true }, (socket: WebSocket, req) => {
    const session: ClientSession = {
      socket,
      stateSeq: 0,
      saidHello: false,
      axisBucket: new TokenBucket(120, 60, Date.now()),
      discreteBucket: new TokenBucket(20, 10, Date.now()),
      lastCommand: null,
      lastCommandResult: null,
    };
    sessions.add(session);
    req.log.info({ clients: sessions.size }, 'ws client connected');

    send(socket, {
      t: 'welcome',
      protocolVersion: PROTOCOL_VERSION,
      backendMode: options.backend.getStatus().mode,
      stateRateHz: options.stateRateHz,
      serverTimeMs: Date.now(),
    });
    if (lastState) {
      session.stateSeq += 1;
      send(socket, { t: 'state', seq: session.stateSeq, state: lastState });
    }

    socket.on('message', (raw: Buffer | string) => {
      void handleMessage(session, String(raw));
    });
    socket.on('close', () => {
      sessions.delete(session);
      app.log.info({ clients: sessions.size }, 'ws client disconnected');
    });
    socket.on('error', (err: Error) => app.log.warn({ err }, 'ws client error'));
  });

  async function handleMessage(session: ClientSession, raw: string): Promise<void> {
    const msg = parseClientMessage(raw);
    if ('parseError' in msg) {
      send(session.socket, { t: 'protocol_error', message: msg.parseError });
      return;
    }
    switch (msg.t) {
      case 'hello': {
        session.saidHello = true;
        if (msg.protocolVersion !== PROTOCOL_VERSION) {
          send(session.socket, {
            t: 'protocol_error',
            message: `protocol version mismatch: bridge=${PROTOCOL_VERSION} client=${msg.protocolVersion}`,
          });
        }
        return;
      }
      case 'ping':
        send(session.socket, {
          t: 'pong',
          seq: msg.seq,
          clientSentAtMs: msg.sentAtMs,
          serverTimeMs: Date.now(),
        });
        return;
      case 'command': {
        const bucket = AXIS_COMMAND_TYPES.has(msg.command.type)
          ? session.axisBucket
          : session.discreteBucket;
        if (!bucket.tryTake(Date.now())) {
          send(session.socket, {
            t: 'command_ack',
            seq: msg.seq,
            result: { ok: false, error: 'rate limited' },
          });
          return;
        }
        session.lastCommand = msg.command.type;
        const result = await options.backend.sendCommand(msg.command);
        session.lastCommandResult = result.ok ? 'ok' : result.error;
        if (!result.ok) {
          app.log.info({ command: msg.command.type, error: result.error }, 'command rejected');
        }
        send(session.socket, { t: 'command_ack', seq: msg.seq, result });
        return;
      }
      case 'set_paused': {
        const result = options.backend.setPaused
          ? await options.backend.setPaused(msg.paused)
          : { ok: false as const, error: 'pause not supported by this backend' };
        send(session.socket, { t: 'command_ack', seq: msg.seq, result });
        return;
      }
      case 'reset_scenario': {
        app.log.info({ config: msg.config }, 'scenario reset requested');
        try {
          await options.backend.resetScenario(msg.config);
          send(session.socket, { t: 'command_ack', seq: msg.seq, result: { ok: true } });
        } catch (err) {
          send(session.socket, {
            t: 'command_ack',
            seq: msg.seq,
            result: { ok: false, error: String(err) },
          });
        }
        return;
      }
    }
  }

  return app;
}

function send(socket: WebSocket, message: ServerMessage): void {
  socket.send(JSON.stringify(message));
}
