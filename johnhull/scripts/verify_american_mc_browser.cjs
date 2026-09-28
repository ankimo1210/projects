// Verify Hull §27.8 figures and text in the rendered Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-27-8');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['american_mc_regression', 'american_mc_boundary', 'american_mc_bias', 'american_mc_dates'];
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
function errorBars(trace, expected, label) {
  arrayClose(trace.error, expected.map(e => 2 * e), `${label} error bars`);
}
async function numeric(plot, key) {
  const { meta, traces } = await plot.evaluate(el => ({ meta: el.layout.meta,
    traces: el._fullData.filter(t => t.visible === true)
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []),
        error: Array.from(t.error_y?.array || []) })) }));
  check(meta.section === '27.8' && meta.figure === key, `${key}: metadata`);
  const hand = data.hand_example;
  if (key === 'american_mc_regression') {
    const steps = hand.least_squares.steps, strike = hand.strike;
    check(traces.length === 6, 'two regressions, the exercise value and the exercised paths');
    const grid = Array.from({ length: 73 }, (_, i) => 0.74 + (1.10 - 0.74) * i / 72);
    ['2', '1'].forEach((time, index) => {
      const step = steps[time], [a, b, c] = step.coefficients;
      arrayClose(traces[2 * index].x, step.spots, `t=${time} spots`);
      arrayClose(traces[2 * index].y, step.discounted_continuation, `t=${time} continuation`);
      arrayClose(traces[2 * index + 1].x, grid, `t=${time} grid`);
      arrayClose(traces[2 * index + 1].y, grid.map(s => a + b * s + c * s * s), `t=${time} regression`);
    });
    arrayClose(traces[4].y, [strike - 0.74, 0], 'exercise value');
    const exercised = ['2', '1'].flatMap(time => steps[time].spots
      .filter((_, i) => steps[time].exercised.includes(steps[time].paths[i])));
    arrayClose(traces[5].x, exercised, 'exercised spots');
    arrayClose(traces[5].y, exercised.map(s => strike - s), 'exercised values');
  } else if (key === 'american_mc_boundary') {
    const steps = hand.boundary.steps;
    check(traces.length === 4, 'two average curves and two optimal intervals');
    ['2', '1'].forEach((time, index) => {
      const step = steps[time], averages = step.averages;
      arrayClose(traces[2 * index].x, [0.70, ...step.candidates.slice(1), 1.12], `t=${time} candidates`);
      arrayClose(traces[2 * index].y, [...averages, averages[averages.length - 1]], `t=${time} averages`);
      arrayClose(traces[2 * index + 1].x, step.interval, `t=${time} interval`);
      const best = Math.max(...averages);
      arrayClose(traces[2 * index + 1].y, [best, best], `t=${time} optimum`);
    });
  } else if (key === 'american_mc_bias') {
    const bias = data.bias;
    check(traces.length === 4, 'fitted and fresh values for both methods');
    ['lsm_in', 'lsm_out', 'boundary_in', 'boundary_out'].forEach((name, index) => {
      arrayClose(traces[index].x, bias.sizes, `bias ${name} sizes`);
      arrayClose(traces[index].y, bias[name].mean.map(m => m - bias.exact), `bias ${name}`);
      errorBars(traces[index], bias[name].standard_error, `bias ${name}`);
    });
  } else {
    const dates = data.dates;
    check(traces.length === 5, 'exact values, three estimates and the American limit');
    arrayClose(traces[0].x, dates.counts, 'exact dates');
    arrayClose(traces[0].y, dates.exact, 'exact Bermudan');
    ['lsm2', 'lsm3', 'boundary'].forEach((name, index) => {
      arrayClose(traces[index + 1].x, dates.counts, `${name} dates`);
      arrayClose(traces[index + 1].y, dates[name].value, `dates ${name}`);
      errorBars(traces[index + 1], dates[name].standard_error, `dates ${name}`);
    });
    arrayClose(traces[4].y, [dates.american, dates.american], 'American limit');
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
      check(await page.locator('h2').filter({ hasText: /14\. モンテカルロ法と/ }).count() === 1,
        'unique Book §14 lesson');
    }
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], `${surface}/${key}/${width}`);
      states.push({ figure: key, width, numeric_checked: true });
      const file = `docs/validation/section-27-8/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.american_mc_bias.evaluate(async el => {
    const saved = Array.from(el.data[3].y);
    const bad = saved.slice(); bad[0] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [3]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.american_mc_bias, 'american_mc_bias'); }
  catch (error) { rejected = error.message.includes('bias boundary_out'); }
  finally { await plots.american_mc_bias.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [3]), original); }
  check(rejected, `${surface}: changed bias value accepted`);
  await numeric(plots.american_mc_bias, 'american_mc_bias');
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
        for (const phrase of ['14.1 8本の経路', '14.2 最小二乗法で', '14.3 行使境界を', '14.4 推定に使った経路を',
          '14.5 行使日を増やす', '14.6 下方バイアス', '15. 三つの数値解法の比較', '16. 練習問題'])
          check(body.includes(phrase), `Book text ${phrase}`);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && requests.length === 0, `${surface}: errors or external requests`);
      record.pages[surface] = { ...result, page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/american_mc.py', 'hullkit/src/hullkit/_american_mc_lesson.py',
      'scripts/build_american_mc_reference.py', 'scripts/verify_american_mc_browser.cjs',
      'docs/validation/section-27-8/reference.json', 'docs/validation/section-27-8/numerical-check.json',
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
