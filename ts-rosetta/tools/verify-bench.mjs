// Functional verification (DoD) + bench measurement for the three UI apps.
// Run from ts-rosetta root: node <this file>
import { chromium } from 'playwright';

const APPS = [
  { name: 'react', url: 'http://localhost:4173' },
  { name: 'vue', url: 'http://localhost:4174' },
  { name: 'angular', url: 'http://localhost:4175' },
];

const browser = await chromium.launch();
const results = {};

for (const { name, url } of APPS) {
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const r = { functional: [], bench: {} };

  // --- functional: add ---
  await page.fill('input[placeholder="New task..."]', 'hello world');
  await page.click('button[type="submit"]');
  await page.waitForSelector('.tasks li:has-text("hello world")');
  r.functional.push('add OK');

  // --- stats after add ---
  let stats = await page.textContent('.filters .stats');
  if (!/total 1 \/ active 1 \/ done 0/.test(stats)) throw new Error(`${name} stats after add: ${stats}`);
  r.functional.push('stats OK');

  // --- toggle ---
  await page.check('.tasks li input[type="checkbox"]');
  await page.waitForSelector('.tasks li span.done');
  stats = await page.textContent('.filters .stats');
  if (!/total 1 \/ active 0 \/ done 1/.test(stats)) throw new Error(`${name} stats after toggle: ${stats}`);
  r.functional.push('toggle OK');

  // --- filter ---
  await page.click('.filters button:has-text("active")');
  await page.waitForFunction(() => document.querySelectorAll('.tasks li').length === 0);
  await page.click('.filters button:has-text("done")');
  await page.waitForFunction(() => document.querySelectorAll('.tasks li').length === 1);
  await page.click('.filters button:has-text("all")');
  r.functional.push('filter OK');

  // --- delete ---
  await page.click('.tasks li button');
  await page.waitForFunction(() => document.querySelectorAll('.tasks li').length === 0);
  stats = await page.textContent('.filters .stats');
  if (!/total 0/.test(stats)) throw new Error(`${name} stats after delete: ${stats}`);
  r.functional.push('delete OK');

  // --- bench (median of 3 runs each) ---
  for (const n of [1000, 10000]) {
    const runs = [];
    for (let i = 0; i < 3; i++) {
      await page.click(`.bench button:has-text("Bench ${n.toLocaleString('en-US')}")`);
      await page.waitForSelector('.bench p');
      const text = await page.textContent('.bench p');
      const m = text.match(/render ([\d.]+)ms \/ update-all\s*([\d.]+)ms(?:\s*\((\d+) fps\))?/s);
      if (!m) throw new Error(`${name} bench parse fail: ${text}`);
      runs.push({ render: +m[1], update: +m[2], fps: m[3] ? +m[3] : null });
      await page.click('.bench button:has-text("Clear")');
      await page.waitForFunction(() => document.querySelectorAll('.tasks li').length === 0);
    }
    runs.sort((a, b) => a.render - b.render);
    r.bench[n] = runs[1]; // median by render time
  }

  results[name] = r;
  await page.close();
  console.log(`${name}: ${r.functional.join(', ')}`);
  console.log(`  bench:`, JSON.stringify(r.bench));
}

await browser.close();
console.log('\nFULL_RESULTS ' + JSON.stringify(results));
