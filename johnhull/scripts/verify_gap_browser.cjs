// Verify Hull §26.4 values, layout and Example 26.1 text in Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-4');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(outDir, 'numerical-check.json'), 'utf8'));
const keys = ['gap_payoff', 'gap_settlement_line', 'gap_insurance', 'gap_transfer_cost'];
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
  await page.waitForFunction(name => Array.from(document.querySelectorAll('.plotly-graph-div'))
    .some(el => el.layout?.meta?.figure === name && el._fullLayout), key);
  const ids = await page.locator('.plotly-graph-div').evaluateAll((els, name) =>
    els.filter(el => el.layout?.meta?.figure === name).map(el => el.id), key);
  check(ids.length === 1, `${key}: unique plot`);
  return page.locator(`[id="${ids[0]}"]`);
}
async function numeric(plot, key) {
  const { meta, traces } = await plot.evaluate(el => ({ meta: el.layout.meta,
    traces: el._fullData.filter(t => t.visible === true)
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []) })) }));
  check(meta.section === '26.4' && meta.figure === key, `${key}: metadata`);
  const solid = values => values.filter(value => value !== null);
  const figure = reference.figure;
  if (key === 'gap_payoff') {
    const payoff = figure.payoff;
    check(traces.length === 4, 'payoff traces');
    arrayClose(traces[0].x, payoff.grid, 'payoff regular x');
    arrayClose(traces[0].y, payoff.regular_call, 'payoff regular');
    check(traces[1].x.filter(v => v === null).length === 1, 'payoff K1=90 break');
    arrayClose(solid(traces[1].x), payoff.grid, 'payoff K1=90 x');
    arrayClose(solid(traces[1].y), payoff.gap_call_K1_90, 'payoff K1=90');
    arrayClose(solid(traces[2].y), payoff.gap_call_K1_110, 'payoff K1=110');
    arrayClose(traces[3].x, [payoff.K2, payoff.K2], 'payoff jump limit x');
    arrayClose(traces[3].y, [payoff.K2 - 90, payoff.K2 - 110], 'payoff jump limits');
  } else if (key === 'gap_settlement_line') {
    const line = figure.settlement_line;
    const at = line.K1.indexOf(line.K2);
    check(traces.length === 4 && at >= 0, 'settlement traces');
    arrayClose(traces[0].x, line.K1, 'settlement K1');
    arrayClose(traces[0].y, line.call, 'settlement call');
    arrayClose(traces[1].y, line.put, 'settlement put');
    arrayClose(traces[2].y, [line.call[at], line.put[at]], 'settlement regular');
    arrayClose(traces[3].x, [reference.conditional_mean.call.closed_form,
      reference.conditional_mean.put.closed_form], 'settlement zero-value K1');
  } else if (key === 'gap_insurance') {
    const insurance = figure.insurance;
    check(traces.length === 4, 'insurance traces');
    arrayClose(traces[0].y, insurance.regular_put, 'insurance regular');
    arrayClose(solid(traces[1].x), insurance.grid, 'insurance insurer x');
    arrayClose(solid(traces[1].y), insurance.insurer_gap_put, 'insurance insurer');
    arrayClose(traces[2].x, [reference.example_26_1.K2], 'insurance jump limit x');
    arrayClose(traces[2].y, [reference.example_26_1.K1 - reference.example_26_1.K2], 'insurance jump limit');
    arrayClose(traces[3].y, insurance.policyholder_net, 'insurance policyholder');
  } else {
    const rows = figure.transfer_cost.rows;
    const example = reference.example_26_1;
    check(traces.length === 4, 'transfer traces');
    arrayClose(traces[0].x, rows.map(row => row.transfer_cost), 'transfer cost');
    arrayClose(traces[0].y, rows.map(row => row.insurer_cost), 'transfer insurer');
    arrayClose(traces[1].y, rows.map(row => row.policyholder_value), 'transfer policyholder');
    arrayClose(traces[2].y, rows.map(row => row.transfer_cost_present_value), 'transfer present value');
    arrayClose(traces[3].y, [example.regular_put, example.insurer_gap_put], 'transfer printed points');
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
    const selectors = '.gtitle,.xtitle,.ytitle,.legend,.annotation-text,.g-xtitle,.g-ytitle';
    for (const node of el.querySelectorAll(selectors)) {
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
    await page.setViewportSize({ width, height: 1050 });
    await settle(page);
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], `${surface}/${key}/${width}`);
      states.push({ figure: key, width, numeric_checked: true });
      const file = `docs/validation/section-26-4/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.gap_settlement_line.evaluate(async el => {
    const saved = Array.from(el.data[0].y);
    const bad = saved.slice(); bad[0] += 1;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.gap_settlement_line, 'gap_settlement_line'); }
  catch (error) { rejected = error.message.includes('settlement call'); }
  finally { await plots.gap_settlement_line.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, `${surface}: changed price accepted`);
  await numeric(plots.gap_settlement_line, 'gap_settlement_line');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}

(async () => {
  check(reference.section === '26.4' && reference.cases.length === 38, 'independent reference');
  check(numerical.section === '26.4' && numerical.status === 'PASS', 'independent numerical verification');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN,
    args: ['--no-sandbox'] });
  record.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const surface of ['portal', 'book']) {
      const page = await context.newPage();
      const errors = [], requests = [], unapproved = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route(/^https?:/, route => {
        const url = route.request().url();
        requests.push(url);
        if (surface === 'book' && url.startsWith('https://cdn.jsdelivr.net/npm/mathjax@3/es5/'))
          return route.continue();
        unapproved.push(url);
        return route.abort();
      });
      const html = surface === 'portal' ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html';
      await page.goto('file://' + path.join(root, html));
      if (surface === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ rendered: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.rendered > 20 && math.errors === 0, 'Book MathJax');
        check(await page.locator('h3').filter({ hasText: /^4\.11 ギャップ/ }).count() === 1,
          'unique Book §4.11 lesson');
        check(await page.locator('h4').filter({ hasText: /^4\.11\.[1-6] / }).count() === 6,
          'six Book §4.11 subsections');
        const body = (await page.locator('body').innerText()).replace(/\s+/g, '');
        const example = reference.example_26_1;
        for (const phrase of ['3,436', '1,896', '約45%', '44.83%', 'トリガー', '差の符号は',
          example.policyholder_put.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          example.transfer_cost_present_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })])
          check(body.includes(phrase.replace(/\s+/g, '')), `Book Example 26.1 phrase missing: ${phrase}`);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && unapproved.length === 0, `${surface}: page errors or unapproved requests`);
      record.pages[surface] = { ...result, external_network_blocked: surface === 'portal',
        page_errors: errors, external_requests: requests,
        unapproved_requests: unapproved };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/gap_options.py', 'hullkit/src/hullkit/_gap_lesson.py',
      'scripts/build_gap_reference.py', 'scripts/verify_gap_browser.cjs',
      'docs/validation/section-26-4/reference.json', 'docs/validation/section-26-4/numerical-check.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/assets/style.css']) record.source_sha256[file] = sha(file);
    for (const file of ['report/site/exotics.html', 'book/_build/html/notebooks/10_exotics.html',
      ...Object.values(record.pages).flatMap(page => page.screenshots)]) record.artifact_sha256[file] = sha(file);
    record.status = 'PASS';
    record.state_checks = Object.values(record.pages).reduce((n, page) => n + page.states.length, 0);
    record.screenshots = Object.values(record.pages).reduce((n, page) => n + page.screenshots.length, 0);
    console.log(JSON.stringify({ status: record.status, state_checks: record.state_checks, screenshots: record.screenshots }));
  } finally { await browser.close(); }
})().catch(error => { record.status = 'FAIL'; record.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(outDir, 'browser-check.json'), JSON.stringify(record, null, 2) + '\n'));
