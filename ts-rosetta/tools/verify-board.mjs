// Live-board functional verification + measurement (production builds).
//
// Prereq (from repo root):
//   pnpm build
//   (cd apps/react   && pnpm exec vite preview --port 4173 --strictPort) &
//   (cd apps/vue     && pnpm exec vite preview --port 4174 --strictPort) &
//   (cd apps/angular/dist/browser && python3 -m http.server 4175) &
//   (cd apps/solid   && pnpm exec vite preview --port 4176 --strictPort) &
// Run:
//   node tools/verify-board.mjs
import { chromium } from 'playwright';

const TARGETS = [
  { name: 'react-naive', url: 'http://localhost:4173/#board', mode: 'naive' },
  { name: 'react-optimized', url: 'http://localhost:4173/#board', mode: 'optimized' },
  { name: 'vue', url: 'http://localhost:4174/#board' },
  { name: 'angular', url: 'http://localhost:4175/#board' },
  { name: 'solid', url: 'http://localhost:4176/' },
];

const CONFIGS = [
  { symbols: 200, rate: 40 },
  { symbols: 1000, rate: 60 },
  // 4x CPU throttle ≈ mid-range phone: shows whether the framework's own
  // work budget survives when the machine stops absorbing it.
  { symbols: 1000, rate: 60, throttle: 4 },
  // 5000 rows: the bottleneck moves to browser layout (30k+ DOM nodes) —
  // framework choice stops mattering; virtualization is the real fix.
  { symbols: 5000, rate: 60 },
];

const SAMPLES = 6; // ~6s per config

async function readStats(page) {
  return {
    fps: Number(await page.textContent('[data-stat="fps"]')),
    long: Number(await page.textContent('[data-stat="long"]')),
    upd: Number(await page.textContent('[data-stat="upd"]')),
    work: Number(await page.textContent('[data-stat="work"]')),
  };
}

const median = (xs) => xs.slice().sort((a, b) => a - b)[Math.floor(xs.length / 2)];

const browser = await chromium.launch();
const results = [];

for (const t of TARGETS) {
  const page = await browser.newPage();
  const cdp = await page.context().newCDPSession(page);
  await page.goto(t.url, { waitUntil: 'networkidle' });
  if (t.mode) await page.click(`button[data-mode="${t.mode}"]`);

  for (const cfg of CONFIGS) {
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: cfg.throttle ?? 1 });
    await page.click(`button[data-symbols="${cfg.symbols}"]`);
    await page.click(`button[data-rate="${cfg.rate}"]`);
    // (re)start with this config
    const label = await page.textContent('button[data-action="toggle"]');
    if (label.trim() === 'Stop') await page.click('button[data-action="toggle"]');
    await page.click('button[data-action="toggle"]');

    // functional: some Last cell text must change between two reads
    await page.waitForSelector('.board-grid tbody tr');
    const cell = page.locator('.board-grid tbody tr:nth-child(3) td:nth-child(2)');
    const before = await cell.textContent();
    await page.waitForTimeout(800);
    const after = await cell.textContent();
    const live =
      before !== after ||
      (await page
        .locator('.board-grid tbody tr:nth-child(1) td:nth-child(2)')
        .textContent()) !== before;

    // measure: SAMPLES windows, medians (long = final cumulative)
    const fps = [];
    const upd = [];
    const work = [];
    let long = 0;
    for (let i = 0; i < SAMPLES; i++) {
      await page.waitForTimeout(1000);
      const s = await readStats(page);
      if (Number.isFinite(s.fps)) fps.push(s.fps);
      upd.push(s.upd);
      work.push(s.work);
      long = s.long;
    }
    await page.click('button[data-action="toggle"]'); // stop

    const row = {
      target: t.name,
      config: `${cfg.symbols}sym@${cfg.rate}tps${cfg.throttle ? `(cpu/${cfg.throttle})` : ''}`,
      live,
      fps: median(fps),
      longTotal: long,
      updPerSec: median(upd),
      workPerSec: median(work),
    };
    results.push(row);
    console.log(
      `${row.target.padEnd(16)} ${row.config.padEnd(22)} live=${row.live} ` +
        `fps=${row.fps} long=${row.longTotal} upd/s=${row.updPerSec} work/s=${row.workPerSec}`,
    );
  }
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
  await page.close();
}

await browser.close();
console.log('\nFULL_RESULTS ' + JSON.stringify(results));
const dead = results.filter((r) => !r.live);
if (dead.length) {
  console.error(`NOT LIVE: ${dead.map((d) => d.target + '/' + d.config).join(', ')}`);
  process.exit(1);
}
