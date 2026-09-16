// §26.13 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-13/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const record = JSON.parse(fs.readFileSync(path.join(out, 'numerical-check.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['asian_payoff', 'asian_distribution', 'asian_observations', 'asian_error'];
const scenarios = {
  asian_payoff: ['average_price', 'average_strike'],
  asian_distribution: reference.distribution.map(r => r.market),
  asian_observations: reference.observations.map(r => r.market),
  asian_error: ['call', 'put'],
};

const result = { checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };
function check(ok, message) { if (!ok) throw new Error(message); }
function close(a, b, message, tol = 1e-8) { check(Number.isFinite(a) && Math.abs(a - b) <= tol, `${message}: ${a} != ${b}`); }
function hash(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }
function normalCdf(x) { // Abramowitz-Stegun 26.2.17, independent of the page.
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
  const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
  return x >= 0 ? 1 - p : p;
}
async function traces(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true)
    .map(t => ({ meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []), name: t.name, mode: t.mode,
      error_y: t.error_y && t.error_y.array ? Array.from(t.error_y.array) : null,
      line_color: t.line?.color })));
}
function trace(rows, role) {
  const found = rows.filter(t => t.meta?.role === role);
  check(found.length === 1, 'Expected unique trace ' + role);
  return found[0];
}
function point(row, x, expected, message, tol = 1e-8) {
  const i = row.x.findIndex(v => typeof v === 'number' && Math.abs(v - x) < 1e-10);
  check(i >= 0, 'Missing point ' + message);
  close(row.y[i], expected, message, tol);
}

