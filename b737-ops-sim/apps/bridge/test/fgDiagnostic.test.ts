import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import { parsePropertyMap, type PropertyMap } from '@b737/flightgear-adapter';
import { afterEach, describe, expect, it } from 'vitest';
import { WebSocketServer, type WebSocket } from 'ws';
import { runFlightGearDiagnostic } from '../src/fgDiagnostic.js';
import type { FlightGearDiagnosticError } from '../src/fgDiagnostic.js';

const propertyMap = parsePropertyMap(
  JSON.parse(
    readFileSync(
      fileURLToPath(
        new URL('../../../config/flightgear/737-800-property-map.json', import.meta.url),
      ),
      'utf8',
    ),
  ),
);

interface FakeDiagnosticServer {
  url: string;
  properties: Map<string, number | boolean | string>;
  setLog: { path: string; value: number | boolean | string }[];
  close(): Promise<void>;
}

async function startFakeServer(
  map: PropertyMap,
  initialTaxiLight: boolean,
  acceptWrites = true,
): Promise<FakeDiagnosticServer> {
  const properties = new Map<string, number | boolean | string>();
  for (const entry of Object.values(map.state)) {
    properties.set(entry.fgProp, entry.type === 'bool' ? false : 0);
  }
  const taxiPath = map.commands['set_light.taxi']!.fgProps[0]!;
  properties.set(taxiPath, initialTaxiLight);
  const setLog: { path: string; value: number | boolean | string }[] = [];
  const clients = new Set<WebSocket>();
  const wss = new WebSocketServer({ port: 0, host: '127.0.0.1', path: '/PropertyListener' });
  await once(wss, 'listening');
  const address = wss.address();
  if (address === null || typeof address === 'string') throw new Error('fake FG has no port');

  wss.on('connection', (ws) => {
    clients.add(ws);
    ws.on('close', () => clients.delete(ws));
    ws.on('message', (data) => {
      const message = JSON.parse(String(data)) as {
        command: string;
        node: string;
        value?: number | boolean | string;
      };
      if (message.command === 'get') {
        const value = properties.get(message.node);
        if (value !== undefined) ws.send(JSON.stringify({ path: message.node, value }));
      } else if (message.command === 'set' && message.value !== undefined) {
        setLog.push({ path: message.node, value: message.value });
        if (acceptWrites) properties.set(message.node, message.value);
      }
    });
  });

  return {
    url: `ws://127.0.0.1:${address.port}/PropertyListener`,
    properties,
    setLog,
    async close() {
      for (const client of clients) client.terminate();
      await new Promise<void>((resolve) => wss.close(() => resolve()));
    },
  };
}

describe('FlightGear diagnostic write transaction', () => {
  let server: FakeDiagnosticServer | undefined;

  afterEach(async () => {
    await server?.close();
    server = undefined;
  });

  it.each([false, true])(
    'toggles and exactly restores an initial taxi-light value of %s',
    async (initial) => {
      server = await startFakeServer(propertyMap, initial);
      const result = await runFlightGearDiagnostic({
        url: server.url,
        propertyMap,
        timeoutMs: 1_000,
        pollIntervalMs: 10,
      });

      const taxiPath = propertyMap.commands['set_light.taxi']!.fgProps[0]!;
      expect(result).toMatchObject({
        writeProperty: taxiPath,
        originalValue: initial,
        testValue: !initial,
      });
      expect(server.setLog).toEqual([
        { path: taxiPath, value: !initial },
        { path: taxiPath, value: initial },
      ]);
      expect(server.properties.get(taxiPath)).toBe(initial);
    },
  );

  it('fails when FlightGear rejects the write', async () => {
    server = await startFakeServer(propertyMap, true, false);
    const attempt = runFlightGearDiagnostic({
      url: server.url,
      propertyMap,
      timeoutMs: 150,
      pollIntervalMs: 10,
    });

    await expect(attempt).rejects.toMatchObject({
      stage: 'write',
    } satisfies Partial<FlightGearDiagnosticError>);
    const taxiPath = propertyMap.commands['set_light.taxi']!.fgProps[0]!;
    expect(server.setLog[0]).toEqual({ path: taxiPath, value: false });
    expect(server.properties.get(taxiPath)).toBe(true);
  });
});
