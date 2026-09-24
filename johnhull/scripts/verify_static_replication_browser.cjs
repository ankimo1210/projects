// Hull §26.17: inspect the rendered Book and portal with the existing Chromium runtime.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'docs/validation/section-26-17');
const reference = JSON.parse(fs.readFileSync(path.join(outDir, 'reference.json'), 'utf8'));
const keys = ['static_boundary', 'static_ladder', 'static_boundary_error', 'static_convergence'];
const result = { checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };

function check(condition, message) { if (!condition) throw new Error(message); }
function close(a, b, label, tolerance = 1e-8) {
  check(Number.isFinite(a) && Math.abs(a - b) <= tolerance, `${label}: ${a} != ${b}`);
}
function arrayClose(actual, expected, label, tolerance = 1e-8) {
  check(actual.length === expected.length, `${label}: length ${actual.length} != ${expected.length}`);
  actual.forEach((value, index) => close(Number(value), Number(expected[index]), `${label}[${index}]`, tolerance));
}
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }

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
    .map(t => ({ x: Array.from(t.x || []), y: Array.from(t.y || []), name: t.name })));
}
async function numeric(plot, key, state) {
  const rows = await visible(plot);
  check(await plot.evaluate(el => el.layout.meta.section) === '26.17', `${key}: section metadata`);
  if (key === 'static_boundary') {
    check(rows.length === 4, 'boundary traces');
    arrayClose(rows[0].x, [0, reference.market.expiry], 'boundary times');
    arrayClose(rows[0].y, [reference.market.barrier, reference.market.barrier], 'barrier');
    arrayClose(rows[2].x, reference.ladders['3'].boundary_nodes.slice().sort((a, b) => a - b), 'three matching nodes');
    close(rows[3].y[0], reference.market.spot, 'initial spot');
  } else if (key === 'static_ladder') {
    check(rows.length === 1, 'ladder trace');
    arrayClose(rows[0].y, reference.ladders['3'].leg_values, 'Table 26.1 legs');
    close(rows[0].y.reduce((a, b) => a + b, 0), reference.ladders['3'].initial_value, 'ladder sum');
  } else if (key === 'static_boundary_error') {
    check(rows.length === 1 && rows[0].name === `${state}点`, `error state ${state}`);
    const curve = reference.ladders[state].boundary_curve;
    arrayClose(rows[0].x, curve.map(p => p.time), `${state} curve time`);
    arrayClose(rows[0].y, curve.map(p => p.value), `${state} curve value`, 2e-12);
  } else {
    check(rows.length === 2, 'convergence traces');
    arrayClose(rows[0].x, [3, 18, 100], 'convergence nodes');
    arrayClose(rows[0].y, [3, 18, 100].map(n => reference.ladders[n].initial_value), 'convergence values');
    arrayClose(rows[1].y, Array(3).fill(reference.analytic_barrier_price), 'absorbed-density price');
  }
}
async function select(page, plot, state) {
  const buttons = await plot.evaluate(el => el.layout.updatemenus[0].buttons.map(b => b.label));
  check(JSON.stringify(buttons) === JSON.stringify(['3点', '18点', '100点']), 'exact three menu states');
  const index = buttons.indexOf(`${state}点`);
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').nth(index).click();
  await page.waitForFunction(({ id, state }) => {
    const el = document.getElementById(id);
    return el._fullData.filter(t => t.visible === true).length === 1
      && el._fullData.find(t => t.visible === true).name === `${state}点`;
  }, { id: await plot.getAttribute('id'), state });
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
async function layout(plot, page, label) {
  await center(page, plot);
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3,
    await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth + 3) return 'plot overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text')) {
      const box = node.getBoundingClientRect();
      if (box.width && box.height && (box.left < frame.left - 3 || box.right > frame.right + 3
        || box.top < frame.top - 3 || box.bottom > frame.bottom + 3)) return `clipped ${node.textContent}`;
    }
    return null;
  });
  check(!issue, `${label}: ${issue}`);
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3), `${label}: page overflow`);
}
async function inspect(page, label) {
  const plots = {}, states = [], screenshots = [];
  for (const key of keys) plots[key] = await plotFor(page, key);
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 }); await settle(page);
    if (label === 'book') {
      const lesson = page.locator('h3').filter({ hasText: /4\.7 静的オプション複製/ }).locator('xpath=..');
      check(await lesson.count() === 1, 'unique Book §4.7 lesson');
      check(await lesson.evaluate(el => Array.from(el.querySelectorAll('div.math'))
        .every(node => node.scrollWidth <= node.clientWidth + 3)), `Book math overflow at ${width}`);
    }
    for (const key of keys) {
      for (const state of key === 'static_boundary_error' ? ['3', '18', '100'] : ['default']) {
        if (key === 'static_boundary_error') await select(page, plots[key], state);
        await numeric(plots[key], key, state);
        await layout(plots[key], page, `${label}/${key}/${state}/${width}`);
        states.push({ figure: key, state, width, numeric_checked: true });
      }
      if (key === 'static_boundary_error') await select(page, plots[key], '3');
      await center(page, plots[key]);
      const file = `docs/validation/section-26-17/${label}-${key}-${width}.png`;
      await plots[key].screenshot({ path: path.join(root, file) }); screenshots.push(file);
    }
  }
  const mutation = await plots.static_convergence.evaluate(async el => {
    const original = Array.from(el.data[0].y);
    const bad = original.slice(); bad[1] += 0.01;
    await Plotly.restyle(el, { y: [bad] }, [0]);
    return original;
  });
  let rejected = false;
  try { await numeric(plots.static_convergence, 'static_convergence', 'default'); }
  catch (error) { rejected = error.message.includes('convergence values'); }
  finally { await plots.static_convergence.evaluate((el, y) => Plotly.restyle(el, { y: [y] }, [0]), mutation); }
  check(rejected, `${label}: altered convergence value was accepted`);
  await numeric(plots.static_convergence, 'static_convergence', 'default');
  return { states, screenshots, numeric_mutation_rejected: rejected, layout_errors: 0 };
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
  result.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    for (const label of ['portal', 'book']) {
      const page = await context.newPage(), errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      if (label === 'portal') await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
      await page.goto('file://' + path.join(root, label === 'portal'
        ? 'report/site/exotics.html' : 'book/_build/html/notebooks/10_exotics.html'));
      if (label === 'book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math = await page.evaluate(() => ({ typeset: document.querySelectorAll('mjx-container').length,
          errors: document.querySelectorAll('mjx-merror,.MathJax_Error').length }));
        check(math.typeset > 0 && math.errors === 0, 'Book MathJax');
        const text = await page.locator('body').innerText();
        for (const phrase of ['4.7.1', '4.7.6', '0.730293', '0.377569', '0.324861', '0.313571'])
          check(text.includes(phrase), `Book lesson text: ${phrase}`);
        for (let index = 1; index <= 6; index++)
          check(await page.locator('h4').filter({ hasText: `4.7.${index}` }).count() === 1,
            `Book subsection 4.7.${index}`);
        const lesson = page.locator('h3').filter({ hasText: /4\.7 静的オプション複製/ }).locator('xpath=..');
        const displayed = await lesson.evaluate(el => ({ math: el.querySelectorAll('mjx-container').length,
          output: Array.from(el.querySelectorAll('pre')).map(node => node.innerText).join('\n') }));
        check(displayed.math > 5, 'Book §4.7 math rendered');
        check(displayed.output.includes('合計=0.730293') && displayed.output.includes('吸収境界の独立積分: 0.313571'),
          'Book §4.7 numerical outputs rendered');
        result.book_math = math;
      }
      result.pages[label] = { ...(await inspect(page, label)), page_errors: errors, external_requests: requests };
      check(errors.length === 0 && requests.length === 0, `${label}: JS or external requests`);
      await page.close();
    }
    for (const file of ['hullkit/src/hullkit/static_replication.py', 'hullkit/src/hullkit/_static_replication_lesson.py',
      'scripts/build_static_replication_reference.py', 'scripts/verify_static_replication_browser.cjs',
      'docs/validation/section-26-17/reference.json', 'docs/validation/section-26-17/numerical-check.json',
      'volumes/10_exotics_martingales/build_exotics_notebook.py', 'volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py']) result.source_sha256[file] = sha(file);
    for (const file of ['report/site/exotics.html', 'book/_build/html/notebooks/10_exotics.html',
      ...Object.values(result.pages).flatMap(page => page.screenshots)]) result.artifact_sha256[file] = sha(file);
    result.status = 'PASS';
    result.state_checks = Object.values(result.pages).reduce((n, page) => n + page.states.length, 0);
    console.log(JSON.stringify({ status: result.status, state_checks: result.state_checks, screenshots: 16 }));
  } finally { await browser.close(); }
})().catch(error => { result.status = 'FAIL'; result.error = error.message; console.error(error.stack); process.exitCode = 1; })
  .finally(() => fs.writeFileSync(path.join(outDir, 'browser-check.json'), JSON.stringify(result, null, 2) + '\n'));
