// Verify Hull §26.3 values, layout and contract text in Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-3');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(outDir, 'numerical-check.json'), 'utf8'));
const keys = ['scheduled_ordering', 'scheduled_exercise', 'scheduled_warrant', 'scheduled_frequency'];
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
  check(meta.section === '26.3' && meta.figure === key, `${key}: metadata`);
  if (key === 'scheduled_ordering') {
    const rows = reference.cases.slice(0, 4);
    check(traces.length >= 1 && traces[0].x.every((x, i) => x === rows[i].label), 'ordering labels');
    arrayClose(traces[0].y, rows.map(row => row.price), 'ordering prices');
  } else if (key === 'scheduled_exercise') {
    const lattice = reference.figure.exercise_lattice;
    check(traces.length >= 2, 'exercise candidate and decision traces');
    arrayClose(traces[0].x, lattice.candidates.map(row => row.step), 'candidate steps');
    arrayClose(traces[0].y, lattice.candidates.map(row => row.stock), 'candidate stock');
    arrayClose(traces[1].x, lattice.points.map(row => row.step), 'exercise steps');
    arrayClose(traces[1].y, lattice.points.map(row => row.stock), 'exercise stock');
  } else if (key === 'scheduled_warrant') {
    check(traces.length >= 1, 'warrant strike trace');
    arrayClose(traces[0].x, reference.figure.warrant_years, 'warrant years');
    arrayClose(traces[0].y, reference.figure.warrant_strikes, 'warrant strikes');
  } else {
    const ladder = reference.figure.exercise_frequency;
    check(traces.length >= 1, 'exercise frequency trace');
    arrayClose(traces[0].x, ladder.date_counts, 'frequency date counts');
    arrayClose(traces[0].y, ladder.prices, 'frequency prices');
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
      const file = `docs/validation/section-26-3/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.scheduled_ordering.evaluate(async el => {
    const saved = Array.from(el.data[0].y);
    const bad = saved.slice(); bad[0] += 1;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.scheduled_ordering, 'scheduled_ordering'); }
  catch (error) { rejected = error.message.includes('ordering prices'); }
  finally { await plots.scheduled_ordering.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, `${surface}: changed price accepted`);
  await numeric(plots.scheduled_ordering, 'scheduled_ordering');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}

(async () => {
  check(reference.section === '26.3' && reference.cases.length === 5, 'independent reference');
  check(numerical.section === '26.3' && numerical.status === 'PASS', 'independent numerical verification');
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
        check(await page.locator('h3').filter({ hasText: /^4\.10 非標準/ }).count() === 1,
          'unique Book §4.10 lesson');
        check(await page.locator('h4').filter({ hasText: /^4\.10\.[1-6] / }).count() === 6,
          'six Book §4.10 subsections');
        const body = (await page.locator('body').innerText()).replace(/\s+/g, '');
        for (const phrase of [reference.warrant.price.toFixed(4), '原典に価格はない',
          '暗黙に丸め', '$30', '$32', '$33'])
          check(body.includes(phrase.replace(/\s+/g, '')), `Book contract phrase missing: ${phrase}`);
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
      'hullkit/src/hullkit/nonstandard_american.py', 'hullkit/src/hullkit/_nonstandard_american_lesson.py',
      'scripts/build_nonstandard_reference.py', 'scripts/verify_nonstandard_browser.cjs',
      'docs/validation/section-26-3/reference.json', 'docs/validation/section-26-3/numerical-check.json',
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
