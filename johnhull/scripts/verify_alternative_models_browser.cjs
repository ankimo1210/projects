// Inspect Hull §27.1 in rendered Book and offline portal against saved independent data.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-27-1');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['alternative_cev', 'alternative_merton', 'alternative_poisson', 'alternative_vg'];
const record = { status: 'FAIL', browser_version: null, pages: {}, source_sha256: {}, artifact_sha256: {} };

function check(ok, message) { if (!ok) throw new Error(message); }
function close(a, b, label, tolerance = 1e-8) {
  check(Number.isFinite(a) && Math.abs(a - b) <= tolerance, `${label}: ${a} != ${b}`);
}
function arrayClose(actual, expected, label, tolerance = 1e-8) {
  check(actual.length === expected.length, `${label}: length ${actual.length} != ${expected.length}`);
  actual.forEach((value, i) => close(Number(value), Number(expected[i]), `${label}[${i}]`, tolerance));
}
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }

async function plotFor(page, key) {
  await page.waitForFunction(key => Array.from(document.querySelectorAll('.plotly-graph-div'))
    .some(el => el.layout?.meta?.figure === key && el._fullLayout), key);
  const ids = await page.locator('.plotly-graph-div').evaluateAll((els, key) =>
    els.filter(el => el.layout?.meta?.figure === key).map(el => el.id), key);
  check(ids.length === 1, `unique plot ${key}`);
  return page.locator(`[id="${ids[0]}"]`);
}
async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function numeric(plot, key) {
  const rows = await plot.evaluate(el => el.data.map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []) })));
  const meta = await plot.evaluate(el => el.layout.meta);
  check(meta.section === '27.1' && meta.figure === key, `${key}: metadata`);
  if (key === 'alternative_cev') {
    check(rows.length === 3, 'CEV traces');
    ['0.7', '1.0', '1.3'].forEach((beta, index) => {
      arrayClose(rows[index].x, data.cev.spots, `CEV ${beta} spot`);
      arrayClose(rows[index].y, data.cev.local_vol[beta].map(v => v * 100), `CEV ${beta} vol`);
    });
  } else if (key === 'alternative_merton') {
    check(rows.length === 1, 'Merton traces');
    arrayClose(rows[0].x, data.merton.strikes.map(k => k / data.merton.spot), 'Merton strikes');
    arrayClose(rows[0].y, data.merton.implied_vol.map(v => v * 100), 'Merton IV');
  } else if (key === 'alternative_poisson') {
    check(rows.length === 2, 'Poisson traces');
    arrayClose(rows[0].x, data.poisson_table.counts, 'Poisson counts');
    arrayClose(rows[0].y, data.poisson_table.probability, 'Poisson pmf');
    arrayClose(rows[1].y, data.poisson_table.cumulative, 'Poisson cdf');
  } else {
    check(rows.length === 2, 'VG traces');
    arrayClose(rows[0].x, data.variance_gamma.terminal_price_centers, 'VG terminal stock price');
    arrayClose(rows[0].y, data.variance_gamma.sample_density, 'VG density');
    arrayClose(rows[1].y, data.variance_gamma.bsm_density, 'BSM density');
  }
}
async function layout(page, plot, label) {
  await plot.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3,
    await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) return 'plot overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3
        || box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) return `clipped ${node.textContent}`;
    }
    return null;
  });
  check(!issue, `${label}: ${issue}`);
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), `${label}: page overflow`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
  record.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    for (const surface of ['portal', 'book']) {
      const page = await context.newPage();
      const errors = [], requests = [], screenshots = [], states = [];
      page.on('pageerror', error => errors.push(error.message));
      if (surface === 'portal') await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
      const html = surface === 'portal' ? 'report/site/numerics.html' : 'book/_build/html/notebooks/06_numerical.html';
      await page.goto('file://' + path.join(root, html));
      if (surface === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ rendered: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.rendered > 10 && math.errors === 0, 'Book MathJax');
        const body = await page.locator('body').innerText();
        for (const phrase of ['7.1 CEV', '7.2 Merton', '7.3 Table 27.1', '7.4 ジャンプ',
          '7.5 分散ガンマ', '7.6 使い分け', '0.3679', '独立PDE'])
          check(body.includes(phrase), `Book text ${phrase}`);
        record.book_math = math;
      }
      const plots = {};
      for (const key of keys) plots[key] = await plotFor(page, key);
      for (const width of [1440, 1000]) {
        await page.setViewportSize({ width, height: 1000 }); await settle(page);
        for (const key of keys) {
          await numeric(plots[key], key);
          await layout(page, plots[key], `${surface}/${key}/${width}`);
          const file = `docs/validation/section-27-1/${surface}-${key}-${width}.png`;
          await plots[key].screenshot({ path: path.join(root, file) });
          screenshots.push(file); states.push({ figure: key, width, numeric_checked: true });
        }
      }
      const original = await plots.alternative_poisson.evaluate(async el => {
        const original = Array.from(el.data[0].y);
        const bad = original.slice(); bad[0] = 0.9;
        await Plotly.restyle(el, { y: [bad] }, [0]);
        return original;
      });
      let rejected = false;
      try { await numeric(plots.alternative_poisson, 'alternative_poisson'); }
      catch (error) { rejected = error.message.includes('Poisson pmf'); }
      finally { await plots.alternative_poisson.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
      check(rejected, `${surface}: altered Poisson probability was accepted`);
      await numeric(plots.alternative_poisson, 'alternative_poisson');
      check(errors.length === 0 && requests.length === 0, `${surface}: JS errors or external requests`);
      record.pages[surface] = { states, screenshots, numeric_mutation_rejected: rejected,
        page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of ['hullkit/src/hullkit/alternative_models.py', 'hullkit/src/hullkit/_alternative_models_lesson.py',
      'scripts/build_alternative_models_reference.py', 'scripts/verify_alternative_models_browser.cjs',
      'docs/validation/section-27-1/reference.json', 'docs/validation/section-27-1/numerical-check.json',
      'volumes/06_numerical_methods/build_numerical_notebook.py', 'volumes/06_numerical_methods/numerical.ipynb',
      'report/report_builder/figures.py', 'report/assets/style.css']) record.source_sha256[file] = sha(file);
    for (const file of ['report/site/numerics.html', 'book/_build/html/notebooks/06_numerical.html',
      ...Object.values(record.pages).flatMap(page => page.screenshots)]) record.artifact_sha256[file] = sha(file);
    record.status = 'PASS';
    record.state_checks = Object.values(record.pages).reduce((n, page) => n + page.states.length, 0);
    console.log(JSON.stringify({ status: record.status, state_checks: record.state_checks, screenshots: 16 }));
  } finally { await browser.close(); }
})().catch(error => { record.status = 'FAIL'; record.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(outDir, 'browser-check.json'), JSON.stringify(record, null, 2) + '\n'));
