/**
 * Phase-0 FlightGear connection diagnostic (spec §22).
 *
 * Usage (bridge package):
 *   pnpm fg:diagnostic                       # defaults FG_HOST/FG_HTTP_PORT
 *   FG_HOST=172.x.x.x pnpm fg:diagnostic     # WSL2 → Windows host
 *
 * Every property comes from the versioned property map — the map is the single
 * source of truth (spec §5), so a diagnostic with its own hardcoded paths could
 * pass while the paths the bridge actually uses were broken (R-22). All
 * non-optional state properties are read, and ONE harmless control property
 * (the taxi light, taken from the command map) is written and restored.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parsePropertyMap } from '@b737/flightgear-adapter';
import { WebSocket } from 'ws';
import { loadConfig } from '../src/config.js';

const config = loadConfig();
const url = `ws://${config.fgHost}:${config.fgHttpPort}/PropertyListener`;

const mapPath = fileURLToPath(
  new URL('../../../config/flightgear/737-800-property-map.json', import.meta.url),
);
const propertyMap = parsePropertyMap(JSON.parse(readFileSync(mapPath, 'utf8')));

/** Required state paths: exactly what the FlightGear backend waits for. */
const READ_PROPS = [
  ...new Set(
    Object.values(propertyMap.state)
      .filter((entry) => entry.optional !== true)
      .map((entry) => entry.fgProp),
  ),
];

const WRITE_PROP = propertyMap.commands['set_light.taxi']?.fgProps[0];
if (WRITE_PROP === undefined) {
  console.error("[fg-diagnostic] property map has no 'set_light.taxi' command — cannot write-test");
  process.exit(1);
}

console.log(`[fg-diagnostic] property map v${propertyMap.version} (${propertyMap.aircraft})`);
console.log(`[fg-diagnostic] connecting to ${url} ...`);
const ws = new WebSocket(url);
const received = new Map<string, unknown>();

const timeout = setTimeout(() => {
  const missing = READ_PROPS.filter((p) => !received.has(p));
  console.error(
    '[fg-diagnostic] TIMEOUT — no complete response in 15 s.\n' +
      `  * ${received.size}/${READ_PROPS.length} mapped properties answered.\n` +
      (missing.length > 0 && received.size > 0
        ? `  * missing (check the property map against this aircraft):\n${missing
            .map((p) => `      ${p}`)
            .join('\n')}\n`
        : '') +
      '  * Is FlightGear running with --httpd=' +
      String(config.fgHttpPort) +
      ' ?\n' +
      '  * From WSL2 (NAT), FG_HOST must be the Windows host IP and the Windows\n' +
      '    firewall must allow the port — see FLIGHTGEAR_SETUP.md.',
  );
  process.exit(1);
}, 15000);

ws.on('error', (err) => {
  clearTimeout(timeout);
  console.error(`[fg-diagnostic] connection error: ${err.message}`);
  console.error('  See FLIGHTGEAR_SETUP.md for launch flags and WSL2 networking.');
  process.exit(1);
});

ws.on('open', () => {
  console.log(`[fg-diagnostic] connected. requesting ${READ_PROPS.length} mapped properties ...`);
  for (const p of READ_PROPS) ws.send(JSON.stringify({ command: 'get', node: p }));
  ws.send(JSON.stringify({ command: 'get', node: WRITE_PROP }));
});

ws.on('message', (data) => {
  try {
    const msg = JSON.parse(String(data)) as { path?: string; value?: unknown };
    if (typeof msg.path === 'string') received.set(msg.path, msg.value);
  } catch {
    /* ignore non-JSON frames */
  }
  if (READ_PROPS.every((p) => received.has(p)) && !writeStarted) {
    writeStarted = true;
    runWriteTest();
  }
});

let writeStarted = false;

function runWriteTest(): void {
  clearTimeout(timeout);
  console.log(`[fg-diagnostic] all ${READ_PROPS.length} required state properties answered:`);
  for (const p of READ_PROPS) console.log(`  ${p} = ${JSON.stringify(received.get(p))}`);

  const original = received.get(WRITE_PROP!);
  console.log(`[fg-diagnostic] write test: toggling ${WRITE_PROP} ...`);
  ws.send(JSON.stringify({ command: 'set', node: WRITE_PROP, value: true }));
  setTimeout(() => {
    ws.send(JSON.stringify({ command: 'get', node: WRITE_PROP }));
    setTimeout(() => {
      const after = received.get(WRITE_PROP!);
      const ok = after === true || after === 'true' || after === 1;
      console.log(
        ok
          ? '[fg-diagnostic] write CONFIRMED (taxi light read back as on)'
          : `[fg-diagnostic] write NOT confirmed (read back: ${JSON.stringify(after)})`,
      );
      // restore
      ws.send(
        JSON.stringify({
          command: 'set',
          node: WRITE_PROP,
          value: original === true || original === 'true' || original === 1,
        }),
      );
      console.log(`[fg-diagnostic] ${ok ? 'ALL CHECKS PASSED' : 'READS OK, WRITE UNCONFIRMED'}`);
      ws.close();
      process.exit(ok ? 0 : 2);
    }, 500);
  }, 500);
}
