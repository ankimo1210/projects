// Verify Hull §26.1 figures and text in the rendered Book and offline portal.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-1');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['packages_range_forward', 'packages_strikes', 'packages_deferred', 'packages_risk'];
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
      .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []), xaxis: t.xaxis, name: t.name })) }));
  check(meta.section === '26.1' && meta.figure === key, `${key}: metadata`);
  const pay = data.figure_payoffs, grid = pay.grid, F = pay.forward_price;
  const K1 = pay.put_strike, K2 = pay.call_strike, A = pay.amount;
  if (key === 'packages_strikes') {
    const curve = data.strike_curve.points, anchor = data.anchor_17_2;
    check(traces.length === 5, 'strike curve, K2 = K1, F, the printed anchor and the forward');
    arrayClose(traces[0].x, curve.map(p => p.put_strike), 'strike curve K1');
    arrayClose(traces[0].y, curve.map(p => p.call_strike), 'strike curve K2');
    arrayClose(traces[1].x, [curve[0].put_strike, data.strike_curve.forward], 'diagonal x');
    arrayClose(traces[1].y, [curve[0].put_strike, data.strike_curve.forward], 'diagonal y');
    arrayClose(traces[2].y, [data.strike_curve.forward, data.strike_curve.forward], 'forward line');
    arrayClose(traces[3].x, [anchor.put_strike], 'anchor K1');
    arrayClose(traces[3].y, [anchor.call_strike], 'anchor K2');
    arrayClose(traces[4].x, [data.strike_curve.forward], 'K1 = F x');
    arrayClose(traces[4].y, [data.strike_curve.forward], 'K1 = F y');
  } else if (key === 'packages_range_forward') {
    check(traces.length === 3, 'forward, range forward and the two strikes');
    arrayClose(traces[0].x, grid, 'forward grid');
    arrayClose(traces[0].y, grid.map(s => s - F), 'forward payoff');
    arrayClose(traces[1].y, grid.map(s => Math.max(s - K2, 0) - Math.max(K1 - s, 0)), 'range forward payoff');
    arrayClose(traces[2].x, [K1, K2], 'strikes');
    arrayClose(traces[2].y, [0, 0], 'strike payoffs');
  } else if (key === 'packages_deferred') {
    check(traces.length === 4, 'forward, call, deferred call and the break-even');
    arrayClose(traces[0].y, grid.map(s => s - F), 'forward payoff');
    arrayClose(traces[1].y, grid.map(s => Math.max(s - F, 0)), 'call payoff');
    arrayClose(traces[2].y, grid.map(s => Math.max(s - F, 0) - A), 'deferred call payoff');
    arrayClose(traces[3].x, [F + A], 'break-even');
    arrayClose(traces[3].y, [0], 'break-even payoff');
    close(Math.min(...traces[2].y), -A, 'maximum loss');
  } else {
    check(traces.length === 9, 'three measures for three packages');
    const panels = [['loss_pv_quadrature', 'x'], ['probability_of_loss', 'x2'], ['max_loss', 'x3']];
    const names = ['forward', 'range_forward', 'break_forward'];
    panels.forEach(([field, axis], column) => names.forEach((name, row) => {
      const trace = traces[3 * column + row];
      check(trace.xaxis === axis, `${field}/${name}: axis ${trace.xaxis}`);
      arrayClose(trace.y, [data.risk_comparison[name][field]], `${field}/${name}`);
    }));
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
    const labels = Array.from(el.querySelectorAll('.barlayer text.bartext'));
    for (let i = 0; i < labels.length; i += 1) {
      const a = labels[i].getBoundingClientRect();
      if (a.right > frame.right + 3 || a.left < frame.left - 3 || a.top < frame.top - 3) return `clipped bar label ${labels[i].textContent}`;
      for (let j = i + 1; j < labels.length; j += 1) {
        const b = labels[j].getBoundingClientRect();
        if (a.width && b.width && meets(a, b)) return `bar labels overlap ${labels[i].textContent} / ${labels[j].textContent}`;
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
    for (const key of keys) {
      await numeric(plots[key], key);
      await layout(page, plots[key], `${surface}/${key}/${width}`);
      states.push({ figure: key, width, numeric_checked: true });
      const file = `docs/validation/section-26-1/${surface}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.packages_deferred.evaluate(async el => {
    const saved = Array.from(el.data[2].y);
    const bad = saved.slice(); bad[0] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [2]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.packages_deferred, 'packages_deferred'); }
  catch (error) { rejected = error.message.includes('deferred call payoff'); }
  finally { await plots.packages_deferred.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [2]), original); }
  check(rejected, `${surface}: changed deferred payoff accepted`);
  await numeric(plots.packages_deferred, 'packages_deferred');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}
function bookPhrases() {
  const printed = data.anchor_17_2, pay = data.figure_payoffs, risk = data.risk_comparison;
  const table = data.cases[0].range_forwards;
  const F = data.cases[0].forward;
  const rows = [0.5, 0.8, 0.9, 0.95, 0.99].map(fraction => {
    const row = table.find(r => r.put_fraction === fraction);
    check(row, `reference row ${fraction}`);
    const slope = (row.call_strike - F) / (F - row.put_strike);
    return `K1/F=${fraction.toFixed(2)}: K1=${row.put_strike.toFixed(4)}, K2=${row.call_strike.toFixed(4)}, ` +
      `K2/F=${(row.call_strike / F).toFixed(3)}, (K2-F)/(F-K1)=${slope.toFixed(4)}`;
  });
  return { rows, extra: [
    `K1 = 1.3000 → K2 = ${printed.call_strike.toFixed(6)}（原典の丸め値 ${printed.printed.call_strike.toFixed(4)}）`,
    `売りプット p(K1) = ${printed.put_at_printed_strikes.toFixed(6)}（原典 ${printed.printed.premium.toFixed(4)}）`,
    `丸め値 K2 = 1.3414 のコール = ${printed.call_at_printed_strikes.toFixed(6)}`,
    `後払い額 A = c·e^(rT) = ${pay.amount.toFixed(6)}`,
    `損益分岐 K + A = ${pay.breakeven.toFixed(6)}`,
    `期待損失PV=${risk.range_forward.loss_pv_quadrature.toFixed(5)}、損失確率=${risk.range_forward.probability_of_loss.toFixed(3)}、最大損失=${risk.range_forward.max_loss.toFixed(4)}`,
    `期待損失PV=${risk.forward.loss_pv_quadrature.toFixed(5)}、損失確率=${risk.forward.probability_of_loss.toFixed(3)}、最大損失=${risk.forward.max_loss.toFixed(4)}`,
    `期待損失PV=${risk.break_forward.loss_pv_quadrature.toFixed(5)}、損失確率=${risk.break_forward.probability_of_loss.toFixed(3)}、最大損失=${risk.break_forward.max_loss.toFixed(4)}`,
    `K1=0.3F: K2=${data.strike_curve.points[0].call_strike.toFixed(4)}`,
  ] };
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
      const html = surface === 'portal' ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html';
      await page.goto('file://' + path.join(root, html));
      if (surface === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ rendered: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.rendered > 20 && math.errors === 0, 'Book MathJax');
        check(await page.locator('h3').filter({ hasText: /^4\.8 パッケージ/ }).count() === 1, 'unique Book §4.8 lesson');
        check(await page.locator('h4').filter({ hasText: /^4\.8\.[1-6] / }).count() === 6, 'six Book §4.8 subsections');
        const body = await page.locator('body').innerText();
        const phrases = bookPhrases();
        const missing = [...phrases.rows, ...phrases.extra].filter(text => !body.includes(text));
        check(missing.length === 0, `Book printed values differ from the reference: ${missing.join(' | ')}`);
        record.book_math = math;
        record.book_phrases = phrases.rows.length + phrases.extra.length;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && requests.length === 0, `${surface}: errors or external requests`);
      record.pages[surface] = { ...result, page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of [
      'hullkit/src/hullkit/packages.py', 'hullkit/src/hullkit/_packages_lesson.py',
      'scripts/build_packages_reference.py', 'scripts/verify_packages_browser.cjs',
      'docs/validation/section-26-1/reference.json', 'docs/validation/section-26-1/numerical-check.json',
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
