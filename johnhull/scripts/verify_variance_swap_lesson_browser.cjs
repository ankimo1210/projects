// §26.16 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-16/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['varswap_payoff', 'varswap_strip', 'varswap_replication', 'volswap_convexity'];
const scenarios = {
  varswap_payoff: ['payoffs', 'difference'],
  varswap_strip: ['q', 'contribution'],
  varswap_replication: ['absolute', 'relative'],
  volswap_convexity: ['levels', 'error'],
};

const result = { command: 'CHROMIUM_BIN=<existing runtime> PLAYWRIGHT_MODULE=<existing runtime> node scripts/verify_variance_swap_lesson_browser.cjs', checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };
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
    varswap_payoff: state === 'payoffs' ? ['volatility-payoff', 'variance-payoff', 'strike'] : ['difference', 'strike'],
    varswap_strip: state === 'q' ? ['q-put', 'q-average', 'q-call', 'printed-q']
      : ['contribution-put', 'contribution-average', 'contribution-call'],
    varswap_replication: ['strip-error-narrow', 'strip-error-wide', 'strip-error-medium', 'zero'],
    volswap_convexity: state === 'levels' ? ['naive', 'exact', 'approximation', 'mc-estimate']
      : ['approximation-error', 'naive-error'],
  };
  exact(rows.map(r => r.meta.role), roleSets[key], key + ' roles');
  check(rows.every(r => r.meta.scenario === state), 'Visible state ' + state);
  if (key === 'varswap_payoff') {
    const pin = reference.payoff;
    const main = trace(rows, state === 'payoffs' ? 'volatility-payoff' : 'difference');
    arrayClose(main.x, pin.sigma, 'Realized volatility grid', 1e-12);
    if (state === 'payoffs') {
      arrayClose(trace(rows, 'volatility-payoff').y, pin.volatility, 'Volatility payoff');
      arrayClose(trace(rows, 'variance-payoff').y, pin.variance, 'Variance payoff');
      check(title.includes('L_var=L_vol/(2σ_K)=' + pin.variance_notional.toFixed(2)), 'Notional link in title');
    } else {
      arrayClose(trace(rows, 'difference').y, pin.difference, 'Payoff difference');
      check(Math.min(...trace(rows, 'difference').y) >= -1e-12, 'Convex gap is non-negative');
    }
    exact(trace(rows, 'strike').x, [0.23, 0.23], 'Strike marker');
  } else if (key === 'varswap_strip') {
    const pins = reference.strip.rows;
    if (state === 'q') {
      for (const kind of ['put', 'average', 'call']) {
        const actual = trace(rows, 'q-' + kind), expected = pins.filter(p => p.kind === kind);
        arrayClose(actual.x, expected.map(p => p.K), 'Strike partition ' + kind, 0);
        arrayClose(actual.y, expected.map(p => p.q), 'Q values ' + kind);
      }
      arrayClose(trace(rows, 'printed-q').y, pins.map(p => p.printed), 'Printed Q', 0);
      pins.forEach(p => check(Math.abs(p.q - p.printed) < 5e-3, 'Printed Q to 2 dp at ' + p.K));
      check(title.includes('S*=' + reference.strip.s_star.toFixed(0)), 'S* in title');
    } else {
      let total = 0;
      for (const kind of ['put', 'average', 'call']) {
        const actual = trace(rows, 'contribution-' + kind), expected = pins.filter(p => p.kind === kind);
        arrayClose(actual.y, expected.map(p => p.contribution), 'Contribution ' + kind);
        total += actual.y.reduce((a, b) => a + b, 0);
      }
      close(reference.strip.boundary + total, reference.strip.expected_variance, 'Strip sum + boundary = E(V)', 1e-14);
      check(title.includes(reference.strip.expected_variance.toFixed(6)), 'E(V) in title');
    }
  } else if (key === 'varswap_replication') {
    for (const name of ['narrow', 'medium', 'wide']) {
      const actual = trace(rows, 'strip-error-' + name), pin = reference.replication.families[name];
      arrayClose(actual.x, pin.delta_k, 'Grid spacing ' + name, 0);
      arrayClose(actual.y, pin[state], 'Strip error ' + name, state === 'absolute' ? 1e-15 : 1e-10);
    }
    const wide = reference.replication.families.wide.absolute;
    check(Math.abs(wide[0] / wide[1] - 4) < 0.05, 'Wide grid error quarters');
    const narrow = reference.replication.families.narrow.absolute;
    check(narrow[0] > 0 && narrow[narrow.length - 1] < 0, 'Narrow strip turns negative');
  } else {
    const pin = reference.convexity;
    if (state === 'levels') {
      for (const role of ['naive', 'exact', 'approximation']) {
        const actual = trace(rows, role);
        arrayClose(actual.x, pin.xi, 'xi grid', 0);
        arrayClose(actual.y, pin[role], 'Level ' + role, 1e-12);
      }
      const mc = trace(rows, 'mc-estimate');
      arrayClose(mc.x, pin.mc_xi, 'MC xi', 0);
      arrayClose(mc.y, pin.mc, 'MC estimate', 1e-12);
      check(mc.error_y.visible && mc.error_y.type === 'data', 'Visible MC uncertainty');
      arrayClose(mc.error_y.array, pin.mc_four_se, 'MC four SE', 1e-12);
      pin.mc_xi.forEach((xi, i) => {
        const j = pin.xi.indexOf(xi);
        check(Math.abs(pin.mc[i] - pin.exact[j]) < pin.mc_four_se[i], 'Exact within MC 4SE at xi=' + xi);
      });
    } else {
      arrayClose(trace(rows, 'approximation-error').y, pin.approximation_error, 'Approximation error', 1e-12);
      arrayClose(trace(rows, 'naive-error').y, pin.naive_error, 'Naive error', 1e-12);
      check(pin.approximation_error.every(v => v < 0), 'Approximation below exact in this market');
    }
  }
}
async function menuContract(plot, key) {
  const menu = await plot.evaluate(el => ({
    states: el.layout.updatemenus[0].buttons.map(b => b.args[1].meta.scenario),
    section: el.layout.meta.section,
    xtype: el._fullLayout.xaxis.type,
    ytitle: el.layout.yaxis.title.text,
  }));
  exact(menu.states, scenarios[key], key + ' exact menu states');
  check(menu.section === '26.16', 'Section metadata');
  if (key === 'varswap_replication') check(menu.xtype === 'log', 'Log grid-spacing axis');
  if (key === 'varswap_payoff') check(menu.ytitle.includes('$ millions'), 'Payoff units');
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
  await select(plot.page(), plot, 'levels');
  const saved = await plot.evaluate(async el => {
    const index = el._fullData.findIndex(t => t.visible === true && t.meta?.role === 'approximation');
    const y = Array.from(el._fullData[index].y), bad = y.slice();
    bad[5] += 0.5;
    await Plotly.restyle(el, { y: [bad] }, [index]);
    return { index, y, state: el._fullData[index].meta.scenario };
  });
  let rejected = false, reason;
  try {
    try { numeric(await traces(plot), 'volswap_convexity', saved.state, await titleOf(plot)); }
    catch (e) {
      check(e.message.includes('Level approximation'), 'Unrelated mutation rejection: ' + e.message);
      rejected = true; reason = e.message;
    }
    check(rejected, 'Deliberate numeric mutation was accepted');
  } finally {
    await plot.evaluate(async (el, s) => Plotly.restyle(el, { y: [s.y] }, [s.index]), saved);
  }
  numeric(await traces(plot), 'volswap_convexity', saved.state, await titleOf(plot));
  return { rejected, restored: true, reason, mutation: 'eq. 26.9 level at xi=0.6 +0.5 percentage points' };
}
async function verifySurface(page, label) {
  const plots = {}, states = [], screenshots = [];
  const text = await page.locator('body').innerText();
  if (label === 'portal') {
    for (const phrase of ['L_var=L_vol/(2σ_K)', 'Example 26.4', 'E(V)=0.0621', '1.69（$m）', '0.2484・1.82（$m）',
      'ξ⁴', '1.5e-12', '分散の分散', '翼の欠落'])
      check(text.includes(phrase), 'Portal math/domain text: ' + phrase);
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
    negative_controls: [await negativeControl(plots.volswap_convexity)],
    math_presentation: label === 'portal' ? 'Unicode equations and domain text, no raw TeX renderer required' : 'MathJax, separately checked',
    numeric_scope: 'Both widths, every exact menu state: payoff grid and notional link, Example 26.4 Q/printed Q/contributions and their sum, strip errors per range and spacing, exact/approximate/naive E(sigma) with MC four-SE bars and errors.' };
}
async function bookMath(page) {
  const heading = page.locator('h3').filter({ hasText: /4\.6 ボラティリティ/ });
  check(await heading.count() === 1, 'Variance-swap section heading');
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
  check(info.typeset >= 25 && info.errors === 0, 'Variance-swap math typesetting ' + info.typeset + '/' + info.errors);
  for (let i = 1; i <= 6; i++) check(info.headings.some(h => h.includes('4.6.' + i)), 'Subsection ' + i);
  const equations = info.equations.map(s => s.replace(/\s/g, '')).join('\n');
  for (const formula of ['\\bar\\sigma=\\sqrt{\\frac{252}{n-2}\\sum_{i=1}^{n-1}',
    'L_{\\rmvol}(\\bar\\sigma-\\sigma_K)', 'L_{\\rmvar}(\\barV-V_K)',
    'L_{\\rmvar}=L_{\\rmvol}/(2\\sigma_K)',
    '\\hatE(\\barV)=\\frac2T\\ln\\frac{F_0}{S^*}-\\frac2T\\left(\\frac{F_0}{S^*}-1\\right)',
    '\\approx\\sum_{i=1}^n\\frac{\\DeltaK_i}{K_i^2}e^{rT}Q(K_i)',
    '\\hatE(\\bar\\sigma)\\approx\\sqrt{\\hatE(\\barV)}\\left\\{1-\\frac18\\frac{\\operatorname{var}(\\barV)}{\\hatE(\\barV)^2}\\right\\}',
    '\\hatE(\\barV)T=-\\left(\\frac{F_0}{S^*}-1\\right)^2'])
    check(equations.includes(formula), 'Typeset formula: ' + formula);
  for (const phrase of ['Example 26.4', 'Example 26.5', 'Technical Note 22', 'CBOE の規則の細部',
    'ジャンプ', '+1.6%', '10万本', '1.08SE', '翼の欠落', '分散の分散'])
    check(info.text.includes(phrase), 'Book teaching text ' + phrase);
  const nb = reference.notebook;
  const realized = info.pre.match(/（n−2）= ([\d.]+)[\s\S]*?（n−1）= ([\d.]+)[\s\S]*?L_var = ([\d.]+)/);
  check(!!realized, 'Displayed realized-variance example');
  close(Number(realized[1]), nb.realized_n2, 'Printed n-2 variance', 5.1e-7);
  close(Number(realized[2]), nb.realized_n1, 'Printed n-1 variance', 5.1e-7);
  close(Number(realized[3]), nb.variance_notional, 'Printed variance notional', 5.1e-5);
  const ex4 = info.pre.match(/E\(V\) = ([\d.]+)（原典 0\.0621）; 価値 = ([\d.]+)/);
  check(!!ex4, 'Displayed Example 26.4');
  close(Number(ex4[1]), nb.example_26_4_expected_variance, 'Printed Example 26.4 E(V)', 5.1e-7);
  close(Number(ex4[2]), nb.example_26_4_value, 'Printed Example 26.4 value', 5.1e-5);
  const ex5 = info.pre.match(/E\(σ\) = ([\d.]+)（原典 0\.2484）; √E\(V\) = ([\d.]+)[\s\S]*?価値 = ([\d.]+)（原典 1\.82/);
  check(!!ex5, 'Displayed Example 26.5');
  close(Number(ex5[1]), nb.example_26_5_expected_volatility, 'Printed Example 26.5 E(sigma)', 5.1e-7);
  close(Number(ex5[2]), nb.naive_volatility, 'Printed sqrt E(V)', 5.1e-7);
  close(Number(ex5[3]), nb.example_26_5_value, 'Printed Example 26.5 value', 5.1e-5);
  const vix = info.pre.match(/式26\.6: E\(V\)T = ([\d.]+); 式26\.10: ([\d.]+)/);
  check(!!vix, 'Displayed VIX truncation');
  close(Number(vix[1]), nb.cumulative_26_6, 'Printed eq. 26.6 cumulative variance', 5.1e-8);
  close(Number(vix[2]), nb.cumulative_26_10, 'Printed eq. 26.10 cumulative variance', 5.1e-8);
  const screenshots = [];
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    check(await section.evaluate(el => Array.from(el.querySelectorAll('div.math')).every(n => n.scrollWidth <= n.clientWidth + 3)), 'Variance-swap math overflow');
    const exampleSection = section.locator('h4').filter({ hasText: /4\.6\.4/ }).locator('xpath=..');
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
    const file = relativeOut + 'book-volswap-formula-example-' + width + '.png';
    await page.screenshot({ path: path.join(root, file), clip }); screenshots.push(file);
  }
  return { typeset: info.typeset, errors: info.errors, headings: info.headings,
    verified_equations: info.equations, example: reference.notebook, screenshots };
}
(async () => {
  for (const [file, digest] of Object.entries(reference.source_sha256))
    check(hash(file) === digest, 'Stale independent pin source ' + file);
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
    const sources = ['hullkit/src/hullkit/_variance_swap_lesson.py', 'hullkit/src/hullkit/variance_swaps.py',
      'scripts/build_variance_swap_browser_reference.py', 'scripts/build_variance_swap_lesson_data.py',
      'scripts/build_variance_swap_reference.py', relativeOut + 'lesson-data.json', relativeOut + 'reference.json',
      relativeOut + 'numerical-check.json', relativeOut + 'browser-reference.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py', 'report/report_builder/render.py', 'report/assets/style.css',
      'book/_ext/book_runtime.py', 'book/_config.yml', 'scripts/verify_variance_swap_lesson_browser.cjs'];
    for (const file of sources) result.source_sha256[file] = hash(file);
    const artifacts = ['report/site/exotics.html', 'report/site/assets/style.css', 'report/site/assets/plotly.min.js',
      'book/_build/html/notebooks/10_exotics.html'];
    const screenshots = [];
    for (const p of Object.values(result.pages)) screenshots.push(...p.screenshots, ...(p.math?.screenshots || []));
    check(screenshots.length === 18, 'Exactly 18 screenshots');
    for (const file of [...artifacts, ...screenshots]) result.artifact_sha256[file] = hash(file);
    result.status = 'PASS';
    console.log(JSON.stringify({ status: 'PASS', surfaces: 2, state_checks: 32, screenshots: screenshots.length, output: out }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { result.status = 'FAIL'; result.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(out, 'browser-m8-check.json'), JSON.stringify(result, null, 2) + '\n'));
