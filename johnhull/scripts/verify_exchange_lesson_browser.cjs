// §26.14 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-14/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const record = JSON.parse(fs.readFileSync(path.join(out, 'numerical-check.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['exchange_payoff', 'exchange_correlation', 'exchange_rate', 'exchange_american'];
const scenarios = {
  exchange_payoff: ['exchange', 'better_of', 'worse_of'],
  exchange_correlation: reference.correlation.map(r => r.market),
  exchange_rate: reference.rate.map(r => r.market),
  exchange_american: reference.american.map(r => r.market),
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
function spreadVolatility(pin, rho) {
  return Math.sqrt(pin.volatility_u ** 2 + pin.volatility_v ** 2 - 2 * rho * pin.volatility_u * pin.volatility_v);
}
function margrabe(spotU, spotV, pin, rho) { // Eq. 26.5 rewritten here in JS.
  const forwardU = spotU * Math.exp(-pin.yield_u * pin.expiry);
  const forwardV = spotV * Math.exp(-pin.yield_v * pin.expiry);
  const scale = spreadVolatility(pin, rho) * Math.sqrt(pin.expiry);
  if (!(scale > 0)) return Math.max(forwardV - forwardU, 0);
  const d1 = (Math.log(forwardV / forwardU) + 0.5 * scale * scale) / scale;
  return forwardV * normalCdf(d1) - forwardU * normalCdf(d1 - scale);
}
async function traces(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true)
    .map(t => ({ meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []), name: t.name, mode: t.mode,
      line_color: t.line?.color })));
}
function trace(rows, role) {
  const found = rows.filter(t => t.meta?.role === role);
  check(found.length === 1, 'Expected unique trace ' + role);
  return found[0];
}