function numeric(rows, key, state, title) {
  check(rows.every(t => t.meta.scenario === state), 'Wrong visible scenario');
  if (key === 'asian_payoff') {
    check(rows.length === 5, 'Payoff trace count');
    const pin = reference.payoff;
    const pathRow = trace(rows, 'path');
    check(JSON.stringify(pathRow.y) === JSON.stringify(pin.path), 'Displayed path');
    for (const [role, value] of [['average', pin.average], ['strike', pin.strike], ['terminal', pin.terminal]])
      close(trace(rows, role).y[0], value, 'Displayed ' + role);
    const bars = trace(rows, 'payoff');
    check(bars.x.length === 3, 'Three payoff bars');
    close(bars.y[0], pin.payoffs[state][0], 'Call payoff');
    close(bars.y[1], pin.payoffs[state][1], 'Put payoff');
    close(bars.y[2], pin.payoffs.vanilla_call, 'Vanilla payoff');
    // The average is drawn as a level, so it must never be read as the terminal value.
    check(Math.abs(pin.average - pin.terminal) > 1e-9, 'Average and terminal must differ');
  } else if (key === 'asian_distribution') {
    check(rows.length === 3, 'Distribution trace count');
    const pin = reference.distribution.find(p => p.market === state);
    close(trace(rows, 'moment').x[0], pin.moment_1, 'Displayed M1');
    const fitted = trace(rows, 'fitted'), simulated = trace(rows, 'simulated');
    check(fitted.x.length === simulated.x.length && fitted.x.length > 40, 'Shared centres');
    fitted.x.forEach((centre, i) => {
      close(simulated.x[i], centre, 'Aligned centres');
      const z = (Math.log(centre) - pin.location) / pin.scale;
      const density = Math.exp(-0.5 * z * z) / (centre * pin.scale * Math.sqrt(2 * Math.PI));
      close(fitted.y[i], density, 'Fitted lognormal density at ' + centre, 1e-9);
    });
    const shown = title.match(/整合ボラ ([\d.]+)%、歪度 実測 ([-\d.]+) 対 当てはめ ([-\d.]+)/);
    check(!!shown, 'Distribution title format: ' + title);
    close(Number(shown[1]) / 100, pin.matched_volatility, 'Displayed matched volatility', 5e-5);
    close(Number(shown[3]), pin.fitted_skewness, 'Displayed fitted skewness', 5e-4);
    check(Number(shown[2]) > Number(shown[3]), 'Simulated skewness exceeds the fit: ' + title);
    // The simulated density must not be the fitted one redrawn.
    check(simulated.y.some((v, i) => Math.abs(v - fitted.y[i]) > 1e-6), 'Distinct densities');
  } else if (key === 'asian_observations') {
    check(rows.length === 4, 'Observation trace count');
    const pin = reference.observations.find(p => p.market === state);
    const approximation = trace(rows, 'approximation'), ref = trace(rows, 'reference');
    const geometric = trace(rows, 'geometric'), continuous = trace(rows, 'continuous');
    check(JSON.stringify(approximation.x) === '[12,52,250]', 'Observation counts');
    pin.entries.forEach((entry, i) => {
      close(approximation.y[i], entry.turnbull_wakeman, 'Displayed moment match', 1e-9);
      close(geometric.y[i], entry.geometric, 'Displayed geometric price', 1e-9);
      const band = 4 * Math.hypot(ref.error_y[i] / 4, entry.standard_error);
      check(Math.abs(ref.y[i] - entry.reference) <= Math.max(band, 1e-9), 'Reference within 4 SE');
      check(geometric.y[i] <= ref.y[i] + 1e-9, 'Geometric is a lower bound');
      check(approximation.y[i] > continuous.y[0] - 1e-9, 'Discrete above the continuous limit');
    });
    close(continuous.y[0], pin.continuous_turnbull_wakeman, 'Independent continuous price', 1e-8);
    check(ref.y[0] >= ref.y[2], 'Refining the grid does not raise the price');
    const gap = approximation.y[2] - ref.y[2];
    const shown = title.match(/上乗せ ([+-][\d.]+)/);
    check(!!shown, 'Observation title format: ' + title);
    close(Number(shown[1]), gap, 'Displayed 250-observation gap', 5e-5);
  } else {
    const shown = {};
    for (const row of rows) {
      check(row.meta.role.startsWith('market:'), 'Error trace role');
      const market = row.meta.role.slice(7);
      row.x.forEach((ratio, i) => {
        const pin = reference.errors.find(p => p.market === market && p.contract === state
          && Math.abs(p.spot_ratio - ratio) < 1e-12);
        check(!!pin, `Unpinned error point ${market}/${state}/${ratio}`);
        close(row.y[i], pin.relative_error_percent, 'Displayed relative error', 1e-9);
        shown[`${market}/${ratio}`] = row.y[i];
      });
    }
    const values = Object.values(shown);
    check(values.length > 0, 'Error points');
    const colors = rows.map(r => r.line_color);
    check(new Set(colors).size === colors.length, 'Two markets share a colour: ' + colors.join(','));
    const extreme = state === 'put' ? Math.max(...values) : Math.min(...values);
    const worst = state === 'put' ? record.approximation_error.largest_overprice
      : record.approximation_error.largest_underprice;
    // The figure shows 52 observations; the record ranges over 2/12/52/250.
    check(Math.abs(extreme) <= Math.abs(100 * worst.relative_error) + 1e-9,
      'Shown error exceeds the recorded extreme');
    const title_worst = title.match(/最大 ([+-][\d.]+)%/);
    check(!!title_worst, 'Error title format: ' + title);
    const largest = values.reduce((a, b) => Math.abs(a) >= Math.abs(b) ? a : b);
    close(Number(title_worst[1]), largest, 'Displayed worst error', 5e-3);
  }
}

