// Verify Hull §27.7 figures and text in the rendered Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-27-7');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['two_asset_nodes', 'two_asset_convergence', 'two_asset_errors', 'two_asset_correlation'];
const record = { status: 'FAIL', browser_version: null, pages: {}, source_sha256: {}, artifact_sha256: {} };
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex');
function check(ok, message) { if (!ok) throw new Error(message); }
function close(actual, expected, label) {
  check(Number.isFinite(Number(actual)) && Math.abs(Number(actual) - Number(expected)) <= 1e-8,
    `${label}: ${actual} != ${expected}`);
}
function arrayClose(actual, expected, label) {
  check(actual.length === expected.length, `${label}: length ${actual.length} != ${expected.length}`);
  actual.forEach((value, index) => close(value, expected[index], `${label}[${index}]`));
}
async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
}
async function plotFor(page, key) {
  await page.waitForFunction(key => Array.from(document.querySelectorAll('.plotly-graph-div'))
    .some(el => el.layout?.meta?.figure === key && el._fullLayout), key);
  const ids = await page.locator('.plotly-graph-div').evaluateAll((els, key) =>
    els.filter(el => el.layout?.meta?.figure === key).map(el => el.id), key);
  check(ids.length === 1, `${key}: unique plot`);
  return page.locator(`[id="${ids[0]}"]`);
}
async function numeric(plot, key) {
  const { meta, traces } = await plot.evaluate(el => ({ meta: el.layout.meta,
    traces: el._fullData.filter(t => t.visible === true)
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []) })) }));
  check(meta.section === '27.7' && meta.figure === key, `${key}: metadata`);
  const methods = ['transform', 'rubinstein', 'adjusted'];
  if (key === 'two_asset_nodes') {
    const hand = data.hand_example, [v1, v2] = data.parameters.volatilities;
    const rho = data.parameters.correlation, root = Math.sqrt(hand.dt);
    check(traces.length === 4, 'three lattices and the ellipse');
    methods.forEach((name, index) => {
      arrayClose(traces[index].x, hand[name].moves.map(m => m[0] / (v1 * root)), `${name} node x`);
      arrayClose(traces[index].y, hand[name].moves.map(m => m[1] / (v2 * root)), `${name} node y`);
    });
    const angles = Array.from({ length: 121 }, (_, i) => 2 * Math.PI * i / 120);
    arrayClose(traces[3].x, angles.map(a => Math.cos(a)), 'ellipse x');
    arrayClose(traces[3].y, angles.map(a => rho * Math.cos(a) + Math.sqrt(1 - rho * rho) * Math.sin(a)),
      'ellipse y');
  } else if (key === 'two_asset_convergence') {
    const conv = data.convergence, reference = data.analytic.american_exchange.value;
    check(traces.length === 4, 'three methods and the 1-D reference');
    methods.forEach((name, index) => {
      arrayClose(traces[index].x, conv.steps, `${name} steps`);
      arrayClose(traces[index].y, conv.american[name], `convergence ${name}`);
    });
    arrayClose(traces[3].y, [reference, reference], 'reference line');
  } else if (key === 'two_asset_errors') {
    const errors = data.errors, start = Math.abs(errors.transform_max_call[0]);
    check(traces.length === 4, 'three methods and the 1/N guide');
    methods.forEach((name, index) => {
      arrayClose(traces[index].x, errors.steps, `${name} error steps`);
      arrayClose(traces[index].y, errors[`${name}_max_call`].map(Math.abs), `error ${name}`);
    });
    const steps = errors.steps;
    arrayClose(traces[3].y, [start, start * steps[0] / steps[steps.length - 1]], 'guide');
  } else {
    const sweep = data.correlation;
    check(traces.length === 3, 'three correlation sweeps');
    methods.forEach((name, index) => {
      arrayClose(traces[index].x, sweep.rho, `${name} rho`);
      arrayClose(traces[index].y, sweep[name], `correlation ${name}`);
    });
  }
}
async function layout(page, plot, label) {
  await plot.evaluate(el => el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }));
  await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3,
    await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) return 'plot overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3 ||
          box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) return `clipped ${node.textContent}`;
    }
    return null;
  });
  check(!issue, `${label}: ${issue}`);
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), `${label}: page overflow`);
}
async function inspect(page, surface) {
  const plots = {}, states = [], screenshots = [];
  for (const key of keys) plots[key] = await plotFor(page, key);
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    if (surface === 'book') {
      check(await page.locator('h2').filter({ hasText: /13\. 相関のある/ }).count() === 1,
        'unique Book §13 lesson');
    }
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], `${surface}/${key}/${width}`);
      states.push({ figure: key, width, numeric_checked: true });
      const file = `docs/validation/section-27-7/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.two_asset_convergence.evaluate(async el => {
    const saved = Array.from(el.data[1].y);
    const bad = saved.slice(); bad[0] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [1]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.two_asset_convergence, 'two_asset_convergence'); }
  catch (error) { rejected = error.message.includes('convergence rubinstein'); }
  finally { await plots.two_asset_convergence.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [1]), original); }
  check(rejected, `${surface}: changed tree price accepted`);
  await numeric(plots.two_asset_convergence, 'two_asset_convergence');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN,
    args: ['--no-sandbox'] });
  record.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const surface of ['portal', 'book']) {
      const page = await context.newPage();
      const errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      if (surface === 'portal') await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
      const html = surface === 'portal' ? 'report/site/numerics.html' : 'book/_build/html/notebooks/06_numerical.html';
      await page.goto('file://' + path.join(root, html));
      if (surface === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ rendered: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.rendered > 20 && math.errors === 0, 'Book MathJax');
        const body = await page.locator('body').innerText();
        for (const phrase of ['13.1 無相関なら', '13.2 変数を変換', '13.3 Rubinstein', '13.4 確率を調整',
          '13.5 米国型を評価', '13.6 収束の違い', '14. Longstaff-Schwartz', '15. 練習問題'])
          check(body.includes(phrase), `Book text ${phrase}`);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && requests.length === 0, `${surface}: errors or external requests`);
      record.pages[surface] = { ...result, page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/two_asset_tree.py', 'hullkit/src/hullkit/_two_asset_tree_lesson.py',
      'scripts/build_two_asset_reference.py', 'scripts/verify_two_asset_browser.cjs',
      'docs/validation/section-27-7/reference.json', 'docs/validation/section-27-7/numerical-check.json',
      'volumes/06_numerical_methods/build_numerical_notebook.py', 'volumes/06_numerical_methods/numerical.ipynb',
      'report/report_builder/figures.py', 'report/assets/style.css']) record.source_sha256[file] = sha(file);
    for (const file of ['report/site/numerics.html', 'book/_build/html/notebooks/06_numerical.html',
      ...Object.values(record.pages).flatMap(page => page.screenshots)]) record.artifact_sha256[file] = sha(file);
    record.status = 'PASS';
    record.state_checks = Object.values(record.pages).reduce((n, page) => n + page.states.length, 0);
    record.screenshots = Object.values(record.pages).reduce((n, page) => n + page.screenshots.length, 0);
    console.log(JSON.stringify({ status: record.status, state_checks: record.state_checks, screenshots: record.screenshots }));
  } finally { await browser.close(); }
})().catch(error => { record.status = 'FAIL'; record.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(outDir, 'browser-check.json'), JSON.stringify(record, null, 2) + '\n'));