function numeric(rows, key, state, title) {
  check(rows.every(t => t.meta.scenario === state), 'Wrong visible scenario');
  const colors = rows.map(r => r.line_color).filter(Boolean);
  check(new Set(colors).size === colors.length, 'Two traces share a colour: ' + colors.join(','));
  if (key === 'exchange_payoff') {
    check(rows.length === 3 || rows.length === 4, 'Payoff trace count ' + rows.length);
    const pin = reference.payoff;
    const payoff = trace(rows, 'payoff');
    check(JSON.stringify(payoff.x) === JSON.stringify(pin.rows.map(r => r.terminal_v)), 'Payoff grid');
    payoff.y.forEach((value, i) => close(value, pin.rows[i][state], 'Displayed ' + state + ' payoff'));
    close(trace(rows, 'given').y[0], pin.terminal_u, 'Displayed U_T');
    trace(rows, 'received').y.forEach((value, i) => close(value, pin.rows[i].terminal_v, 'Displayed V_T'));
    if (state !== 'exchange') {
      // The decomposition markers must be the identity, recomputed here, not the same array.
      const drawn = trace(rows, 'decomposition');
      drawn.y.forEach((value, i) => {
        const row = pin.rows[i];
        const rebuilt = state === 'better_of' ? pin.terminal_u + row.exchange : row.terminal_v - row.exchange;
        close(value, rebuilt, 'Decomposition marker');
        close(payoff.y[i], rebuilt, 'Decomposition equals the payoff');
      });
    } else {
      check(!rows.some(r => r.meta.role === 'decomposition'), 'No decomposition on the plain contract');
      check(payoff.y.some(v => v === 0) && payoff.y.some(v => v > 0), 'The payoff must have its kink');
    }
  } else if (key === 'exchange_correlation') {
    check(rows.length === 3, 'Correlation trace count');
    const pin = reference.correlation.find(p => p.market === state);
    const prices = trace(rows, 'price'), volatility = trace(rows, 'volatility'), forward = trace(rows, 'forward');
    check(prices.x.length >= 30, 'Correlation grid too coarse');
    prices.x.forEach((rho, i) => {
      close(prices.y[i], margrabe(100, 100, pin, rho), 'Displayed price at rho=' + rho, 2e-5);
      close(volatility.y[i], 100 * spreadVolatility(pin, rho), 'Displayed sigma-hat at rho=' + rho, 1e-9);
    });
    for (let i = 1; i < prices.y.length; i++)
      check(prices.y[i] <= prices.y[i - 1] + 1e-12, 'Price must fall as rho rises');
    close(forward.y[0], pin.forward_spread, 'Displayed forward spread', 1e-9);
    check(Math.min(...prices.y) >= pin.forward_spread - 1e-9, 'Price below the forward spread');
    const shown = title.match(/価格は ([\d.]+) → ([\d.]+)/);
    check(!!shown, 'Correlation title format: ' + title);
    close(Number(shown[1]), pin.endpoints['-0.95'].price, 'Displayed left endpoint', 2e-4);
    close(Number(shown[2]), pin.endpoints['+0.95'].price, 'Displayed right endpoint', 2e-4);
  } else if (key === 'exchange_rate') {
    check(rows.length === 3, 'Rate trace count');
    const pin = reference.rate.find(p => p.market === state);
    const ref = trace(rows, 'reference'), restated = trace(rows, 'restated'), naive = trace(rows, 'naive');
    check(JSON.stringify(ref.x.map(v => Number((v / 100).toFixed(4)))) === JSON.stringify(pin.rates), 'Rate grid');
    check(Math.min(...ref.x) < 0, 'A negative rate must be on the axis');
    ref.y.forEach(value => close(value, pin.price, 'Displayed price at some rate', 2e-5));
    check(Math.max(...ref.y) - Math.min(...ref.y) < 1e-11, 'The price must not move with r');
    restated.y.forEach(value => close(value, pin.restated_price, 'Displayed restatement', 2e-5));
    // The comparison line must actually move, or the flat line proves nothing.
    naive.y.forEach((value, i) => close(value, pin.fixed_strike_misreading[i], 'Displayed misreading', 2e-5));
    check(Math.max(...naive.y) - Math.min(...naive.y) > 1, 'The misreading line must move with r');
    for (let i = 1; i < naive.y.length; i++) check(naive.y[i] >= naive.y[i - 1] - 1e-9, 'Misreading rises with r');
    const shown = title.match(/価格は ([\d.]+) のまま/);
    check(!!shown, 'Rate title format: ' + title);
    close(Number(shown[1]), pin.price, 'Displayed flat price', 2e-4);
  } else {
    check(rows.length === 5, 'American trace count');
    const pin = reference.american.find(p => p.market === state);
    const european = trace(rows, 'european'), american = trace(rows, 'american');
    const intrinsic = trace(rows, 'intrinsic'), premium = trace(rows, 'premium'), grid = trace(rows, 'grid');
    check(JSON.stringify(european.x) === JSON.stringify(pin.ratios), 'American grid');
    european.y.forEach((value, i) => {
      close(value, pin.european[i], 'Displayed European price', 2e-5);
      close(intrinsic.y[i], pin.intrinsic[i], 'Displayed intrinsic value', 1e-9);
      check(american.y[i] >= intrinsic.y[i] - 1e-6, 'American below intrinsic');
      // american - european = early exercise + grid residual, so the split must close.
      close(Math.abs((american.y[i] - value) - premium.y[i]), grid.y[i], 'Premium plus grid residual', 1e-9);
    });
    const maxPremium = Math.max(...premium.y), maxGrid = Math.max(...grid.y);
    if (pin.yield_v === 0) {
      check(maxPremium < 1e-9, 'Early exercise must be worthless at qV=0: ' + maxPremium);
      check(maxGrid > 1e-4 && maxGrid > 1e6 * maxPremium, 'The grid residual must dominate');
      check(title.includes('早期行使に価値なし'), 'Title must say so: ' + title);
      close(record.american.max_premium_without_yield, reference.record.max_premium_without_yield, 'Record pin');
      check(record.american.max_premium_without_yield < 1e-9, 'Recorded premium at qV=0');
    } else {
      check(maxPremium > 1, 'A yield on the received asset must buy early exercise');
      check(maxPremium > 1000 * maxGrid, 'Premium must dominate the grid residual');
      check(!title.includes('早期行使に価値なし'), 'Title must not deny the premium: ' + title);
      // Deep in the money with a yield, exercising now is optimal.
      const last = american.y.length - 1;
      close(american.y[last], intrinsic.y[last], 'Deep ITM American equals intrinsic', 1e-5);
    }
    const shown = title.match(/q_V = (\d+)%/);
    check(!!shown, 'American title format: ' + title);
    close(Number(shown[1]) / 100, pin.yield_v, 'Displayed qV', 1e-9);
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
  // Tilt the flat r-independence line; the numeric check must reject it.
  const saved = await plot.evaluate(async el => {
    const index = el._fullData.findIndex(t => t.visible === true && t.meta?.role === 'reference');
    const y = Array.from(el._fullData[index].y), bad = y.slice();
    bad[bad.length - 1] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [index]);
    return { index, y, state: el._fullData[index].meta.scenario };
  });
  let rejected = false;
  try {
    const rows = await traces(plot), title = await titleOf(plot);
    try { numeric(rows, 'exchange_rate', saved.state, title); }
    catch (e) {
      check(e.message.includes('must not move with r') || e.message.includes('Displayed price at some rate'),
        'Unrelated rejection: ' + e.message);
      rejected = true;
    }
    check(rejected, 'Tilted flat line passed');
  } finally {
    await plot.evaluate(async (el, s) => Plotly.restyle(el, { y: [s.y] }, [s.index]), saved);
  }
  numeric(await traces(plot), 'exchange_rate', saved.state, await titleOf(plot));
  return { rejected, restored: true, mutation: 'rate reference last point +0.5 currency units' };
}
async function verifySurface(page, label) {
  if (label === 'portal') {
    const text = await page.locator('body').innerText();
    for (const phrase of ['満期給付であって現在価値ではない', '行使価格が固定額でなく',
      '成長率の上昇と割引率の上昇が相殺', '早期行使に価値はない', '有限格子', 'σ̂'])
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
  const negative_controls = [await negativeControl(plots.exchange_rate)];
  return { figures: keys, states, negative_controls, screenshots, layout_errors: 0,
    numeric_scope: 'Both widths, every menu state: the payoff identity recomputed from max/min, 39 correlation points against equation 26.5 rewritten in JS, 7 rates against the flat price plus the ratio restatement and the moving misreading, and 17 moneyness points of the American figure with the early-exercise premium separated from the grid residual.' };
}
async function displayedTables(section) {
  // The two DataFrames in the notebook must price the contract the reference prices.
  const tables = await section.evaluate(el => Array.from(el.querySelectorAll('table')).map(node => ({
    header: Array.from(node.querySelectorAll('thead th')).map(n => n.textContent.trim()),
    rows: Array.from(node.querySelectorAll('tbody tr')).map(tr =>
      Array.from(tr.querySelectorAll('th,td')).map(n => n.textContent.trim())),
  })));
  const ratioTable = tables.filter(t => t.header.some(h => h.includes('V/U への読み替え')));
  check(ratioTable.length === 1, 'Expected one ratio table, found ' + ratioTable.length);
  const americanTable = tables.filter(t => t.header.some(h => h.includes('米国型')));
  check(americanTable.length === 1, 'Expected one American table, found ' + americanTable.length);
  const cellOf = (table, row, name) => {
    const index = table.header.findIndex(text => text.includes(name));
    check(index >= 0, 'Column ' + name + ' in ' + JSON.stringify(table.header));
    return row[row.length - table.header.length + index];
  };
  const checkedRatios = [];
  reference.notebook.ratio_table.forEach((pin, i) => {
    const row = ratioTable[0].rows[i];
    close(Number(cellOf(ratioTable[0], row, '相関ρ')), pin.correlation, 'Displayed rho');
    close(Number(cellOf(ratioTable[0], row, 'σ̂')), pin.spread_volatility, 'Displayed sigma-hat', 5e-5);
    close(Number(cellOf(ratioTable[0], row, '交換オプション')), pin.price, 'Displayed exchange price', 5e-5);
    close(Number(cellOf(ratioTable[0], row, 'V/U への読み替え')), pin.restated, 'Displayed restatement', 5e-5);
    checkedRatios.push({ correlation: pin.correlation, price: pin.price, restated: pin.restated });
  });
  check(checkedRatios.length === 4 && checkedRatios[0].price > checkedRatios[3].price,
    'The ratio table must show the price falling with rho');
  const checkedAmerican = [];
  reference.notebook.american_table.forEach((pin, i) => {
    const row = americanTable[0].rows[i];
    close(Number(cellOf(americanTable[0], row, 'V₀/U₀')), pin.value_ratio, 'Displayed ratio');
    close(Number(cellOf(americanTable[0], row, '欧州型')), pin.european, 'Displayed European price', 5e-5);
    const premium = Number(cellOf(americanTable[0], row, '早期行使の上乗せ'));
    const american = Number(cellOf(americanTable[0], row, '米国型'));
    close(american - Number(cellOf(americanTable[0], row, '欧州型')), premium, 'Displayed premium', 1e-4);
    if (pin.yield_v === 0) check(Math.abs(premium) < 6e-3, 'qV=0 premium must be a grid residual: ' + premium);
    else check(premium > 0.01, 'qV>0 must show a premium: ' + premium);
    checkedAmerican.push({ label: pin.label, value_ratio: pin.value_ratio, european: pin.european, premium });
  });
  return { ratio_table: checkedRatios, american_table: checkedAmerican };
}

async function bookMath(page) {
  const heading = page.locator('h3').filter({ hasText: /4\.4 交換オプション/ });
  check(await heading.count() === 1, 'Missing exchange h3');
  const section = heading.locator('xpath=..');
  await page.waitForFunction(() => !!window.MathJax?.startup?.promise, null, { timeout });
  await page.evaluate(() => window.MathJax.startup.promise);
  const math = await section.evaluate(el => ({
    typeset: el.querySelectorAll('mjx-container').length,
    errors: el.querySelectorAll('mjx-merror,.MathJax_Error').length,
    headings: Array.from(el.querySelectorAll('h4')).map(n => n.textContent),
    text: el.textContent,
    pre: Array.from(el.querySelectorAll('pre')).map(n => n.textContent),
  }));
  check(math.typeset >= 15 && math.errors === 0, 'Exchange math typesetting');
  for (let i = 1; i <= 6; i++) check(math.headings.some(h => h.includes('4.4.' + i)), 'Exchange E0' + i);
  check(!math.text.includes('4.3 アジアン') && !math.text.includes('4.5 レインボー'), 'Own section boundaries');
  for (const phrase of ['Rubinstein', '通貨の交換', '公開買付', '打ち消し合う', '行使価格 1.0',
    '早期行使', '格子効果', '例題がなく', '7.965567', '恒等式'])
    check(math.text.includes(phrase), 'Teaching text ' + phrase);
  // The r-independence number on the page must be the measured one, not a rounded claim.
  const spread = record.rate_independence.max_spread;
  check(math.text.includes('1.8×10⁻¹⁴'), 'Measured r spread on the page');
  check(spread < 2e-14 && spread > 1e-14, 'Recorded r spread does not round to 1.8e-14: ' + spread);
  // The decomposition residual quoted in the text must match the record.
  check(math.text.includes('8.5'), 'Decomposition residual on the page');
  check(reference.record.decomposition_max_residual < 1e-9, 'Recorded decomposition residual');
  // The printed console lines must agree with the independent decomposition.
  const printed = math.pre.join('\n');
  const pin = reference.notebook.decomposition;
  const better = printed.match(/better-of ([\d.]+) \+ worse-of ([\d.]+) = ([\d.]+)/);
  check(!!better, 'Missing the printed decomposition line: ' + printed.slice(0, 400));
  close(Number(better[1]), pin.better_of, 'Printed better-of', 5e-5);
  close(Number(better[2]), pin.worse_of, 'Printed worse-of', 5e-5);
  close(Number(better[3]), pin.forward_sum, 'Printed sum equals the forward sum', 5e-5);
  math.tables = await displayedTables(section);
  delete math.text; delete math.pre; math.screenshots = [];
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    check(await section.evaluate(el => Array.from(el.querySelectorAll('div.math')).every(n => n.scrollWidth <= n.clientWidth + 3)),
      'Exchange math overflow');
    const closing = section.locator('h4').filter({ hasText: /4\.4\.6/ }).locator('xpath=..');
    const contentHeight = await closing.evaluate(el => {
      const list = el.querySelector('ol') || el.querySelector('p');
      return list.getBoundingClientRect().bottom - el.querySelector('h4').getBoundingClientRect().top;
    });
    await page.setViewportSize({ width, height: Math.max(1050, Math.ceil(contentHeight) + 260) }); await settle(page);
    await closing.locator('h4').first().evaluate(el => {
      document.activeElement?.blur();
      window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - 130, behavior: 'instant' });
    });
    await settle(page);
    const clip = await closing.evaluate(el => {
      const a = el.querySelector('h4').getBoundingClientRect();
      const b = (el.querySelector('ol') || el.querySelector('p')).getBoundingClientRect();
      const frame = el.getBoundingClientRect();
      return { x: frame.left, y: a.top, width: frame.width, height: b.bottom - a.top + 12 };
    });
    const box = await closing.locator('ol').last().boundingBox();
    check(box.y + box.height < page.viewportSize().height, 'Closing list fully in viewport');
    const file = relativeOut + 'book-exchange-domain-' + width + '.png';
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
    for (const file of ['hullkit/src/hullkit/_exchange_lesson.py', 'hullkit/src/hullkit/exotics.py',
      'scripts/build_exchange_browser_reference.py', 'scripts/build_exchange_lesson_data.py',
      'scripts/build_exchange_reference.py', relativeOut + 'lesson-data.json', relativeOut + 'prices.json',
      relativeOut + 'numerical-check.json', relativeOut + 'browser-reference.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/report_builder/render.py', 'report/assets/style.css',
      'book/_ext/book_runtime.py', 'book/_config.yml', 'scripts/verify_exchange_lesson_browser.cjs'])
      result.source_sha256[file] = hash(file);
    const artifacts = ['report/site/exotics.html', 'report/site/assets/style.css', 'report/site/assets/plotly.min.js',
      'book/_build/html/notebooks/10_exotics.html'];
    for (const p of Object.values(result.pages)) artifacts.push(...p.screenshots, ...(p.math?.screenshots || []));
    for (const file of artifacts) result.artifact_sha256[file] = hash(file);
    result.status = 'PASS';
    console.log(JSON.stringify({ status: 'PASS', surfaces: 2, screenshots: Object.values(result.pages).reduce((n, p) => n + p.screenshots.length + (p.math?.screenshots.length || 0), 0), output: out }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { result.status = 'FAIL'; result.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(out, 'browser-m6b-check.json'), JSON.stringify(result, null, 2) + '\n'));