async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => !document.getAnimations().some(a => a.playState === 'running'), null, { timeout });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function center(page, locator) {
  await locator.evaluate(el => el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }));
  await settle(page);
  const shift = await locator.evaluate(el => {
    const bottom = Math.max(0, ...Array.from(document.querySelectorAll('.topbar,.bd-header-article'))
      .map(n => n.getBoundingClientRect()).filter(r => r.top >= -1 && r.top < 150).map(r => r.bottom));
    return Math.min(0, el.getBoundingClientRect().top - bottom - 12);
  });
  if (shift < 0) { await page.evaluate(dy => window.scrollBy(0, dy), shift); await settle(page); }
}
async function plotFor(page, key) {
  await page.waitForFunction(key => Array.from(document.querySelectorAll('.plotly-graph-div'))
    .some(el => el.layout?.meta?.figure === key && el._fullLayout), key, { timeout });
  const ids = await page.locator('.plotly-graph-div').evaluateAll((els, key) =>
    els.filter(el => el.layout?.meta?.figure === key).map(el => el.id), key);
  check(ids.length === 1, 'Unique plot ' + key);
  return page.locator('[id="' + ids[0] + '"]');
}
async function select(page, plot, state) {
  const label = await plot.evaluate((el, state) =>
    el.layout.updatemenus[0].buttons.find(b => b.args[1].meta.scenario === state).label, state);
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').filter({ hasText: label }).click();
  await page.waitForFunction(({ id, state }) => document.getElementById(id).layout.meta.scenario === state,
    { id: await plot.getAttribute('id'), state }, { timeout });
  await settle(page);
}
async function titleOf(plot) { return plot.evaluate(el => el._fullLayout.title.text); }
async function layoutCheck(page, plot, label) {
  await center(page, plot);
  await plot.hover({ position: { x: 10, y: 10 } }); await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3, await plot.elementHandle(), { timeout });
  const errors = await plot.evaluate(el => {
    const errors = [], frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) errors.push('plot overflow');
    for (const n of el.querySelectorAll('.annotation-text,.gtitle,.xtitle,.ytitle,.xtick text,.ytick text,.legend')) {
      const b = n.getBoundingClientRect();
      if (b.width && b.height && (b.left < frame.left - 3 || b.right > frame.right + 3 || b.top < frame.top - 3 || b.bottom > frame.bottom + 3))
        errors.push('clipped ' + n.textContent);
    }
    const overlap = (a, b) => a.width > 0 && b.width > 0 && a.left < b.right - 2 && a.right > b.left + 2 && a.top < b.bottom - 2 && a.bottom > b.top + 2;
    const legend = el.querySelector('.legend')?.getBoundingClientRect();
    const modebar = el.querySelector('.modebar');
    if (modebar && Number(getComputedStyle(modebar).opacity) > 0) {
      const title = el.querySelector('.gtitle');
      if (title && overlap(modebar.getBoundingClientRect(), title.getBoundingClientRect())) errors.push('modebar/title');
    }
    if (legend) for (const n of el.querySelectorAll('.annotation-text')) if (overlap(n.getBoundingClientRect(), legend)) errors.push('legend/annotation');
    for (const a of el.querySelectorAll('.xtitle,.ytitle,.xtick text,.ytick text'))
      for (const b of el.querySelectorAll('.legendtext')) if (overlap(a.getBoundingClientRect(), b.getBoundingClientRect())) errors.push('axis/legend');
    return errors;
  });
  check(errors.length === 0, label + ': ' + errors.join('; '));
}
async function negativeControl(plot) {
  // Move one displayed error point; the numeric check must reject it.
  const saved = await plot.evaluate(async el => {
    const index = el._fullData.findIndex(t => t.visible === true && t.meta?.role?.startsWith('market:'));
    const y = Array.from(el._fullData[index].y), bad = y.slice();
    bad[0] += 1.0;
    await Plotly.restyle(el, { y: [bad] }, [index]);
    return { index, y, role: el._fullData[index].meta.role };
  });
  let rejected = false;
  try {
    const rows = await traces(plot), title = await titleOf(plot);
    try { numeric(rows, 'asian_error', 'call', title); }
    catch (e) { check(e.message.includes('Displayed relative error'), 'Unrelated rejection: ' + e.message); rejected = true; }
    check(rejected, 'Moved error point passed');
  } finally {
    await plot.evaluate(async (el, s) => Plotly.restyle(el, { y: [s.y] }, [s.index]), saved);
  }
  numeric(await traces(plot), 'asian_error', 'call', await titleOf(plot));
  return { rejected, restored: true, mutation: saved.role + ' first point +1 percentage point' };
}
async function verifySurface(page, label) {
  if (label === 'portal') {
    const text = await page.locator('body').innerText();
    for (const phrase of ['今日は観測日に入らない', '満期給付であって現在価値ではない', '固定シード',
      '幾何平均はコール価格の下界', 'σ√T', '誤差は片側でない', '2観測日の行だけ'])
      check(text.includes(phrase), 'Portal domain ' + phrase);
  }
  const plots = {}, states = [], screenshots = [];
  for (const key of keys) plots[key] = await plotFor(page, key);
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    for (const key of keys) for (const state of scenarios[key]) {
      await center(page, plots[key]);
      await select(page, plots[key], state);
      await layoutCheck(page, plots[key], label + '/' + key + '/' + state + '/' + width);
      const observed = await traces(plots[key]);
      numeric(observed, key, state, await titleOf(plots[key]));
      states.push({ figure: key, scenario: state, width, numeric_checked: true, traces: observed.length });
    }
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), 'Page overflow');
    for (const key of keys) {
      await select(page, plots[key], scenarios[key][0]);
      await layoutCheck(page, plots[key], label + '/' + key + '/' + width);
      const file = relativeOut + label + '-' + key + '-' + width + '.png';
      await plots[key].screenshot({ path: path.join(root, file) }); screenshots.push(file);
    }
  }
  const negative_controls = [await negativeControl(plots.asian_error)];
  return { figures: keys, states, negative_controls, screenshots, layout_errors: 0,
    numeric_scope: 'Both widths, every menu state: payoff 8 algebraic pins, distribution M1 and the whole fitted density against an independently recomputed lognormal, observations 18 frozen rows plus an independently quadratured continuous price, errors 29 frozen relative errors. Monte Carlo references carry a standard error and are compared within 4 SE.' };
}
async function seasonedTable(section) {
  // The displayed K* table must be the contract the independent reference prices.
  const table = await section.evaluate(el => {
    const found = Array.from(el.querySelectorAll('table')).filter(node =>
      node.textContent.includes('K*') && node.textContent.includes('観測済み平均'));
    if (found.length !== 1) return { count: found.length };
    const header = Array.from(found[0].querySelectorAll('thead th')).map(n => n.textContent.trim());
    const rows = Array.from(found[0].querySelectorAll('tbody tr')).map(tr =>
      Array.from(tr.querySelectorAll('th,td')).map(n => n.textContent.trim()));
    return { count: 1, header, rows };
  });
  check(table.count === 1, 'Expected exactly one seasoned K* table, found ' + table.count);
  const column = name => {
    const index = table.header.findIndex(text => text.includes(name));
    check(index >= 0, 'Seasoned column ' + name + ' in ' + JSON.stringify(table.header));
    return index;
  };
  const columns = {
    average: column('観測済み平均'), shifted: column('K*'),
    certain: column('確実に行使'), price: column('call 価格'),
  };
  const pins = reference.seasoned.rows;
  const body = table.rows.filter(row => row.length >= table.header.length);
  check(body.length === pins.length, `Seasoned rows ${body.length} != ${pins.length}`);
  const checked = [];
  pins.forEach((pin, index) => {
    const row = body[index];
    const cell = key => Number(row[row.length - table.header.length + columns[key]]);
    close(cell('average'), pin.observed_average, 'Displayed observed average');
    close(cell('shifted'), pin.shifted_strike, 'Displayed K*', 5e-4);
    close(cell('price'), pin.price, 'Displayed seasoned price', 5e-5);
    const flag = row[row.length - table.header.length + columns.certain];
    check(flag.toLowerCase() === String(pin.certain_exercise),
      `Displayed exercise flag ${flag} for K*=${pin.shifted_strike}`);
    checked.push({ observed_average: pin.observed_average, shifted_strike: pin.shifted_strike,
      certain_exercise: pin.certain_exercise, price: pin.price });
  });
  check(checked.some(row => row.certain_exercise), 'The table must show the K*<0 branch');
  return { inputs: reference.seasoned.inputs, checked };
}

