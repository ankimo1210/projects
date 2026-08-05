import type { PropertyMap } from '@b737/flightgear-adapter';
import { WebSocket } from 'ws';

export type DiagnosticStage = 'connection' | 'read' | 'write' | 'restore';

export class FlightGearDiagnosticError extends Error {
  constructor(
    readonly stage: DiagnosticStage,
    message: string,
  ) {
    super(message);
    this.name = 'FlightGearDiagnosticError';
  }
}

export interface FlightGearDiagnosticOptions {
  url: string;
  propertyMap: PropertyMap;
  timeoutMs?: number;
  pollIntervalMs?: number;
  log?: (message: string) => void;
}

export interface FlightGearDiagnosticResult {
  requiredPropertyCount: number;
  writeProperty: string;
  originalValue: boolean;
  testValue: boolean;
}

/**
 * Exercise the exact state/command map used by the FlightGear backend.
 *
 * The taxi-light write is deliberately transactional: read the typed original
 * value, write its opposite, confirm it, restore the exact original value, and
 * confirm the restoration before reporting success.
 */
export function runFlightGearDiagnostic(
  options: FlightGearDiagnosticOptions,
): Promise<FlightGearDiagnosticResult> {
  const timeoutMs = options.timeoutMs ?? 15_000;
  const pollIntervalMs = options.pollIntervalMs ?? 100;
  const log = options.log ?? (() => undefined);
  const requiredPaths = [
    ...new Set(
      Object.values(options.propertyMap.state)
        .filter((entry) => entry.optional !== true)
        .map((entry) => entry.fgProp),
    ),
  ];
  const writeProperty = options.propertyMap.commands['set_light.taxi']?.fgProps[0];

  if (writeProperty === undefined) {
    return Promise.reject(
      new FlightGearDiagnosticError(
        'write',
        "property map has no 'set_light.taxi' command — cannot write-test",
      ),
    );
  }

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(options.url);
    const received = new Map<string, unknown>();
    let stage: 'read' | 'write' | 'restore' = 'read';
    let originalValue: boolean | undefined;
    let testValue: boolean | undefined;
    let pollTimer: ReturnType<typeof setInterval> | undefined;
    let settled = false;

    const stopPolling = (): void => {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = undefined;
    };
    const cleanup = (): void => {
      clearTimeout(deadline);
      stopPolling();
      ws.removeAllListeners();
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close();
    };
    const fail = (errorStage: DiagnosticStage, message: string): void => {
      if (settled) return;
      settled = true;
      // A failed read-back is not permission to leave a control changed. Once
      // the original was known, make one final best-effort exact restore.
      if (originalValue !== undefined && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: 'set', node: writeProperty, value: originalValue }));
      }
      cleanup();
      reject(new FlightGearDiagnosticError(errorStage, message));
    };
    const succeed = (): void => {
      if (settled || originalValue === undefined || testValue === undefined) return;
      settled = true;
      const result: FlightGearDiagnosticResult = {
        requiredPropertyCount: requiredPaths.length,
        writeProperty,
        originalValue,
        testValue,
      };
      cleanup();
      resolve(result);
    };
    const requestWriteReadback = (): void => {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ command: 'get', node: writeProperty }));
    };
    const beginReadback = (): void => {
      stopPolling();
      requestWriteReadback();
      pollTimer = setInterval(requestWriteReadback, pollIntervalMs);
    };

    const deadline = setTimeout(() => {
      if (stage === 'read') {
        const expected = new Set([...requiredPaths, writeProperty]);
        const missing = [...expected].filter((path) => !received.has(path));
        fail(
          'read',
          `timed out waiting for ${missing.length} mapped property/ies` +
            (missing.length > 0 ? `: ${missing.join(', ')}` : ''),
        );
      } else if (stage === 'write') {
        fail('write', `write read-back timed out for ${writeProperty}`);
      } else {
        fail('restore', `restore read-back timed out for ${writeProperty}`);
      }
    }, timeoutMs);

    ws.on('error', (error) => {
      fail('connection', `connection error: ${error.message}`);
    });

    ws.on('open', () => {
      log(`connected. requesting ${requiredPaths.length} required mapped properties ...`);
      for (const path of requiredPaths) {
        ws.send(JSON.stringify({ command: 'get', node: path }));
      }
      if (!requiredPaths.includes(writeProperty)) {
        ws.send(JSON.stringify({ command: 'get', node: writeProperty }));
      }
    });

    ws.on('message', (data) => {
      let message: { path?: unknown; value?: unknown };
      try {
        message = JSON.parse(String(data)) as { path?: unknown; value?: unknown };
      } catch {
        return;
      }
      if (typeof message.path !== 'string') return;
      received.set(message.path, message.value);

      if (stage === 'read') {
        if (!requiredPaths.every((path) => received.has(path)) || !received.has(writeProperty)) {
          return;
        }
        const original = received.get(writeProperty);
        if (typeof original !== 'boolean') {
          fail(
            'read',
            `expected boolean initial value for ${writeProperty}, received ${JSON.stringify(original)}`,
          );
          return;
        }
        originalValue = original;
        testValue = !original;
        log(`all ${requiredPaths.length} required state properties answered`);
        for (const path of requiredPaths) log(`  ${path} = ${JSON.stringify(received.get(path))}`);
        log(`write test: ${writeProperty} ${String(originalValue)} -> ${String(testValue)}`);
        stage = 'write';
        ws.send(JSON.stringify({ command: 'set', node: writeProperty, value: testValue }));
        beginReadback();
        return;
      }

      if (message.path !== writeProperty) return;
      if (stage === 'write' && Object.is(message.value, testValue)) {
        stopPolling();
        log(`write confirmed: ${writeProperty} = ${String(testValue)}`);
        stage = 'restore';
        ws.send(JSON.stringify({ command: 'set', node: writeProperty, value: originalValue }));
        beginReadback();
      } else if (stage === 'restore' && Object.is(message.value, originalValue)) {
        stopPolling();
        log(`restore confirmed: ${writeProperty} = ${String(originalValue)}`);
        succeed();
      }
    });
  });
}
