/**
 * Phase-0 FlightGear connection diagnostic (spec §22).
 *
 * Usage (bridge package):
 *   pnpm fg:diagnostic                       # defaults FG_HOST/FG_HTTP_PORT
 *   FG_HOST=172.x.x.x pnpm fg:diagnostic     # WSL2 → Windows host
 *
 * Reads a handful of properties and writes ONE harmless control property
 * (taxi light), restoring its previous value afterwards.
 */
import { WebSocket } from 'ws';
import { loadConfig } from '../src/config.js';

const config = loadConfig();
const url = `ws://${config.fgHost}:${config.fgHttpPort}/PropertyListener`;

const READ_PROPS = [
  '/sim/aircraft',
  '/sim/description',
  '/position/latitude-deg',
  '/position/longitude-deg',
  '/position/altitude-ft',
  '/velocities/airspeed-kt',
  '/controls/lighting/taxi-light',
];

console.log(`[fg-diagnostic] connecting to ${url} ...`);
const ws = new WebSocket(url);
const received = new Map<string, unknown>();

const timeout = setTimeout(() => {
  console.error(
    '[fg-diagnostic] TIMEOUT — no response in 10 s.\n' +
      '  * Is FlightGear running with --httpd=' + String(config.fgHttpPort) + ' ?\n' +
      '  * From WSL2 (NAT), FG_HOST must be the Windows host IP and the Windows\n' +
      '    firewall must allow the port — see docs/FLIGHTGEAR_SETUP.md.',
  );
  process.exit(1);
}, 10000);

ws.on('error', (err) => {
  clearTimeout(timeout);
  console.error(`[fg-diagnostic] connection error: ${err.message}`);
  console.error('  See docs/FLIGHTGEAR_SETUP.md for launch flags and WSL2 networking.');
  process.exit(1);
});

ws.on('open', () => {
  console.log('[fg-diagnostic] connected. requesting properties ...');
  for (const p of READ_PROPS) ws.send(JSON.stringify({ command: 'get', node: p }));
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
  console.log('[fg-diagnostic] property reads OK:');
  for (const p of READ_PROPS) console.log(`  ${p} = ${JSON.stringify(received.get(p))}`);

  const original = received.get('/controls/lighting/taxi-light');
  console.log('[fg-diagnostic] write test: toggling /controls/lighting/taxi-light ...');
  ws.send(JSON.stringify({ command: 'set', node: '/controls/lighting/taxi-light', value: true }));
  setTimeout(() => {
    ws.send(JSON.stringify({ command: 'get', node: '/controls/lighting/taxi-light' }));
    setTimeout(() => {
      const after = received.get('/controls/lighting/taxi-light');
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
          node: '/controls/lighting/taxi-light',
          value: original === true || original === 'true' || original === 1,
        }),
      );
      console.log(`[fg-diagnostic] ${ok ? 'ALL CHECKS PASSED' : 'READS OK, WRITE UNCONFIRMED'}`);
      ws.close();
      process.exit(ok ? 0 : 2);
    }, 500);
  }, 500);
}
