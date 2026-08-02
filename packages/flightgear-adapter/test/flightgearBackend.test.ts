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

describe('FlightGearBackend against a fake FG server', () => {
  let server: FakeFgServer;
  let backend: FlightGearBackend;

  beforeEach(() => {
    server = new FakeFgServer(PORT);
    backend = new FlightGearBackend({
      host: '127.0.0.1',
      httpPort: PORT,
      propertyMap: parsePropertyMap(mapJson),
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
    const r1 = await backend.sendCommand({ type: 'set_control_axis', axis: 'pitch', valueNorm: 0.5 });
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
});
