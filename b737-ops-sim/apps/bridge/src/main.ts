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
  allowedOrigins: config.allowedOrigins,
});

// FlightGear may start after the bridge. The backend owns reconnection (a
// second retry loop here would race it and leak sockets — R-04); we just start
// it and report what the status says.
await backend.connect();
const initialStatus = backend.getStatus();
app.log[initialStatus.connected ? 'info' : 'warn'](
  { mode: config.backendMode, detail: initialStatus.detail },
  initialStatus.connected
    ? 'flight backend connected'
    : 'flight backend not ready; retrying in the background (is FlightGear running with --httpd? see FLIGHTGEAR_SETUP.md)',
);

await app.listen({ port: config.port, host: config.host });
app.log.info(
  { url: `ws://${config.host}:${config.port}/ws`, mode: config.backendMode },
  'bridge listening',
);
