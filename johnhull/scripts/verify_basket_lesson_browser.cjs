// §26.15 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-15/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['basket_payoff', 'basket_correlation', 'basket_comparison', 'basket_error'];
const scenarios = {
  basket_payoff: ['call', 'put'],
  basket_correlation: ['all', 'covariance-only', 'volatility-only'],
  basket_comparison: ['baseline-call', 'long-high-volatility-call', 'baseline-put'],
  basket_error: ['call', 'put'],
};

const result = { command: 'CHROMIUM_BIN=<existing runtime> PLAYWRIGHT_MODULE=<existing runtime> node scripts/verify_basket_lesson_browser.cjs', checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };
function check(ok, message) { if (!ok) throw new Error(message); }
function close(a, b, message, tol = 1e-8) { check(Number.isFinite(a) && Math.abs(a - b) <= tol, `${message}: ${a} != ${b}`); }
function hash(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }

async function traces(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true).map(t => ({
    meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []), name: t.name,
    customdata: t.customdata, yaxis: t.yaxis, error_y: t.error_y,
    pattern: t.marker?.pattern?.shape,
  })));
}
function trace(rows, role) {
  const found = rows.filter(t => t.meta?.role === role);
  check(found.length === 1, 'Unique role ' + role);
  return found[0];
}
function arrayClose(actual, expected, label, tol = 1e-8) {
  check(actual.length === expected.length, label + ' length');
  actual.forEach((v, i) => close(v, expected[i], label + '[' + i + ']', tol));
}
function exact(actual, expected, label) {
  check(JSON.stringify(actual) === JSON.stringify(expected), label + ': ' + JSON.stringify(actual));
}
function numeric(rows, key, state, title) {
  const roleSets = {
    basket_payoff: ['basket-terminal', 'payoff', 'strike'],
    basket_correlation: state === 'all' ? ['cross-covariance', 'matched-volatility']
      : state === 'covariance-only' ? ['cross-covariance'] : ['matched-volatility'],
    basket_comparison: ['approximation', 'independent-reference', 'mc-estimate'],
    basket_error: ['absolute-relative-gap-established', 'absolute-relative-gap-unresolved', 'four-se-relative-uncertainty'],
  };
  exact(rows.map(r => r.meta.role), roleSets[key], key + ' roles');
  check(rows.every(r => r.meta.scenario === state), 'Visible state ' + state);
  rows.forEach(r => check(r.yaxis === (r.meta.role === 'matched-volatility' ? 'y2' : 'y'), 'Axis allocation ' + r.meta.role));
  if (key === 'basket_payoff') {
    const pin = reference.payoff;
    rows.forEach(r => exact(r.x, pin.labels, 'Literal terminal labels'));
    arrayClose(trace(rows, 'basket-terminal').y, pin.basket, 'Basket terminal');
    arrayClose(trace(rows, 'payoff').y, pin[state], 'Displayed payoff');
    arrayClose(trace(rows, 'strike').y, pin.basket.map(() => pin.strike), 'Strike');
    exact(trace(rows, 'basket-terminal').customdata, pin.terminals, 'Terminal assets');
    check(title.includes(state === 'call' ? 'max(B_T−K, 0)' : 'max(K−B_T, 0)'), 'Payoff formula');
  } else if (key === 'basket_correlation') {
    rows.forEach(r => {
      arrayClose(r.x, reference.correlation.map(p => p.rho), 'Rho only');
      arrayClose(r.y, reference.correlation.map(p =>
        r.meta.role === 'cross-covariance' ? p.cross_covariance : p.sigma_percent), 'Moment/covariance');
    });
  } else if (key === 'basket_comparison') {
    const pins = reference.comparison[state];
    rows.forEach(r => arrayClose(r.x, pins.map(p => p.K), 'Strike grid'));
    arrayClose(trace(rows, 'approximation').y, pins.map(p => p.approximation), 'Approximation');
    arrayClose(trace(rows, 'independent-reference').y, pins.map(p => p.reference), 'Independent reference');
    const mc = trace(rows, 'mc-estimate');
    arrayClose(mc.y, pins.map(p => p.mc), 'MC estimate');
    check(mc.error_y.visible && mc.error_y.type === 'data', 'Visible MC uncertainty');
    arrayClose(mc.error_y.array, pins.map(p => p.four_se), 'MC four SE');
  } else {
    const pins = reference.error[state];
    for (const [role, established] of [['absolute-relative-gap-established', true], ['absolute-relative-gap-unresolved', false]]) {
      const actual = trace(rows, role), expected = pins.filter(p => p.sign_established === established);
      exact(actual.x, expected.map(p => p.market), 'Error market partition');
      arrayClose(actual.y, expected.map(p => p.gap_percent), 'Absolute relative gap');
    }
    const unresolved = trace(rows, 'absolute-relative-gap-unresolved');
    check(unresolved.pattern === '/', 'Unresolved bars must be hatched');
    check(unresolved.name.includes('符号未確定'), 'Unresolved label');
    const uncertainty = trace(rows, 'four-se-relative-uncertainty');
    exact(uncertainty.x, pins.map(p => p.market), 'Uncertainty markets');
    arrayClose(uncertainty.y, pins.map(p => p.four_se_percent), 'Relative four SE');
    const target = pins.find(p => p.market === 'three-diversified');
    check(target.reference_method === 'mc' && !target.sign_established && target.gap < target.four_se,
      'MC-only unresolved example');
    const shown = title.match(/\|gap\|=([\d.]+) < 4SE=([\d.]+)/);
    check(!!shown, 'Error title numeric statement');
    close(Number(shown[1]), target.gap, 'Title gap', 5.1e-8);
    close(Number(shown[2]), target.four_se, 'Title uncertainty', 5.1e-8);
    check(title.includes('符号未確定'), 'Title must qualify the sign');
    const counter = pins.find(p => p.market === 'baseline');
    check(counter.sign_established && counter.gap < counter.four_se
      && counter.reference_method === 'conditional_quadrature', 'Conditional sign inside MC bar');
  }
}
async function menuContract(plot, key) {
  const menu = await plot.evaluate(el => ({
    states: el.layout.updatemenus[0].buttons.map(b => b.args[1].meta.scenario),
    section: el.layout.meta.section,
    axes: {left: el.layout.yaxis.title.text, right: el.layout.yaxis2?.title.text,
      side: el.layout.yaxis2?.side, overlay: el.layout.yaxis2?.overlaying, order: el.layout.xaxis.categoryorder, categories: el.layout.xaxis.categoryarray},
  }));
  exact(menu.states, scenarios[key], key + ' exact menu states');
  check(menu.section === '26.15', 'Section metadata');
  if (key === 'basket_correlation') {
    check(menu.axes.left.includes('M₂') && menu.axes.right.includes('%'), 'Moment/volatility axis units');
    check(menu.axes.side === 'right' && menu.axes.overlay === 'y', 'Dual axes');
  }
  if (key === 'basket_error') {
    check(menu.axes.left.includes('絶対相対誤差'), 'Unsigned error axis');
    check(menu.axes.order === 'array', 'Explicit category order');
    exact(menu.axes.categories, ['baseline', 'long-high-volatility', 'three-diversified', 'three-high-volatility'], 'Fixed market axis');
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
  const index = await plot.evaluate((el, state) =>
    el.layout.updatemenus[0].buttons.findIndex(b => b.args[1].meta.scenario === state), state);
  check(index >= 0, 'Known exact menu state ' + state);
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').nth(index).click();
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
  const saved = await plot.evaluate(async el => {
    const index = el._fullData.findIndex(t => t.visible === true && t.meta?.role === 'approximation');
    const y = Array.from(el._fullData[index].y), bad = y.slice();
    bad[1] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [index]);
    return { index, y, state: el._fullData[index].meta.scenario };
  });
  let rejected = false, reason;
  try {
    try { numeric(await traces(plot), 'basket_comparison', saved.state, await titleOf(plot)); }
    catch (e) {
      check(e.message.includes('Approximation'), 'Unrelated mutation rejection: ' + e.message);
      rejected = true; reason = e.message;
    }
    check(rejected, 'Deliberate numeric mutation was accepted');
  } finally {
    await plot.evaluate(async (el, s) => Plotly.restyle(el, { y: [s.y] }, [s.index]), saved);
  }
  numeric(await traces(plot), 'basket_comparison', saved.state, await titleOf(plot));
  return { rejected, restored: true, reason, mutation: 'approximation at K=100 +0.5 currency' };
}
async function verifySurface(page, label) {
  const plots = {}, states = [], screenshots = [];
  const text = await page.locator('body').innerText();
  if (label === 'portal') {
    for (const phrase of ['M₁=ΣFᵢ', 'M₂=ΣᵢΣⱼFᵢFⱼ', 'Black', '近似', 'MC の誤差棒内でも符号が確定',
      'CBOT', '印刷されたバスケット価格例ではない', '非負', '正半定値', '66.8378%', '63行'])
      check(text.includes(phrase), 'Portal math/domain text: ' + phrase);
    close(Number(text.match(/最大絶対相対誤差([\d.]+)%/)[1]), reference.summary.max_relative_percent, 'Portal measured error', 5.1e-5);
  }
  for (const key of keys) { plots[key] = await plotFor(page, key); await menuContract(plots[key], key); }
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
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), label + ' page overflow');
    for (const key of keys) {
      await select(page, plots[key], scenarios[key][0]);
      await layoutCheck(page, plots[key], label + '/' + key + '/' + width);
      const file = relativeOut + label + '-' + key + '-' + width + '.png';
      await plots[key].screenshot({ path: path.join(root, file) }); screenshots.push(file);
    }
  }
  return { figures: keys, states, screenshots, layout_errors: 0,
    negative_controls: [await negativeControl(plots.basket_comparison)],
    math_presentation: label === 'portal' ? 'Unicode equations and domain text, no raw TeX renderer required' : 'MathJax, separately checked',
    numeric_scope: 'Both widths, every exact menu state: all terminal payoffs, covariance and matched volatility, Black/conditional/MC price points and four-SE error bars, absolute error markets and sign partition.' };
}
async function bookMath(page) {
  const heading = page.locator('h3').filter({ hasText: /4\.5 レインボー/ });
  check(await heading.count() === 1, 'Basket section heading');
  const section = heading.locator('xpath=..');
  await page.waitForFunction(() => !!window.MathJax?.startup?.promise, null, { timeout });
  await page.evaluate(() => window.MathJax.startup.promise);
  const info = await section.evaluate(el => ({
    typeset: el.querySelectorAll('mjx-container').length,
    errors: el.querySelectorAll('mjx-merror,.MathJax_Error').length,
    headings: Array.from(el.querySelectorAll('h4')).map(n => n.textContent),
    text: el.textContent,
    pre: Array.from(el.querySelectorAll('pre')).map(n => n.textContent).join('\n'),
    equations: Array.from(window.MathJax.startup.document.math).filter(m => el.contains(m.typesetRoot)).map(m => m.math),
  }));
  check(info.typeset >= 25 && info.errors === 0, 'Basket math typesetting ' + info.typeset + '/' + info.errors);
  for (let i = 1; i <= 6; i++) check(info.headings.some(h => h.includes('4.5.' + i)), 'Subsection ' + i);
  const equations = info.equations.map(s => s.replace(/\s/g, '')).join('\n');
  for (const formula of ['B_T=\\sum_iw_iS_i(T)', 'M_1=E[B_T]=\\sum_iF_i',
    'M_2=E[B_T^2]=\\sum_i\\sum_jF_iF_j', 'F_i=w_iS_i(0)e^{(r-q_i)T}',
    'C_{\\rmMM}=e^{-rT}[M_1N(d_1)-KN(d_2)]',
    'P_{\\rmMM}=e^{-rT}[KN(-d_2)-M_1N(-d_1)]',
    '3.0\\times10^{-10}', '100\\,|V_{\\rmMM}-V_{\\rmref}|'])
    check(equations.includes(formula), 'Typeset formula: ' + formula);
  for (const phrase of ['CBOT', 'レインボーの文脈', '印刷されたバスケット価格例ではありません',
    '数値例題がなく', '厳密', '近似', 'MC の誤差棒内でも符号が確定', '正半定値', '100万本', '2万本'])
    check(info.text.includes(phrase), 'Book teaching text ' + phrase);
  const example = info.pre.match(/M1 = ([\d.]+); M2 = ([\d.]+);\s*matched sigma = ([\d.]+)/);
  check(!!example, 'Displayed deterministic example');
  ['M1', 'M2', 'sigma'].forEach((name, i) => close(Number(example[i + 1]), reference.notebook[name], 'Printed ' + name, 5.1e-7));
  const prices = info.pre.match(/approx call = ([\d.]+); approx put = ([\d.]+)/);
  check(!!prices, 'Displayed call/put example');
  close(Number(prices[1]), reference.notebook.call, 'Printed call', 5.1e-7);
  close(Number(prices[2]), reference.notebook.put, 'Printed put', 5.1e-7);
  const parity = info.pre.match(/call - put = ([\d.]+);\s*discounted forward spread = ([\d.]+)/);
  check(!!parity, 'Displayed parity');
  close(Number(parity[1]), reference.notebook.parity, 'Printed parity', 5.1e-7);
  close(Number(parity[2]), reference.notebook.parity, 'Printed forward spread', 5.1e-7);
  check(info.text.includes(reference.summary.max_relative_percent.toFixed(4) + '%'), 'Measured relative error');
  check(info.text.includes(reference.summary.max_absolute.toFixed(6)), 'Measured absolute error');
  const screenshots = [];
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    check(await section.evaluate(el => Array.from(el.querySelectorAll('div.math')).every(n => n.scrollWidth <= n.clientWidth + 3)), 'Basket math overflow');
    const exampleSection = section.locator('h4').filter({ hasText: /4\.5\.2/ }).locator('xpath=..');
    const contentHeight = await exampleSection.evaluate(el => el.getBoundingClientRect().height);
    await page.setViewportSize({ width, height: Math.max(1050, Math.ceil(contentHeight) + 280) });
    await exampleSection.evaluate(el => {
      document.activeElement?.blur();
      window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - 140, behavior: 'instant' });
    });
    await settle(page);
    check(await exampleSection.evaluate(el => Array.from(el.querySelectorAll('pre')).every(
      n => n.scrollWidth <= n.clientWidth + 3)), 'Example code/output horizontal overflow');
    const clip = await exampleSection.boundingBox();
    check(clip.y >= 100 && clip.y + clip.height < page.viewportSize().height,
      'Entire formula/example must be within the viewport');
    const overlaps = await page.locator('a').filter({ hasText: 'Skip to main content' }).evaluateAll(
      (els, box) => els.some(n => { const b = n.getBoundingClientRect();
        return b.width > 0 && b.height > 0 && b.left < box.x + box.width
          && b.right > box.x && b.top < box.y + box.height && b.bottom > box.y; }), clip);
    check(!overlaps, 'Skip-link overlay must not cover formula/example');
    const file = relativeOut + 'book-basket-formula-example-' + width + '.png';
    await page.screenshot({ path: path.join(root, file), clip }); screenshots.push(file);
  }
  return { typeset: info.typeset, errors: info.errors, headings: info.headings,
    verified_equations: info.equations, example: reference.notebook, screenshots };
}
(async () => {
  for (const [file, digest] of Object.entries(reference.source_sha256))
    check(hash(file) === digest, 'Stale independent pin source ' + file);
  const counter = reference.deterministic_sign_inside_mc_bar;
  check(counter.gap < counter.four_se && counter.gap > counter.reference_uncertainty, 'Independent sign counterexample');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN || undefined, args: ['--no-sandbox'] });
  result.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const label of ['portal', 'book']) {
      const page = await context.newPage(), errors = [], requests = [], failed = [], responses = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('requestfailed', r => failed.push({ url: r.url(), failure: r.failure()?.errorText }));
      page.on('response', r => { if (r.status() >= 400) responses.push({ url: r.url(), status: r.status() }); });
      if (label === 'portal') await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
      else page.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()); });
      await page.goto('file://' + path.join(root, label === 'portal' ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html'));
      const math = label === 'book' ? await bookMath(page) : undefined;
      result.pages[label] = { ...(await verifySurface(page, label)), math, external_network_blocked: label === 'portal',
        external_requests: requests, page_errors: errors, failed_requests: failed, http_errors: responses };
      check(errors.length === 0, label + ' JS errors: ' + errors.join(';'));
      check(failed.length === 0 && responses.length === 0, label + ' network errors ' + JSON.stringify({failed, responses}));
      if (label === 'portal') check(requests.length === 0, 'Portal external requests');
      await page.close();
    }
    const sources = ['hullkit/src/hullkit/_basket_lesson.py', 'hullkit/src/hullkit/exotics.py',
      'scripts/build_basket_browser_reference.py', 'scripts/build_basket_lesson_data.py',
      'scripts/build_basket_reference.py', relativeOut + 'lesson-data.json', relativeOut + 'prices.json',
      relativeOut + 'numerical-check.json', relativeOut + 'browser-reference.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/report_builder/render.py', 'report/assets/style.css',
      'book/_ext/book_runtime.py', 'book/_config.yml', 'scripts/verify_basket_lesson_browser.cjs'];
    for (const file of sources) result.source_sha256[file] = hash(file);
    const artifacts = ['report/site/exotics.html', 'report/site/assets/style.css', 'report/site/assets/plotly.min.js',
      'book/_build/html/notebooks/10_exotics.html'];
    const screenshots = [];
    for (const p of Object.values(result.pages)) screenshots.push(...p.screenshots, ...(p.math?.screenshots || []));
    check(screenshots.length === 18, 'Exactly 18 screenshots');
    for (const file of [...artifacts, ...screenshots]) result.artifact_sha256[file] = hash(file);
    result.status = 'PASS';
    console.log(JSON.stringify({ status: 'PASS', surfaces: 2, state_checks: 40, screenshots: screenshots.length, output: out }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { result.status = 'FAIL'; result.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(out, 'browser-m7-check.json'), JSON.stringify(result, null, 2) + '\n'));
