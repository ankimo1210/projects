// Inspect Hull §27.2 in the rendered Book and offline portal against saved independent data.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-27-2');
const data = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['stochvol_term', 'stochvol_mixing', 'stochvol_correlation', 'stochvol_sabr'];
const sabrStates = { rho: 'ρを変える（ν=0.4）', nu: 'νを変える（ρ=0）' };
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
const pct = values => values.map(v => 100 * v);

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
async function visible(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true)
    .map(t => ({ name: t.name, x: Array.from(t.x || []), y: Array.from(t.y || []) })));
}
async function numeric(plot, key, state) {
  const rows = await visible(plot);
  const meta = await plot.evaluate(el => el.layout.meta);
  check(meta.section === '27.2' && meta.figure === key, `${key}: metadata`);
  const heston = data.heston;
  const moneyness = heston.strikes.map(k => k / heston.spot);
  if (key === 'stochvol_term') {
    const term = data.term_structure;
    check(rows.length === 3, 'term traces');
    arrayClose(rows[0].x, term.times, 'term times');
    arrayClose(rows[0].y, pct(term.sigma), 'instantaneous vol');
    arrayClose(rows[1].y, pct(term.remaining_rms_vol), 'remaining RMS vol');
    arrayClose(rows[2].y, [25, 25], 'arithmetic vol', 1e-12);
    close(term.average_variance, 0.065, 'Hull average variance', 1e-15);
  } else if (key === 'stochvol_mixing') {
    check(rows.length === 2, 'mixing traces');
    arrayClose(rows[0].x, moneyness, 'mixing moneyness');
    arrayClose(rows[0].y, pct(heston.smiles['+0.0'].implied_vol), 'rho=0 implied vol');
    arrayClose(rows[1].y, [100 * heston.flat_volatility, 100 * heston.flat_volatility], 'flat BSM vol');
  } else if (key === 'stochvol_correlation') {
    check(rows.length === 3, 'correlation traces');
    ['-0.7', '+0.0', '+0.7'].forEach((rho, i) => {
      arrayClose(rows[i].x, moneyness, `rho ${rho} moneyness`);
      arrayClose(rows[i].y, pct(heston.smiles[rho].implied_vol), `rho ${rho} implied vol`);
    });
  } else {
    const smile = data.sabr;
    check(rows.length === 4, `SABR ${state} visible traces`);
    const group = state === 'rho' ? ['-0.6', '+0.0', '+0.6'].map(k => smile.rho_group[k])
      : ['0.2', '0.4', '0.8'].map(k => smile.nu_group[k]);
    group.forEach((vols, i) => {
      arrayClose(rows[i].x, pct(smile.strikes), `SABR ${state} strikes ${i}`);
      arrayClose(rows[i].y, pct(vols), `SABR ${state} vols ${i}`);
    });
    arrayClose(rows[3].y, pct(smile.monte_carlo.rows.map(r => r.implied_vol)), 'SABR Monte Carlo');
  }
}
async function select(page, plot, state) {
  const labels = await plot.evaluate(el => el.layout.updatemenus[0].buttons.map(b => b.label));
  check(JSON.stringify(labels) === JSON.stringify([sabrStates.rho, sabrStates.nu]), 'exact SABR menu states');
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').nth(labels.indexOf(sabrStates[state])).click();
  const expected = state === 'rho' ? 'ρ=-0.6' : 'ν=0.2';
  await page.waitForFunction(({ id, expected }) => {
    const el = document.getElementById(id);
    return el._fullData.filter(t => t.visible === true)[0]?.name === expected;
  }, { id: await plot.getAttribute('id'), expected });
  await settle(page);
}
async function center(page, plot) {
  await plot.evaluate(el => el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }));
  await settle(page);
  const shift = await plot.evaluate(el => {
    const header = Math.max(0, ...Array.from(document.querySelectorAll('.topbar,.bd-header-article'))
      .map(n => n.getBoundingClientRect()).filter(r => r.top >= -1 && r.top < 150).map(r => r.bottom));
    return Math.min(0, el.getBoundingClientRect().top - header - 12);
  });
  if (shift < 0) { await page.evaluate(dy => window.scrollBy(0, dy), shift); await settle(page); }
}
async function layout(page, plot, label) {
  await center(page, plot);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3,
    await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) return 'plot overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text,.updatemenu-header')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3
        || box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) return `clipped ${node.textContent}`;
    }
    const title = el.querySelector('.gtitle')?.getBoundingClientRect();
    const menu = el.querySelector('.updatemenu-header')?.getBoundingClientRect();
    if (title && menu && title.right > menu.left && title.bottom > menu.top && menu.bottom > title.top)
      return 'title overlaps menu';
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
      const lesson = page.locator('h2').filter({ hasText: /8\. 確率ボラティリティ・モデル/ }).locator('xpath=..');
      check(await lesson.count() === 1, 'unique Book §8 lesson');
      check(await lesson.evaluate(el => Array.from(el.querySelectorAll('div.math, mjx-container[display="true"]'))
        .every(node => node.scrollWidth <= node.clientWidth + 3)), `Book math overflow at ${width}`);
    }
    for (const key of keys) {
      for (const state of key === 'stochvol_sabr' ? ['rho', 'nu'] : ['default']) {
        if (key === 'stochvol_sabr') await select(page, plots[key], state);
        await numeric(plots[key], key, state);
        await layout(page, plots[key], `${surface}/${key}/${state}/${width}`);
        states.push({ figure: key, state, width, numeric_checked: true });
        const suffix = key === 'stochvol_sabr' && state === 'nu' ? '-nu' : '';
        const file = `docs/validation/section-27-2/${surface}-${key}${suffix}-${width}.png`;
        await plots[key].screenshot({ path: path.join(root, file) });
        screenshots.push(file);
      }
      if (key === 'stochvol_sabr') await select(page, plots[key], 'rho');
    }
  }
  const original = await plots.stochvol_mixing.evaluate(async el => {
    const original = Array.from(el.data[0].y);
    const bad = original.slice(); bad[12] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return original;
  });
  let rejected = false;
  try { await numeric(plots.stochvol_mixing, 'stochvol_mixing', 'default'); }
  catch (error) { rejected = error.message.includes('rho=0 implied vol'); }
  finally { await plots.stochvol_mixing.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), original); }
  check(rejected, `${surface}: altered implied volatility was accepted`);
  await numeric(plots.stochvol_mixing, 'stochvol_mixing', 'default');
  return { states, screenshots, numeric_mutation_rejected: rejected };
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
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
        for (const phrase of ['8.1 時間で決まるボラ', '8.2 確率ボラ', '8.3 無相関なら', '8.4 相関と Heston',
          '8.5 SABR', '8.6 GARCH', '0.065', '25.5%', '88–128', '9. Longstaff-Schwartz', '10. 練習問題'])
          check(body.includes(phrase), `Book text ${phrase}`);
        record.book_math = math;
      }
      const result = await inspect(page, surface);
      check(errors.length === 0 && requests.length === 0, `${surface}: JS errors or external requests`);
      record.pages[surface] = { ...result, page_errors: errors, external_requests: requests };
      await page.close();
    }
    for (const file of ['hullkit/src/hullkit/stochastic_volatility.py', 'hullkit/src/hullkit/_stochastic_volatility_lesson.py',
      'scripts/build_stochastic_volatility_reference.py', 'scripts/verify_stochastic_volatility_browser.cjs',
      'docs/validation/section-27-2/reference.json', 'docs/validation/section-27-2/numerical-check.json',
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
