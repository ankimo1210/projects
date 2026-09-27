// Verify §27.4 plots and text in the rendered Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-27-4');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['cb_tree', 'cb_decisions', 'cb_credit', 'cb_convergence'];
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
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []), customdata: Array.from(t.customdata || []) })) }));
  check(meta.section === '27.4' && meta.figure === key, `${key}: metadata`);
  const nodes = data.textbook.nodes;
  if (key === 'cb_tree') {
    const levels = [['A'], ['C', 'B'], ['F', 'E', 'D'], ['J', 'I', 'H', 'G']];
    check(traces.length === levels.length, 'tree levels');
    levels.forEach((names, index) => {
      arrayClose(traces[index].x, names.map(() => index), `tree time ${index}`);
      arrayClose(traces[index].y, names.map((_, up) => 2 * up - index), `tree position ${index}`);
      arrayClose(traces[index].customdata.map(row => row[0]), names.map(name => nodes[name].value), `tree bond ${index}`);
      arrayClose(traces[index].customdata.map(row => row[1]), names.map(name => nodes[name].stock), `tree stock ${index}`);
    });
  } else if (key === 'cb_decisions') {
    check(traces.length === 2, 'decision traces');
    arrayClose(traces[0].y, ['B', 'D', 'E'].map(name => nodes[name].continuation), 'continuation');
    arrayClose(traces[1].y, ['B', 'D', 'E'].map(name => nodes[name].value), 'after decision');
  } else if (key === 'cb_credit') {
    check(traces.length === 2, 'credit traces');
    arrayClose(traces[0].x, data.scenarios.credit.map(row => 100 * row.hazard_rate), 'hazard');
    arrayClose(traces[0].y, data.scenarios.credit.map(row => row.price), 'hazard prices');
    arrayClose(traces[1].x, data.scenarios.recovery.map(row => row.recovery_value), 'recovery');
    arrayClose(traces[1].y, data.scenarios.recovery.map(row => row.price), 'recovery prices');
  } else {
    check(traces.length === 1, 'convergence trace');
    arrayClose(traces[0].x, data.scenarios.convergence.map(row => row.steps), 'steps');
    arrayClose(traces[0].y, data.scenarios.convergence.map(row => row.price), 'convergence prices');
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
      check(await page.locator('h2').filter({ hasText: /10\. 転換社債/ }).count() === 1,
        'unique Book §10 lesson');
    }
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], `${surface}/${key}/${width}`);
      states.push({ figure: key, width, numeric_checked: true });
      const file = `docs/validation/section-27-4/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.cb_tree.evaluate(async el => {
    const saved = el.data[0].customdata.map(row => Array.from(row));
    const bad = saved.map(row => Array.from(row)); bad[0][0] += 0.5;
    await Plotly.restyle(el, { customdata: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.cb_tree, 'cb_tree'); }
  catch (error) { rejected = error.message.includes('tree bond'); }
  finally { await plots.cb_tree.evaluate((el, value) => Plotly.restyle(el, { customdata: [value] }, [0]), original); }
  check(rejected, `${surface}: changed tree value accepted`);
  await numeric(plots.cb_tree, 'cb_tree');
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
        for (const phrase of ['10.1 契約', '10.2 生存', '10.3 満期', '10.4 コール',
          '10.5 信用', '10.6 格子', '11. Longstaff-Schwartz', '12. 練習問題'])
          check(body.includes(phrase), `Book text ${phrase}`);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && requests.length === 0, `${surface}: errors or external requests`);
      record.pages[surface] = { ...result, page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/convertible_bond.py', 'hullkit/src/hullkit/_convertible_bond_lesson.py',
      'scripts/build_convertible_bond_reference.py', 'scripts/verify_convertible_bond_browser.cjs',
      'docs/validation/section-27-4/reference.json', 'docs/validation/section-27-4/numerical-check.json',
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