async function bookMath(page) {
  const heading = page.locator('h3').filter({ hasText: /4\.3 アジアン/ });
  check(await heading.count() === 1, 'Missing asian h3');
  const section = heading.locator('xpath=..');
  await page.waitForFunction(() => !!window.MathJax?.startup?.promise, null, { timeout });
  await page.evaluate(() => window.MathJax.startup.promise);
  const math = await section.evaluate(el => ({
    typeset: el.querySelectorAll('mjx-container').length,
    errors: el.querySelectorAll('mjx-merror,.MathJax_Error').length,
    headings: Array.from(el.querySelectorAll('h4')).map(n => n.textContent),
    text: el.textContent,
    rows: Array.from(el.querySelectorAll('tr')).map(n => n.textContent.replace(/\s/g, '')),
  }));
  check(math.typeset >= 15 && math.errors === 0, 'Asian math typesetting');
  for (let i = 1; i <= 6; i++) check(math.headings.some(h => h.includes('4.3.' + i)), 'Asian A0' + i);
  check(!math.text.includes('4.2 シャウト') && !math.text.includes('4.4 '), 'Own section boundaries');
  const over = (100 * record.approximation_error.largest_overprice.relative_error).toFixed(2);
  const under = (100 * record.approximation_error.largest_underprice.relative_error).toFixed(2);
  for (const phrase of ['52.59', '2,922.76', '23.54', '5.62', '6.00', '5.70', '5.63',
    '+' + over + '%', '−' + under.replace('-', '') + '%', 'Margrabe', '確実に行使', '恒等式'])
    check(math.text.includes(phrase), 'Teaching text ' + phrase);
  check(math.rows.some(r => r.includes('観測250') && r.includes('+' + over + '%')), 'Measured error table');
  check(math.rows.some(r => r.includes('観測12') && r.includes(under.replace('-', '−') + '%')), 'Measured error table');
  // The headline range covers only the rows priced above the threshold; say so on the page.
  const measured = record.approximation_error;
  for (const phrase of [String(measured.rows_measured), String(measured.rows_total), '可除特異点',
    '一般則ではありません', '上界'])
    check(math.text.includes(phrase), 'Teaching text ' + phrase);
  math.seasoned = await seasonedTable(section);
  delete math.text; delete math.rows; math.screenshots = [];
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    check(await section.evaluate(el => Array.from(el.querySelectorAll('div.math')).every(n => n.scrollWidth <= n.clientWidth + 3)),
      'Asian math overflow');
    const example = section.locator('h4').filter({ hasText: /4\.3\.6/ }).locator('xpath=..');
    const contentHeight = await example.evaluate(el =>
      el.querySelector('table').getBoundingClientRect().bottom - el.querySelector('h4').getBoundingClientRect().top);
    await page.setViewportSize({ width, height: Math.max(1050, Math.ceil(contentHeight) + 260) }); await settle(page);
    await example.locator('h4').first().evaluate(el => {
      document.activeElement?.blur();
      window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - 130, behavior: 'instant' });
    });
    await settle(page);
    const clip = await example.evaluate(el => {
      const a = el.querySelector('h4').getBoundingClientRect(), b = el.querySelector('table').getBoundingClientRect();
      const frame = el.getBoundingClientRect();
      return { x: frame.left, y: a.top, width: frame.width, height: b.bottom - a.top + 12 };
    });
    const box = await example.locator('table').first().boundingBox();
    check(box.y + box.height < page.viewportSize().height, 'Error table fully in viewport');
    const file = relativeOut + 'book-asian-domain-' + width + '.png';
    await page.screenshot({ path: path.join(root, file), clip }); math.screenshots.push(file);
  }
  return math;
}
(async () => {
  for (const [file, digest] of Object.entries(reference.source_sha256))
    check(hash(file) === digest, 'Stale independent pin source ' + file);
  check(Math.abs(normalCdf(0) - 0.5) < 1e-9, 'Normal CDF sanity');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN || undefined, args: ['--no-sandbox'] });
  result.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const label of ['portal', 'book']) {
      const page = await context.newPage(), errors = [], requests = [];
      page.on('pageerror', e => errors.push(e.message));
      if (label === 'portal') await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
      else page.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()); });
      await page.goto('file://' + path.join(root, label === 'portal' ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html'));
      const math = label === 'book' ? await bookMath(page) : undefined;
      result.pages[label] = { ...(await verifySurface(page, label)), math, external_network_blocked: label === 'portal', external_requests: requests, page_errors: errors };
      check(errors.length === 0, label + ' JS errors: ' + errors.join(';'));
      if (label === 'portal') check(requests.length === 0, 'Portal external requests');
      await page.close();
    }
    for (const file of ['hullkit/src/hullkit/_asian_lesson.py', 'hullkit/src/hullkit/exotics.py',
      'scripts/build_asian_browser_reference.py', 'scripts/build_asian_lesson_data.py',
      'scripts/build_asian_reference.py', relativeOut + 'lesson-data.json', relativeOut + 'prices.json',
      relativeOut + 'numerical-check.json', relativeOut + 'browser-reference.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/report_builder/render.py', 'report/assets/style.css',
      'book/_ext/book_runtime.py', 'book/_config.yml', 'scripts/verify_asian_lesson_browser.cjs'])
      result.source_sha256[file] = hash(file);
    const artifacts = ['report/site/exotics.html', 'report/site/assets/style.css', 'report/site/assets/plotly.min.js',
      'book/_build/html/notebooks/10_exotics.html'];
    for (const p of Object.values(result.pages)) artifacts.push(...p.screenshots, ...(p.math?.screenshots || []));
    for (const file of artifacts) result.artifact_sha256[file] = hash(file);
    result.status = 'PASS';
    console.log(JSON.stringify({ status: 'PASS', surfaces: 2, screenshots: Object.values(result.pages).reduce((n, p) => n + p.screenshots.length + (p.math?.screenshots.length || 0), 0), output: out }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { result.status = 'FAIL'; result.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(out, 'browser-m5b-check.json'), JSON.stringify(result, null, 2) + '\n'));
