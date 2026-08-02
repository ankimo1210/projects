import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { AircraftState } from '@b737/shared';
import { FlightGearBackend } from '../src/flightgear/flightgearBackend.js';
import { parsePropertyMap } from '../src/flightgear/propertyMap.js';
import { FakeFgServer } from './fakeFgServer.js';

const PORT = 55123;

const mapJson = JSON.parse(
  readFileSync(
    fileURLToPath(new URL('../../../config/flightgear/737-800-property-map.json', import.meta.url)),
    'utf8',
  ),
) as unknown;

function waitFor<T>(predicate: () => T | undefined, timeoutMs = 3000): Promise<T> {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      const value = predicate();
      if (value !== undefined) {
        clearInterval(timer);
        resolve(value);
      } else if (Date.now() - started > timeoutMs) {
        clearInterval(timer);
        reject(new Error('waitFor timeout'));
      }
    }, 10);
  });
}

const propertyMap = parsePropertyMap(mapJson);

/**
 * FlightGear pushes every subscribed property once on connect. Tests that want
 * state out of the adapter must reproduce that: the adapter refuses to publish
 * until every non-optional property has arrived (R-05).
 */
function seedRequired(server: FakeFgServer): void {
  for (const [key, entry] of Object.entries(propertyMap.state)) {
    if (entry.optional === true) continue;
    server.push(entry.fgProp, key === 'weightOnWheels' ? true : 0);
  }
}

