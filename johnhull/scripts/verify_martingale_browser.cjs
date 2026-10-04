// Inspect Hull §28.3 conditional martingales and same-payoff Q/G pricing on both surfaces.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-28-3');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(outDir, 'numerical-check.json'), 'utf8'));
const keys = ['martingale_ito', 'martingale_conditional', 'martingale_conditional_mc', 'martingale_pricing'];
const record = { status: 'FAIL', browser_version: null, pages: {}, source_sha256: {}, artifact_sha256: {} };
const sha = name => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
function check(ok, label) { if (!ok) throw new Error(label); }
function arrayClose(actual, expected, label) {
  check(actual.length === expected.length, label + ': length');
  actual.forEach((value, i) => check(typeof expected[i] === 'string'
    ? value === expected[i]
    : Number.isFinite(Number(value)) && Math.abs(Number(value)-expected[i]) <= 1e-8,
    label + '[' + i + ']'));
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
  const result = {}, f = reference.figure;
  const add = (role,x,y,error) => { result[role]={x,y,error}; };
  if (key === 'martingale_ito') add('ito',f.ito.labels,f.ito.values);
  else if (key === 'martingale_conditional') f.conditional.curves.forEach(c=>add('lambda-'+c.risk_price,f.conditional.horizons,c.mean));
  else {
    const rows = key === 'martingale_conditional_mc' ? numerical.conditional_mc : numerical.pricing;
    const labels = key === 'martingale_conditional_mc' ? f.conditional_mc.labels : f.pricing.labels;
    add('mc',labels,rows.map(r=>r.mean-r.reference),rows.map(r=>1.96*r.se));
    add('reference',labels,rows.map(()=>0));
  }
  return result;
}
async function numeric(plot, key) {
  const actual = await plot.evaluate(el => ({
    meta: el.layout.meta, shapes: el.layout.shapes || [],
    traces: el._fullData.filter(t => t.visible === true).map(t =>
      ({ role: t.meta?.role, x: Array.from(t.x || []), y: Array.from(t.y || []), customdata: t.customdata ? Array.from(t.customdata) : null, error: t.error_y?.visible ? Array.from(t.error_y.array || []) : null })),
  }));
  check(actual.meta.section === '28.3' && actual.meta.figure === key, key + ': metadata');
  const expected = expectedTraces(key);
  check(actual.traces.length === Object.keys(expected).length, key + ': trace count');
  for (const [role, row] of Object.entries(expected)) {
    const traces = actual.traces.filter(t => t.role === role);
    check(traces.length === 1, key + ': unique role ' + role);
    arrayClose(traces[0].x, row.x, key + '/' + role + '.x');
    arrayClose(traces[0].y, row.y, key + '/' + role + '.y');
    if (row.customdata) {
      check(traces[0].customdata !== null, key + ': missing payment cashflows');
      check(traces[0].customdata.length === row.customdata.length, key + ': payment row count');
      row.customdata.forEach((values,i)=>arrayClose(traces[0].customdata[i],values,key+'/'+role+'.customdata['+i+']'));
    }
    if (row.error) {
      check(traces[0].error !== null, key + ': missing MC error bars');
      arrayClose(traces[0].error, row.error, key + '/' + role + '.error');
    }
  }
}
async function layout(page, plot, label) {
  check(await plot.evaluate(el => el.clientWidth >= 700), label + ': conditional labels require a readable full row');
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
      const file = 'docs/validation/section-28-3/' + surface + '-' + key + '-' + width + '.png';
      await plots[key].screenshot({ path: path.join(root, file) });
      screenshots.push(file);
    }
  }
  const original = await plots.martingale_ito.evaluate(async el => {
    const saved = Array.from(el.data[0].y), bad = saved.slice();
    bad[0] += 1;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return saved;
  });
  let rejected = false;
  try { await numeric(plots.martingale_ito, 'martingale_ito'); }
  catch (error) { rejected = error.message.includes('martingale_ito/ito.y'); }
  finally { await plots.martingale_ito.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, surface + ': changed price accepted');
  await numeric(plots.martingale_ito, 'martingale_ito');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}
(async () => {
  check(reference.section === '28.3' && reference.cases.length === 6, 'reference');
  check(numerical.section === '28.3' && numerical.status === 'PASS', 'numerical');
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
        check(await page.locator('h2').filter({hasText:/^6B\. マルチンゲール/}).count()===1,'unique martingale parent');
        check(await page.locator('h3').filter({hasText:/^6B\.[1-6] /}).count()===6,'six martingale subsections');
        const body=(await page.locator('body').innerText()).replace(/\s+/g,'');
        for (const phrase of ['ConditionalAPI:9states/timecombinations','Samesyntheticcall:17.2494832790','別初期市場']) check(body.includes(phrase),'Book phrase missing: '+phrase);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(!errors.length && !unapproved.length, surface + ': page errors or requests');
      record.pages[surface] = { ...result, external_network_blocked: surface === 'portal',
        page_errors: errors, external_requests: requests, unapproved_requests: unapproved };
      await page.close();
    }
    for (const name of [
      'hullkit/src/hullkit/_martingales.py', 'hullkit/src/hullkit/risk_premium.py', 'hullkit/src/hullkit/_martingale_lesson.py',
      'scripts/build_martingale_reference.py', 'scripts/verify_martingale_browser.cjs', 'scripts/verify_martingale_numerics.py', 'hullkit/src/hullkit/bsm.py',
      'docs/validation/section-28-3/reference.json', 'docs/validation/section-28-3/numerical-check.json',
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
