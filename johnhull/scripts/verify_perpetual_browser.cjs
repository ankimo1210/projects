// Verify Hull §26.2 shared figures in the rendered Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-2');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(outDir, 'numerical-check.json'), 'utf8'));
const keys = [
  'perpetual_value', 'perpetual_boundaries', 'perpetual_zero_dividend',
  'perpetual_convergence',
];
const cases = reference.cases;
const anchor = cases.find(item => item.label === 'symmetric');
const zeroYield = cases.find(item => item.label === 'zero_yield');
const record = { status: 'FAIL', browser_version: null, pages: {}, source_sha256: {}, artifact_sha256: {} };
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex');
function check(ok, message) { if (!ok) throw new Error(message); }
function close(actual, expected, label) {
  check(Number.isFinite(Number(actual)) && Math.abs(Number(actual) - Number(expected)) <= 1e-8,
    `${label}: ${actual} != ${expected}`);
}
function arrayClose(actual, expected, label) {
  check(actual.length === expected.length, `${label}: length ${actual.length} != ${expected.length}`);
  actual.forEach((value, index) => {
    if (expected[index] === null) check(value === null || value === undefined,
      `${label}[${index}]: ${value} != null`);
    else close(value, expected[index], `${label}[${index}]`);
  });
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
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []), name: t.name })) }));
  check(meta.section === '26.2' && meta.figure === key, `${key}: metadata`);
  const figure = reference.figure;
  if (key === 'perpetual_value') {
    check(traces.length >= 4, 'call, put and two intrinsic-value traces');
    for (const [index, field] of ['call', 'put', 'call_intrinsic', 'put_intrinsic'].entries()) {
      arrayClose(traces[index].x, figure.spot_grid, `${field} spot grid`);
      arrayClose(traces[index].y, figure[field], `${field} value`);
    }
  } else if (key === 'perpetual_boundaries') {
    check(traces.length >= 3, 'call and put exercise boundaries and current spot');
    const labels = traces[0].x;
    check(labels.length === cases.length, 'boundary case count');
    check(labels.every((label, index) => label === traces[1].x[index] && label === traces[2].x[index]),
      'boundary case labels');
    const call = cases.map(item => item.call.boundary === null
      ? null : item.call.boundary / item.parameters.strike);
    const put = cases.map(item => item.put.boundary / item.parameters.strike);
    arrayClose(traces[0].y, call, 'call H1/K');
    arrayClose(traces[1].y, put, 'put H2/K');
    arrayClose(traces[2].y,
      cases.map(item => item.parameters.spot / item.parameters.strike), 'current S0/K');
  } else if (key === 'perpetual_zero_dividend') {
    check(traces.length >= 3, 'q=0 value, intrinsic value and saved reference spot');
    const grid = figure.spot_grid, strike = zeroYield.parameters.strike;
    arrayClose(traces[0].x, grid, 'q=0 spot grid');
    arrayClose(traces[0].y, grid, 'q=0 call V=S');
    arrayClose(traces[1].x, grid, 'intrinsic spot grid');
    arrayClose(traces[1].y, grid.map(spot => Math.max(spot - strike, 0)), 'call intrinsic value');
    arrayClose(traces[2].x, [zeroYield.parameters.spot], 'q=0 reference spot');
    arrayClose(traces[2].y, [zeroYield.call.value], 'q=0 reference value');
  } else {
    check(traces.length >= 6, 'finite and perpetual call/put prices and gaps');
    const rows = anchor.lattice.rows;
    const maturities = rows.map(row => row.maturity);
    for (let index = 0; index < 4; index += 1) {
      arrayClose(traces[index].x, maturities, `convergence maturity ${index}`);
    }
    arrayClose(traces[0].y, rows.map(row => row.call), 'finite call');
    arrayClose(traces[1].y, rows.map(row => row.put), 'finite put');
    arrayClose(traces[2].y, rows.map(() => anchor.call.value), 'perpetual call');
    arrayClose(traces[3].y, rows.map(() => anchor.put.value), 'perpetual put');
    arrayClose(traces[4].y, rows.map(row => row.call_gap), 'call gap');
    arrayClose(traces[5].y, rows.map(row => row.put_gap), 'put gap');
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
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text,.g-xtitle,.g-ytitle')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3 ||
          box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) {
        return `clipped ${node.textContent}: frame=${[frame.left, frame.right, frame.top, frame.bottom].map(Math.round)} ` +
          `label=${[box.left, box.right, box.top, box.bottom].map(Math.round)}`;
      }
    }
    const gap = 4;
    const meets = (a, b) => a.left < b.right + gap && b.left < a.right + gap &&
      a.top < b.bottom + gap && b.top < a.bottom + gap;
    for (const [title, ticks] of [['.ytitle', '.yaxislayer-above text'], ['.xtitle', '.xaxislayer-above text']]) {
      const label = el.querySelector(title);
      if (!label) continue;
      const box = label.getBoundingClientRect();
      for (const tick of el.querySelectorAll(ticks)) {
        const mark = tick.getBoundingClientRect();
        if (mark.width && mark.height && meets(box, mark)) return `overlap ${label.textContent} / ${tick.textContent}`;
      }
    }
    const legend = el.querySelector('.legend');
    if (legend) {
      const legendBox = legend.getBoundingClientRect();
      for (const tick of el.querySelectorAll('.xaxislayer-above text')) {
        const box = tick.getBoundingClientRect();
        if (box.width && box.height && meets(box, legendBox)) {
          return `x tick overlaps legend: ${tick.textContent}`;
        }
      }
    }
    const barLabels = Array.from(el.querySelectorAll('.barlayer text.bartext'));
    for (let i = 0; i < barLabels.length; i += 1) {
      const a = barLabels[i].getBoundingClientRect();
      if (!a.width || !a.height) continue;
      if (a.right > frame.right + 3 || a.left < frame.left - 3 || a.top < frame.top - 3) {
        return `clipped bar label ${barLabels[i].textContent}: ` +
          `frame=${[frame.left, frame.right, frame.top, frame.bottom].map(Math.round)} ` +
          `label=${[a.left, a.right, a.top, a.bottom].map(Math.round)}`;
      }
      for (let j = i + 1; j < barLabels.length; j += 1) {
        const b = barLabels[j].getBoundingClientRect();
        if (b.width && b.height && meets(a, b)) {
          return `bar labels overlap ${barLabels[i].textContent} / ${barLabels[j].textContent}`;
        }
      }
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
      const file = `docs/validation/section-26-2/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.perpetual_value.evaluate(async el => {
    const saved = Array.from(el.data[0].y);
    const bad = saved.slice(); bad[0] += 1;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.perpetual_value, 'perpetual_value'); }
  catch (error) { rejected = error.message.includes('call value'); }
  finally { await plots.perpetual_value.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, `${surface}: changed call value accepted`);
  await numeric(plots.perpetual_value, 'perpetual_value');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}
function bookPhrases() {
  const rows = anchor.lattice.rows;
  const last = rows[rows.length - 1];
  const zeroLast = zeroYield.lattice.rows.at(-1);
  return [
    `コール価値${zeroYield.call.value.toFixed(0)}、プット境界${zeroYield.put.boundary.toFixed(4)}、プット価値${zeroYield.put.value.toFixed(4)}です。`,
    `${rows.map(row => row.call.toFixed(4)).join('、')}と永久値${anchor.call.value.toFixed(0)}へ近づきます。`,
    `${last.maturity.toFixed(0)}年・${last.steps}ステップでも差は約${last.call_gap.toFixed(4)}残ります。`,
    `無配当コールも同じ計算で160年の価格${zeroLast.call.toFixed(4)}`,
    '満期を有限にした効果とツリー格子の誤差の両方',
    '原典§26.2に数値例はないため',
  ];
}

(async () => {
  check(reference.section === '26.2' && anchor && zeroYield, 'independent reference');
  check(numerical.section === '26.2' && numerical.status === 'PASS', 'independent numerical verification');
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
        if (surface === 'book' && url.startsWith('https://cdn.jsdelivr.net/npm/mathjax@3/es5/')) {
          return route.continue();
        }
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
        check(await page.locator('h3').filter({ hasText: /^4\.9 永久/ }).count() === 1,
          'unique Book §4.9 lesson');
        check(await page.locator('h4').filter({ hasText: /^4\.9\.[1-6] / }).count() === 6,
          'six Book §4.9 subsections');
        const body = (await page.locator('body').innerText()).replace(/\s+/g, '');
        const phrases = bookPhrases();
        const missing = phrases.filter(phrase => !body.includes(phrase.replace(/\s+/g, '')));
        check(missing.length === 0, `Book printed values differ from the independent reference: ${missing.join(' | ')}`);
        record.book_math = math;
        record.book_phrases = phrases.length;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && unapproved.length === 0, `${surface}: page errors or unapproved external requests`);
      record.pages[surface] = { ...result, external_network_blocked: surface === 'portal',
        page_errors: errors, external_requests: requests,
        unapproved_requests: unapproved };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/perpetual_american.py', 'hullkit/src/hullkit/_perpetual_american_lesson.py',
      'scripts/build_perpetual_reference.py', 'scripts/verify_perpetual_browser.cjs',
      'docs/validation/section-26-2/reference.json', 'docs/validation/section-26-2/numerical-check.json',
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
