import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import WebSocket from 'ws';
import type { FastifyInstance } from 'fastify';
import { MockBackend } from '@b737/flightgear-adapter';
import { PROTOCOL_VERSION, parseServerMessage, type ServerMessage } from '@b737/shared';
import { buildBridge } from '../src/server.js';

const ALLOWED_ORIGIN = 'http://localhost:5173';

describe('bridge integration (real WS client ↔ mock backend)', () => {
  let app: FastifyInstance;
  let backend: MockBackend;
  let url: string;

  beforeEach(async () => {
    backend = new MockBackend({ stateRateHz: 50 });
    await backend.connect();
    app = await buildBridge({
      backend,
      stateRateHz: 50,
      logLevel: 'silent',
      allowedOrigins: [ALLOWED_ORIGIN],
    });
    await app.listen({ port: 0, host: '127.0.0.1' });
    const address = app.server.address();
    if (address === null || typeof address === 'string') throw new Error('no port');
    url = `ws://127.0.0.1:${address.port}/ws`;
  });

  afterEach(async () => {
    await app.close();
  });

  /** Every real client opens from the web app's origin and says hello first. */
  function open(): WebSocket {
    const ws = new WebSocket(url, { origin: ALLOWED_ORIGIN });
    ws.on('open', () => hello(ws));
    return ws;
  }

  function hello(ws: WebSocket, protocolVersion = PROTOCOL_VERSION): void {
    ws.send(JSON.stringify({ t: 'hello', protocolVersion, clientName: 'test' }));
  }

  function collect(ws: WebSocket): ServerMessage[] {
    const messages: ServerMessage[] = [];
    ws.on('message', (raw) => {
      const msg = parseServerMessage(String(raw));
      if (!('parseError' in msg)) messages.push(msg);
    });
    return messages;
  }

  function waitFor<T>(predicate: () => T | undefined, timeoutMs = 4000): Promise<T> {
    return new Promise((resolve, reject) => {
      const started = Date.now();
      const timer = setInterval(() => {
        const v = predicate();
        if (v !== undefined) {
          clearInterval(timer);
          resolve(v);
        } else if (Date.now() - started > timeoutMs) {
          clearInterval(timer);
          reject(new Error('timeout'));
        }
      }, 10);
    });
  }

  it('sends welcome and streams sequenced state updates', async () => {
    const ws = open();
    const messages = collect(ws);
    const welcome = await waitFor(() => messages.find((m) => m.t === 'welcome'));
    expect(welcome).toMatchObject({ backendMode: 'mock', stateRateHz: 50 });

    await waitFor(() => (messages.filter((m) => m.t === 'state').length >= 5 ? true : undefined));
    const states = messages.filter((m) => m.t === 'state');
    const seqs = states.map((s) => s.seq);
    expect(seqs).toEqual([...seqs].sort((a, b) => a - b));
    expect(new Set(seqs).size).toBe(seqs.length);
    expect(states[0]!.state.airport.icao).toBe('KSFO');
    ws.close();
  });

  it('acks valid commands and applies them to the backend', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    ws.send(
      JSON.stringify({
        t: 'command',
        seq: 7,
        sentAtMs: Date.now(),
        command: { type: 'set_light', light: 'landing', on: true },
      }),
    );
    const ack = await waitFor(() => messages.find((m) => m.t === 'command_ack' && m.seq === 7));
    expect(ack).toMatchObject({ result: { ok: true } });
    const lit = await waitFor(() =>
      messages.find((m) => m.t === 'state' && m.state.lights.landing) ? true : undefined,
    );
    expect(lit).toBe(true);
    ws.close();
  });

  it('rejects malformed and invalid commands without crashing', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    ws.send('garbage');
    ws.send(JSON.stringify({ t: 'command', seq: 1, sentAtMs: 0, command: { type: 'explode' } }));
    await waitFor(() =>
      messages.filter((m) => m.t === 'protocol_error').length >= 2 ? true : undefined,
    );
    // still alive: ping works
    ws.send(JSON.stringify({ t: 'ping', seq: 2, sentAtMs: Date.now() }));
    const pong = await waitFor(() => messages.find((m) => m.t === 'pong'));
    expect(pong).toMatchObject({ seq: 2 });
    ws.close();
  });

  it('answers ping with pong carrying timestamps', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    const sentAt = Date.now();
    ws.send(JSON.stringify({ t: 'ping', seq: 42, sentAtMs: sentAt }));
    const pong = await waitFor(() => messages.find((m) => m.t === 'pong'));
    expect(pong).toMatchObject({ seq: 42, clientSentAtMs: sentAt });
    ws.close();
  });

  it('rate limits discrete command floods', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    for (let i = 0; i < 60; i++) {
      ws.send(
        JSON.stringify({
          t: 'command',
          seq: 100 + i,
          sentAtMs: Date.now(),
          command: { type: 'set_light', light: 'taxi', on: i % 2 === 0 },
        }),
      );
    }
    await waitFor(() =>
      messages.filter((m) => m.t === 'command_ack').length >= 60 ? true : undefined,
    );
    const rejected = messages.filter(
      (m) => m.t === 'command_ack' && !m.result.ok && m.result.error === 'rate limited',
    );
    expect(rejected.length).toBeGreaterThan(0);
    ws.close();
  });

  it('broadcasts backend status periodically', async () => {
    const ws = open();
    const messages = collect(ws);
    const status = await waitFor(() => messages.find((m) => m.t === 'backend_status'), 3000);
    expect(status).toMatchObject({ status: { mode: 'mock', connected: true } });
    ws.close();
  });

  it('resets the scenario on request', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    ws.send(
      JSON.stringify({
        t: 'reset_scenario',
        seq: 9,
        config: {
          seed: 1,
          airportIcao: 'KSFO',
          runwayId: '28R',
          startAt: 'threshold',
          flapDetent: 5,
          parkingBrakeSet: true,
          grossWeightLb: 145000,
          windDirDeg: 290,
          windSpeedKt: 6,
        },
      }),
    );
    const ack = await waitFor(() => messages.find((m) => m.t === 'command_ack' && m.seq === 9));
    expect(ack).toMatchObject({ result: { ok: true } });
    ws.close();
  });

  // ------------------------------------------------------------- R-03 contract

  it('refuses the upgrade for a foreign origin', async () => {
    const ws = new WebSocket(url, { origin: 'https://evil.example' });
    const error = await new Promise<Error>((resolve) => ws.on('error', resolve));
    expect(String(error)).toMatch(/403/);
    expect(ws.readyState).not.toBe(WebSocket.OPEN);
  });

  it('accepts a connection with no Origin header (non-browser client)', async () => {
    const ws = new WebSocket(url);
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    ws.close();
  });

  it('rejects commands sent before the hello handshake', async () => {
    const ws = new WebSocket(url, { origin: ALLOWED_ORIGIN });
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    ws.send(
      JSON.stringify({
        t: 'command',
        seq: 3,
        sentAtMs: Date.now(),
        command: { type: 'set_light', light: 'taxi', on: true },
      }),
    );
    const ack = await waitFor(() => messages.find((m) => m.t === 'command_ack' && m.seq === 3));
    expect(ack).toMatchObject({
      result: { ok: false, error: 'handshake required: send hello first' },
    });
    // the command never reached the backend
    const state = await waitFor(() => messages.find((m) => m.t === 'state'));
    expect(state.state.lights.taxi).toBe(false);
    ws.close();
  });

  it('closes the socket on a protocol version mismatch', async () => {
    const ws = new WebSocket(url, { origin: ALLOWED_ORIGIN });
    const messages = collect(ws);
    const closed = new Promise<number>((resolve) => ws.on('close', (code) => resolve(code)));
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    hello(ws, PROTOCOL_VERSION + 1);
    expect(await closed).toBe(1002);
    expect(messages.some((m) => m.t === 'protocol_error')).toBe(true);
  });

  it('rate limits pause and reset floods', async () => {
    const ws = open();
    const messages = collect(ws);
    await waitFor(() => messages.find((m) => m.t === 'welcome'));
    for (let i = 0; i < 40; i++) {
      ws.send(JSON.stringify({ t: 'set_paused', seq: 500 + i, paused: i % 2 === 0 }));
    }
    await waitFor(() =>
      messages.filter((m) => m.t === 'command_ack' && m.seq >= 500).length >= 40 ? true : undefined,
    );
    const limited = messages.filter(
      (m) => m.t === 'command_ack' && !m.result.ok && m.result.error === 'rate limited',
    );
    expect(limited.length).toBeGreaterThan(0);
    ws.close();
  });
});
