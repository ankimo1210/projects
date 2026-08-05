/** Phase-0 FlightGear connection diagnostic (spec §22). */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parsePropertyMap } from '@b737/flightgear-adapter';
import { FlightGearDiagnosticError, runFlightGearDiagnostic } from '../src/fgDiagnostic.js';
import { loadConfig } from '../src/config.js';

const config = loadConfig();
const url = `ws://${config.fgHost}:${config.fgHttpPort}/PropertyListener`;
const mapPath = fileURLToPath(
  new URL('../../../config/flightgear/737-800-property-map.json', import.meta.url),
);
const propertyMap = parsePropertyMap(JSON.parse(readFileSync(mapPath, 'utf8')));

console.log(`[fg-diagnostic] property map v${propertyMap.version} (${propertyMap.aircraft})`);
console.log(`[fg-diagnostic] connecting to ${url} ...`);

try {
  await runFlightGearDiagnostic({
    url,
    propertyMap,
    log: (message) => console.log(`[fg-diagnostic] ${message}`),
  });
  console.log('[fg-diagnostic] ALL CHECKS PASSED — write and exact restore confirmed');
} catch (error) {
  const diagnosticError =
    error instanceof FlightGearDiagnosticError
      ? error
      : new FlightGearDiagnosticError('connection', String(error));
  console.error(`[fg-diagnostic] FAILED (${diagnosticError.stage}): ${diagnosticError.message}`);
  console.error(
    `  Is FlightGear running with --httpd=${String(config.fgHttpPort)}? ` +
      'See FLIGHTGEAR_SETUP.md for launch flags, property-map checks and WSL2 networking.',
  );
  process.exitCode =
    diagnosticError.stage === 'write' || diagnosticError.stage === 'restore' ? 2 : 1;
}
