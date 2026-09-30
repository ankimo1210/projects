// Inspect Hull §26.4 signed-payoff plots and Example26.1 on both surfaces.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-4');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(outDir, 'numerical-check.json'), 'utf8'));
const keys = ['gap_payoff', 'gap_decomposition', 'gap_insurance', 'gap_premium'];
const record = { status: 'FAIL', browser_version: null, pages: {}, source_sha256: {}, artifact_sha256: {} };
const sha = name => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
function check(ok, label) { if (!ok) throw new Error(label); }
function arrayClose(actual, expected, label) {
  check(actual.length === expected.length, label + ': length');
  actual.forEach((value, i) => check(Number.isFinite(Number(value)) &&
    Math.abs(Number(value) - expected[i]) <= 1e-8, label + '[' + i + ']'));
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
  check(ids.length === 1, key + ': unique plot');
  return page.locator('[id="' + ids[0] + '"]');
}
function expectedTraces(key) {
  const result = {};
  const add = (role, x, y) => { result[role] = { x, y }; };
  const f = reference.figure;
  if (key === 'gap_payoff') {
    const p = f.payoff, t = p.trigger;
    const left = p.stock.map((s, i) => ({ s, i })).filter(row => row.s < t);
    const right = p.stock.map((s, i) => ({ s, i })).filter(row => row.s > t);
    add('call-inactive', [...left.map(row => row.s), t], Array(left.length + 1).fill(0));
    add('call-active', [t, ...right.map(row => row.s)], [t - p.call_strike, ...right.map(row => p.call[row.i])]);
    add('put-active', [...left.map(row => row.s), t], [...left.map(row => p.put[row.i]), p.put_strike - t]);
    add('put-inactive', [t, ...right.map(row => row.s)], Array(right.length + 1).fill(0));
    add('call-limit', [t], [t - p.call_strike]);
    add('put-limit', [t], [p.put_strike - t]);
    add('trigger-value', [t], [0]);
  } else if (key === 'gap_decomposition') {
    for (const [role, field] of [['gap', 'price'], ['vanilla', 'vanilla'], ['cash', 'cash_adjustment']])
      add(role, f.decomposition.map(row => row.K1), f.decomposition.map(row => row[field]));
  } else if (key === 'gap_insurance') {
    const p = f.insurance, t = p.trigger;
    const left = p.stock.map((s, i) => ({ s, i })).filter(row => row.s < t);
    const right = p.stock.filter(s => s >= t);
    add('ordinary', p.stock.map(s => s / 1000), p.ordinary.map(v => v / 1000));
    add('insurer-active', [...left.map(row => row.s / 1000), t / 1000],
      [...left.map(row => p.insurer[row.i] / 1000), (reference.example.K1 - t) / 1000]);
    add('insurer-inactive', right.map(s => s / 1000), Array(right.length).fill(0));
    add('holder', p.stock.map(s => s / 1000), p.holder.map(v => v / 1000));
    add('insurer-limit', [t / 1000], [(reference.example.K1 - t) / 1000]);
    add('insurer-trigger', [t / 1000], [0]);
  } else {
    for (const role of ['insurer', 'holder', 'transfer'])
      add(role, f.premium.map(row => row.cost / 1000), f.premium.map(row => row[role] / 1000));
  }
  return result;
}
async function numeric(plot, key) {
  const actual = await plot.evaluate(el => ({
    meta: el.layout.meta,
    traces: el._fullData.filter(t => t.visible === true).map(t =>
      ({ role: t.meta?.role, x: Array.from(t.x || []), y: Array.from(t.y || []) })),
  }));
  check(actual.meta.section === '26.4' && actual.meta.figure === key, key + ': metadata');
  const expected = expectedTraces(key);
  check(actual.traces.length === Object.keys(expected).length, key + ': trace count');
  for (const [role, row] of Object.entries(expected)) {
    const traces = actual.traces.filter(t => t.role === role);
    check(traces.length === 1, key + ': unique role ' + role);
    arrayClose(traces[0].x, row.x, key + '/' + role + '.x');
    arrayClose(traces[0].y, row.y, key + '/' + role + '.y');
  }
}
async function layout(page, plot, label) {
  await plot.evaluate(el => el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }));
  await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3, await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) return 'plot overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text,.g-xtitle,.g-ytitle')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3 ||
        box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) return 'clipped ' + node.textContent;
    }
    return null;
  });
  check(!issue, label + ': ' + issue);
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), label + ': page overflow');
}
async function inspect(page, surface) {
  const plots = {}, states = [], screenshots = [];
  for (const key of keys) plots[key] = await plotFor(page, key);
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 });
    await settle(page);
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], surface + '/' + key + '/' + width);
      states.push({ figure: key, width, numeric_checked: true });
      const file = 'docs/validation/section-26-4/' + surface + '-' + key + '-' + width + '.png';
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.gap_decomposition.evaluate(async el => {
    const saved = Array.from(el.data[0].y), bad = saved.slice();
    bad[0] += 1;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.gap_decomposition, 'gap_decomposition'); }
  catch (error) { rejected = error.message.includes('gap_decomposition/gap.y'); }
  finally { await plots.gap_decomposition.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, surface + ': changed price accepted');
  await numeric(plots.gap_decomposition, 'gap_decomposition');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}
