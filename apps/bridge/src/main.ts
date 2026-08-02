import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  FlightGearBackend,
  MockBackend,
  parsePropertyMap,
  type FlightBackend,
} from '@b737/flightgear-adapter';
import { loadConfig } from './config.js';
import { buildBridge } from './server.js';

const config = loadConfig();

function createBackend(): FlightBackend {
  if (config.backendMode === 'mock') {
    return new MockBackend({ stateRateHz: config.stateRateHz });
  }
  const mapPath = fileURLToPath(
    new URL('../../../config/flightgear/737-800-property-map.json', import.meta.url),
  );
  const propertyMap = parsePropertyMap(JSON.parse(readFileSync(mapPath, 'utf8')));
  return new FlightGearBackend({
    host: config.fgHost,
    httpPort: config.fgHttpPort,
    propertyMap,
    stateRateHz: config.stateRateHz,
  });
}

const backend = createBackend();
const app = await buildBridge({
  backend,
  stateRateHz: config.stateRateHz,
  logLevel: config.logLevel,
  prettyLogs: process.stdout.isTTY,
});

// FlightGear may start after the bridge: retry until the first connect works,
// after which the backend reconnects on its own.
async function connectWithRetry(): Promise<void> {
  for (;;) {
    try {
      await backend.connect();
      app.log.info({ mode: config.backendMode }, 'flight backend connected');
      return;
    } catch (err) {
      app.log.warn(
        { err: String(err), mode: config.backendMode },
        'backend connect failed; retrying in 3 s (is FlightGear running with --httpd? see FLIGHTGEAR_SETUP.md)',
      );
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
}
void connectWithRetry();

await app.listen({ port: config.port, host: config.host });
app.log.info(
  { url: `ws://${config.host}:${config.port}/ws`, mode: config.backendMode },
  'bridge listening',
);