describe('FlightGearBackend against a fake FG server', () => {
  let server: FakeFgServer;
  let backend: FlightGearBackend;

  beforeEach(() => {
    server = new FakeFgServer(PORT);
    backend = new FlightGearBackend({
      host: '127.0.0.1',
      httpPort: PORT,
      propertyMap,
      stateRateHz: 50,
      reconnectDelayMs: 100,
    });
  });

  afterEach(async () => {
    await backend.disconnect();
    await server.close();
  });

  it('validates the shipped property map', () => {
    expect(() => parsePropertyMap(mapJson)).not.toThrow();
  });

  it('subscribes to every mapped state property on connect', async () => {
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 30 ? true : undefined));
    expect(server.listenedPaths.has('/position/altitude-ft')).toBe(true);
    expect(server.listenedPaths.has('/velocities/airspeed-kt')).toBe(true);
  });

  it('assembles unit-converted state from pushed properties', async () => {
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
    seedRequired(server);
    server.push('/position/altitude-ft', 1500);
    server.push('/velocities/airspeed-kt', 180);
    server.push('/velocities/vertical-speed-fps', 20); // 1200 fpm
    server.push('/gear/gear[1]/wow', false);

    const states: AircraftState[] = [];
    backend.subscribe((s) => states.push(s));
    const state = await waitFor(() => states.find((s) => s.position.altitudeFtMsl === 1500));
    expect(state.speeds.iasKt).toBe(180);
    expect(state.speeds.verticalSpeedFpm).toBeCloseTo(1200, 5);
    expect(state.weightOnWheels).toBe(false);
  });

  it('maps commands to FG property writes with conversions', async () => {
    await backend.connect();
    const r1 = await backend.sendCommand({
      type: 'set_control_axis',
      axis: 'pitch',
      valueNorm: 0.5,
    });
    const r2 = await backend.sendCommand({ type: 'set_flaps', detent: 5 });
    const r3 = await backend.sendCommand({ type: 'set_throttle', valueNorm: 0.9 });
    expect(r1.ok && r2.ok && r3.ok).toBe(true);
    await waitFor(() => (server.setLog.length >= 4 ? true : undefined));
    // schema +pitch = nose up -> FG elevator -0.5
    expect(server.setLog).toContainEqual({ path: '/controls/flight/elevator', value: -0.5 });
    // flaps detent 5 -> norm 3/8
    expect(server.setLog).toContainEqual({ path: '/controls/flight/flaps', value: 0.375 });
    // throttle fans out to both engines
    expect(server.setLog).toContainEqual({
      path: '/controls/engines/engine[0]/throttle',
      value: 0.9,
    });
    expect(server.setLog).toContainEqual({
      path: '/controls/engines/engine[1]/throttle',
      value: 0.9,
    });
  });

  it('reports commands as failed when disconnected', async () => {
    const res = await backend.sendCommand({ type: 'set_throttle', valueNorm: 0.5 });
    expect(res.ok).toBe(false);
  });

  it('reconnects after the server drops the connection', async () => {
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
    await server.close();
    await new Promise((r) => setTimeout(r, 50));
    server = new FakeFgServer(PORT);
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined), 5000);
    expect(server.listenedPaths.has('/position/altitude-ft')).toBe(true);
  });

  // -------------------------------------------------- R-04 connection lifecycle

  it('starts streaming when FlightGear appears after a failed first connect', async () => {
    await server.close();
    const states: AircraftState[] = [];
    backend.subscribe((s) => states.push(s));
    await backend.connect(); // FG is not up yet: must not throw, must keep trying
    expect(backend.getStatus().connected).toBe(false);

    server = new FakeFgServer(PORT);
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined), 5000);
    seedRequired(server);
    server.push('/position/altitude-ft', 2500);
    const state = await waitFor(() => states.find((s) => s.position.altitudeFtMsl === 2500));
    expect(state).toBeDefined();
    expect(backend.getStatus().connected).toBe(true);
  });

  it('keeps exactly one FlightGear socket across repeated connects', async () => {
    await backend.connect();
    await backend.connect();
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
    await new Promise((r) => setTimeout(r, 300));
    expect(server.clientCount).toBe(1);
    await backend.disconnect();
    await waitFor(() => (server.clientCount === 0 ? true : undefined));
    expect(server.clientCount).toBe(0);
  });

  // ------------------------------------------------------- R-05 state integrity

  it('publishes nothing until every required property has arrived', async () => {
    const states: AircraftState[] = [];
    backend.subscribe((s) => states.push(s));
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
    server.push('/position/altitude-ft', 1000); // partial cache
    await new Promise((r) => setTimeout(r, 200));
    expect(states).toHaveLength(0);
    expect(backend.getStatus().connected).toBe(false);
    expect(backend.getStatus().detail).toMatch(/waiting for/);

    seedRequired(server);
    await waitFor(() => (states.length > 0 ? true : undefined));
    expect(backend.getStatus().connected).toBe(true);
  });

  it('stops publishing when the FlightGear stream goes stale', async () => {
    const stale = new FlightGearBackend({
      host: '127.0.0.1',
      httpPort: PORT,
      propertyMap,
      stateRateHz: 50,
      reconnectDelayMs: 100,
      staleAfterMs: 120,
    });
    try {
      const states: AircraftState[] = [];
      stale.subscribe((s) => states.push(s));
      await stale.connect();
      await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
      seedRequired(server);
      await waitFor(() => (states.length > 0 ? true : undefined));

      await new Promise((r) => setTimeout(r, 300)); // FG says nothing further
      const frozen = states.length;
      await new Promise((r) => setTimeout(r, 200));
      expect(states.length).toBe(frozen);
      expect(stale.getStatus().connected).toBe(false);
    } finally {
      await stale.disconnect();
    }
  });

  it('drops cached values when the socket closes', async () => {
    const states: AircraftState[] = [];
    backend.subscribe((s) => states.push(s));
    await backend.connect();
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined));
    seedRequired(server);
    server.push('/position/altitude-ft', 4200);
    await waitFor(() => states.find((s) => s.position.altitudeFtMsl === 4200));

    await server.close();
    await new Promise((r) => setTimeout(r, 50));
    const afterClose = states.length;
    server = new FakeFgServer(PORT);
    await waitFor(() => (server.listenedPaths.size > 0 ? true : undefined), 5000);
    // reconnected, but the new session has no properties yet: no stale 4200 ft
    await new Promise((r) => setTimeout(r, 200));
    expect(states.length).toBe(afterClose);
  });
});