(async () => {
  check(reference.section === '26.4' && reference.cases.length === 30, 'reference');
  check(numerical.section === '26.4' && numerical.status === 'PASS', 'numerical');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
  record.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const surface of ['portal', 'book']) {
      const page = await context.newPage(), errors = [], requests = [], unapproved = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route(/^https?:/, route => {
        const url = route.request().url(); requests.push(url);
        if (surface === 'book' && url.startsWith('https://cdn.jsdelivr.net/npm/mathjax@3/es5/')) return route.continue();
        unapproved.push(url); return route.abort();
      });
      const html = surface === 'portal' ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html';
      await page.goto('file://' + path.join(root, html));
      if (surface === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ rendered: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.rendered > 20 && math.errors === 0, 'Book MathJax');
        check(await page.locator('h3').filter({ hasText: /^4\.11 ギャップ/ }).count() === 1, 'unique gap lesson');
        check(await page.locator('h4').filter({ hasText: /^4\.11\.[1-6] / }).count() === 6, 'six gap subsections');
        const body = (await page.locator('body').innerText()).replace(/\s+/g, '');
        for (const phrase of ['3,436', '1,896', '630.790352', '1,264.898592', '負の給付', '44.827760%'])
          check(body.includes(phrase), 'Book example phrase missing: ' + phrase);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(!errors.length && !unapproved.length, surface + ': page errors or requests');
      record.pages[surface] = { ...result, external_network_blocked: surface === 'portal',
        page_errors: errors, external_requests: requests, unapproved_requests: unapproved };
      await page.close();
    }
    for (const name of [
      'hullkit/src/hullkit/exotics.py', 'hullkit/src/hullkit/bsm.py', 'hullkit/src/hullkit/_gap_lesson.py',
      'scripts/build_gap_reference.py', 'scripts/verify_gap_browser.cjs',
      'docs/validation/section-26-4/reference.json', 'docs/validation/section-26-4/numerical-check.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/assets/style.css',
    ]) record.source_sha256[name] = sha(name);
    for (const name of ['report/site/exotics.html', 'book/_build/html/notebooks/10_exotics.html',
      ...Object.values(record.pages).flatMap(p => p.screenshots)]) record.artifact_sha256[name] = sha(name);
    record.status = 'PASS';
    record.state_checks = Object.values(record.pages).reduce((n, p) => n + p.states.length, 0);
    record.screenshots = Object.values(record.pages).reduce((n, p) => n + p.screenshots.length, 0);
    console.log(JSON.stringify({ status: record.status, state_checks: record.state_checks, screenshots: record.screenshots }));
  } finally { await browser.close(); }
})().catch(error => { record.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(outDir, 'browser-check.json'), JSON.stringify(record, null, 2) + '\n'));
