'use strict';

// No packages are installed. Pass an existing playwright-core and Chromium.
// node tools/browser_qa.cjs --module /existing/playwright-core --browser /existing/chrome
// Options also accept MATH_QA_MODULE, MATH_QA_BROWSER, MATH_QA_OUTPUT, MATH_QA_SITE.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');

function permittedPage(raw, known) {
  if (!raw.startsWith('/') || raw.startsWith('//')) return null;
  const name = raw.split('?')[0].slice(1);
  return /^[a-z0-9-]+\.html$/.test(name) && known.has(name) ? name : null;
}

function selfTest() {
  const known = new Set(['index.html', 'limits.html']);
  assert.equal(permittedPage('/index.html', known), 'index.html');
  assert.equal(permittedPage('/limits.html?theme=dark', known), 'limits.html');
  for (const value of ['/../README.md', '/%2e%2e/README.md', '/other.html', '//outside.test/index.html', '/assets/style.css']) {
    assert.equal(permittedPage(value, known), null);
  }
  console.log('Browser QA self-test passed.');
}

function options() {
  const values = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i];
    if (!['--module', '--browser', '--output', '--site'].includes(key) || !process.argv[i + 1]) {
      throw new Error('Use --module PATH --browser PATH [--output DIRECTORY] [--site DIRECTORY].');
    }
    values[key.slice(2)] = process.argv[i + 1];
  }
  return {
    module: values.module || process.env.MATH_QA_MODULE,
    browser: values.browser || process.env.MATH_QA_BROWSER,
    output: path.resolve(values.output || process.env.MATH_QA_OUTPUT || '/home/kazumasa/projects/_data/math-foundations/figure-messages-2026-11-08'),
    site: path.resolve(values.site || process.env.MATH_QA_SITE || path.join(__dirname, '../site')),
  };
}

const digest = text => crypto.createHash('sha256').update(text).digest('hex');
const mathScrollHintText = '長い数式は、式の枠内を左右にスクロールして読めます。';
const displayPath = value => process.platform === 'linux' && value.startsWith('/home/')
  ? '\\\\wsl.localhost\\Ubuntu' + value.replaceAll('/', '\\') : value;
const errorText = error => String(error.stack || error).replaceAll('/home/kazumasa/projects/', '\\\\wsl.localhost\\Ubuntu\\home\\kazumasa\\projects\\');

async function main(config) {
  if (!config.module || !config.browser) throw new Error('Existing --module and --browser paths are required.');
  const { chromium } = require(path.resolve(config.module));
  const catalog = JSON.parse(await fs.readFile(path.join(__dirname, '../catalog.json'), 'utf8'));
  const known = new Set(['index.html', ...catalog.chapters.map(chapter => chapter.slug + '.html')]);
  assert.equal(known.size, catalog.chapters.length + 1, 'Chapter slugs must be unique.');
  assert.equal(catalog.chapters.filter(chapter => chapter.book === 'discrete').length, 10, 'The discrete book has ten chapters.');
  assert.equal(catalog.chapters.filter(chapter => chapter.book === 'complex').length, 10, 'The complex book has ten chapters.');
  for (const book of ['vector','numerical','optimization','linear-core']) assert.equal(catalog.chapters.filter(chapter => chapter.book === book).length, 10, book + ' has ten chapters.');
  const expectedStates = known.size * 6;
  const expectedLabs = catalog.chapters.filter(chapter => chapter.lab).length;
  const fragments = await Promise.all(catalog.chapters.map(chapter => fs.readFile(path.join(__dirname, '../chapters', chapter.slug + '.html'), 'utf8')));
  const expectedFigures = fragments.reduce((sum, fragment) => sum + (fragment.match(/<figure\b[^>]*class="concept-figure"/g) || []).length, 0);
  const expectedTables = fragments.reduce((sum, fragment) => sum + (fragment.match(/<table\b[^>]*class="concept-table"/g) || []).length, 0);
  const pages = new Map(await Promise.all([...known].map(async name => [name, await fs.readFile(path.join(config.site, name))])));
  await fs.mkdir(config.output, { recursive: true });
  const report = {
    startedAt: new Date().toISOString(), status: 'running', platform: process.platform,
    scope: 'Linux headless Chromium, locally served generated HTML; no Windows browser or human trial reading',
    inputs: { browser: config.browser, module: config.module, site: config.site,
      pages: Object.fromEntries([...pages].map(([name, bytes]) => [name, digest(bytes)])) },
    checks: 0, failures: [], candidates: [], harnessErrors: [], console: [], pageErrors: [],
    requestFailures: [], httpErrors: [], blockedRequests: [], states: [], interactions: [],
    noJavaScript: [], screenshots: [], conceptScreenshots: [], limitations: [
      'MathML QA checks native support and nonzero layout boxes, not mathematical semantic correctness.',
      'SVG text bounds are candidates for visual review; non-text shapes may be intentionally clipped.',
      'All HTML bytes are snapshotted at server startup; source/build consistency is identified by page hashes.',
    ],
  };
  function check(ok, code, detail, where = {}) {
    report.checks++;
    if (!ok) report.failures.push({ code, detail, ...where });
    return !!ok;
  }
  let phase = 'startup', current = {}, browser, server;
  const repeated = new Map();
  async function section(label, task) {
    phase = label;
    try { await task(); }
    catch (error) {
      const message = String(error.message || error);
      const key = label + ':' + message.split('\n')[0];
      repeated.set(key, (repeated.get(key) || 0) + 1);
      report.harnessErrors.push({ phase, ...current, message: errorText(error) });
      if (repeated.get(key) >= 3) throw new Error('Three repeated harness failures: ' + key);
    }
  }
  try {
    server = http.createServer((request, response) => {
      const name = permittedPage(request.url, known);
      if (!['GET', 'HEAD'].includes(request.method) || !name) {
        report.httpErrors.push({ phase, ...current, url: request.url, status: 404, source: 'localhost-server' });
        response.writeHead(404, { 'Content-Type': 'text/plain' }); response.end('Not found'); return;
      }
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
        'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'" });
      response.end(request.method === 'HEAD' ? undefined : pages.get(name));
    });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    const origin = 'http://127.0.0.1:' + server.address().port;
    report.origin = origin;
    browser = await chromium.launch({ executablePath: config.browser, headless: true,
      args: ['--no-sandbox', '--disable-background-networking', '--disable-component-update', '--disable-domain-reliability',
        '--disable-sync', '--no-first-run', '--safebrowsing-disable-auto-update', '--metrics-recording-only',
        '--disable-features=MediaRouter,OptimizationHints,AutofillServerCommunication'] });
    report.browserVersion = browser.version();
    async function context(settings) {
      const result = await browser.newContext(settings);
      await result.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin === origin) await route.continue();
        else { report.blockedRequests.push({ phase, ...current, url: url.href }); await route.abort('blockedbyclient'); }
      });
      result.on('page', page => {
        page.on('console', event => report.console.push({ phase, ...current, type: event.type(), text: event.text(), location: event.location() }));
        page.on('pageerror', error => report.pageErrors.push({ phase, ...current, message: String(error) }));
        page.on('requestfailed', request => report.requestFailures.push({ phase, ...current, url: request.url(), failure: request.failure(), resourceType: request.resourceType() }));
        page.on('response', response => { if (response.status() >= 400) report.httpErrors.push({ phase, ...current, url: response.url(), status: response.status(), source: 'playwright-response' }); });
      });
      return result;
    }
    const ctx = await context({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    page.setDefaultTimeout(7000);
    async function go(name) {
      current = { page: name };
      const response = await page.goto(origin + '/' + name, { waitUntil: 'load' });
      check(response && response.ok(), 'page-response', response && response.status(), current);
      await page.evaluate(() => document.fonts.ready);
    }
    async function inspect(label = '') {
      const state = await page.evaluate(() => {
        const rect = element => { const r = element.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; };
        const hidden = element => !!element.closest('details:not([open])') && !element.closest('summary');
        const ids = [...document.querySelectorAll('[id]')].map(element => element.id);
        const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
        const labs = [...document.querySelectorAll('[data-lab]')].map(host => ({
          name: host.dataset.lab, initialized: host.dataset.labInitialized,
          invalid: /\b(?:NaN|Infinity|undefined)\b/.test(host.innerHTML),
          unavailable: /この数値範囲では計算できません/.test(host.textContent),
          figures: [...host.querySelectorAll('svg')].map(svg => {
            const view = svg.viewBox.baseVal;
            const labelled = (svg.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
            return { viewBox: { x: view.x, y: view.y, width: view.width, height: view.height },
              rect: rect(svg), role: svg.getAttribute('role'), title: svg.querySelector('title')?.textContent,
              description: svg.querySelector('desc')?.textContent,
              labelled: labelled.map(id => ({ id, exists: !!document.getElementById(id) })),
              texts: [...svg.querySelectorAll('text')].map(text => {
                const box = text.getBBox(), matrix = text.getScreenCTM();
                const size = parseFloat(getComputedStyle(text).fontSize);
                return { text: text.textContent, bbox: { x: box.x, y: box.y, width: box.width, height: box.height },
                  cssFontSize: size, effectiveFontPx: matrix ? size * Math.hypot(matrix.a, matrix.b) : null,
                  outside: box.x < view.x - .5 || box.y < view.y - .5 || box.x + box.width > view.x + view.width + .5 || box.y + box.height > view.y + view.height + .5 };
              }) };
          }) }));
        const staticFigures = [...document.querySelectorAll('main svg')].filter(svg => !svg.closest('[data-lab]')).map(svg => {
          const view = svg.viewBox.baseVal;
          return { viewBox: { x: view.x, y: view.y, width: view.width, height: view.height }, rect: rect(svg),
            title: svg.querySelector('title')?.textContent, description: svg.querySelector('desc')?.textContent,
            key: svg.closest('figure[data-visual]')?.dataset.visual,
            role: svg.getAttribute('role'), labels: (svg.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean).map(id => ({ id, exists: !!document.getElementById(id) })),
            texts: [...svg.querySelectorAll('text')].map(text => {
              const local = text.getBBox(), matrix = text.getScreenCTM(), size = parseFloat(getComputedStyle(text).fontSize);
              const relative = svg.getScreenCTM().inverse().multiply(matrix);
              const corners = [[local.x, local.y], [local.x + local.width, local.y], [local.x, local.y + local.height], [local.x + local.width, local.y + local.height]]
                .map(([x, y]) => new DOMPoint(x, y).matrixTransform(relative));
              const box = { x: Math.min(...corners.map(p => p.x)), y: Math.min(...corners.map(p => p.y)),
                width: Math.max(...corners.map(p => p.x)) - Math.min(...corners.map(p => p.x)),
                height: Math.max(...corners.map(p => p.y)) - Math.min(...corners.map(p => p.y)) };
              return { text: text.textContent, bbox: { x: box.x, y: box.y, width: box.width, height: box.height },
                cssFontSize: size, effectiveFontPx: matrix ? size * Math.hypot(matrix.a, matrix.b) : null,
                outside: box.x < view.x - .5 || box.y < view.y - .5 || box.x + box.width > view.x + view.width + .5 || box.y + box.height > view.y + view.height + .5 };
            }) };
        });
        const conceptTables = [...document.querySelectorAll('table.concept-table')].filter(table => !table.closest('[data-lab]')).map(table => {
          const wrapper = table.closest('.concept-table-wrap');
          return { key: table.dataset.visual, caption: table.caption?.textContent.trim(), captionRect: table.caption ? rect(table.caption) : null,
            brokenMathGroups: [...table.querySelectorAll('.table-math')].filter(group => group.getClientRects().length !== 1).map(group => group.textContent),
            transforms: [...new Set([...table.querySelectorAll('th')].map(cell => getComputedStyle(cell).textTransform))],
            headers: table.querySelectorAll('th').length, unscoped: [...table.querySelectorAll('th')].filter(t => !t.hasAttribute('scope')).length,
            wrapper: wrapper ? { rect: rect(wrapper), tabindex: wrapper.tabIndex, role: wrapper.getAttribute('role'),
              label: wrapper.getAttribute('aria-label'), clientWidth: wrapper.clientWidth, scrollWidth: wrapper.scrollWidth } : null,
            fontPx: Math.min(...[...table.querySelectorAll('th,td')].map(cell => parseFloat(getComputedStyle(cell).fontSize))) };
        });
        const undefinedSvgTokens = [...document.querySelectorAll('main svg')].flatMap(svg =>
          [...svg.outerHTML.matchAll(/var\((--[\w-]+)\s*\)/g)].map(match => match[1]))
          .filter(token => !getComputedStyle(document.documentElement).getPropertyValue(token).trim());
        const math = [...document.querySelectorAll('main math')].filter(element => !hidden(element));
        const sectionMenu = document.querySelector('.section-menu');
        const visible = element => !!element && element.getBoundingClientRect().width > 0 && element.getBoundingClientRect().height > 0
          && getComputedStyle(element).visibility !== 'hidden' && getComputedStyle(element).display !== 'none' && !hidden(element);
        const mathHints = [...document.querySelectorAll('.chapter-header .math-scroll-hint')];
        return { width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          h1: [...document.querySelectorAll('h1')].map(element => ({ text: element.textContent, rect: rect(element) })),
          mainLength: document.querySelector('main')?.innerText.length || 0,
          math: { count: math.length, total: document.querySelectorAll('main math').length, native: CSS.supports('math-style', 'normal'), invalidBoxes: math.map(rect).filter(r => r.width <= 0 || r.height <= 0) },
          duplicateIds: [...new Set(duplicates)], menuOpen: document.querySelector('.chapter-menu')?.open, labs, staticFigures,
          conceptTables,
          chapterSummaryVisible: visible(document.querySelector('.chapter-menu > summary')),
          mathHint: { count: mathHints.length, texts: mathHints.map(element => element.textContent.trim()), visible: mathHints.map(visible) },
          sectionMenu: { exists: !!sectionMenu, native: sectionMenu?.tagName === 'DETAILS', open: sectionMenu?.open,
            summaryVisible: visible(sectionMenu?.querySelector('summary')),
            navigationVisible: visible(sectionMenu?.querySelector('nav[aria-label="この章の目次"]')) },
          undefinedSvgTokens: [...new Set(undefinedSvgTokens)] };
      });
      const where = { ...current, width: state.width, theme: await page.locator('html').getAttribute('data-theme') || 'auto', label };
      check(state.h1.length === 1 && state.h1[0].text.trim() && state.h1[0].rect.height > 0, 'heading-render', state.h1, where);
      check(state.mainLength > 150, 'body-render', state.mainLength, where);
      check(state.scrollWidth <= state.width + 1, 'page-horizontal-overflow', { viewport: state.width, scroll: state.scrollWidth }, where);
      check(!state.duplicateIds.length, 'duplicate-ids', state.duplicateIds, where);
      check(state.math.native && !state.math.invalidBoxes.length, 'mathml-render', state.math, where);
      check(!state.undefinedSvgTokens.length, 'svg-color-tokens-defined', state.undefinedSvgTokens, where);
      if (state.width <= 760) check(state.menuOpen === false, 'mobile-menu-initially-closed', state.menuOpen, where);
      else if (where.page !== 'index.html') check(state.chapterSummaryVisible, 'desktop-chapter-menu-summary-visible', null, where);
      if (where.page !== 'index.html') {
        check(state.sectionMenu.exists && state.sectionMenu.native, 'section-menu-native-details', state.sectionMenu, where);
        if (state.width <= 760) {
          check(state.sectionMenu.open === false && state.sectionMenu.summaryVisible && !state.sectionMenu.navigationVisible,
            'mobile-section-menu-visible-and-closed', state.sectionMenu, where);
        } else {
          check(state.sectionMenu.open === true && state.sectionMenu.summaryVisible && state.sectionMenu.navigationVisible,
            'desktop-section-menu-open-readable', state.sectionMenu, where);
        }
        if (state.math.total > 0) {
          check(state.mathHint.count === 1 && state.mathHint.texts[0] === mathScrollHintText,
            'math-scroll-hint-once-in-header', state.mathHint, where);
          check(state.mathHint.visible[0] === (state.width <= 760), 'math-scroll-hint-responsive-visibility', state.mathHint, where);
        } else check(state.mathHint.count === 0, 'mathless-chapter-no-scroll-hint', state.mathHint, where);
      }
      for (const lab of state.labs) {
        check(lab.initialized === 'true' && lab.figures.length > 0, 'lab-initialized', lab.name, where);
        check(!lab.invalid && !lab.unavailable, 'lab-finite-markup', { name: lab.name, invalid: lab.invalid, unavailable: lab.unavailable }, where);
        for (const [index, figure] of lab.figures.entries()) {
          check(figure.rect.width > 0 && figure.rect.height > 0 && figure.role === 'img' && !!figure.title && !!figure.description && figure.labelled.length >= 2 && figure.labelled.every(ref => ref.exists), 'svg-accessibility', { lab: lab.name, index }, where);
          for (const text of figure.texts.filter(item => item.outside)) report.candidates.push({ code: 'svg-text-outside-viewbox', ...where, lab: lab.name, figure: index, ...text });
        }
      }
      for (const [index, figure] of state.staticFigures.entries()) {
        check(figure.rect.width > 0 && figure.rect.height > 0 && figure.role === 'img' && !!figure.title && !!figure.description && figure.labels.length >= 2 && figure.labels.every(ref => ref.exists), 'static-svg-render-accessibility', index, where);
        for (const text of figure.texts.filter(item => item.outside)) report.candidates.push({ code: 'static-svg-text-outside-viewbox', ...where, figure: index, ...text });
        if (figure.key) {
          const minFont = Math.min(...figure.texts.map(text => text.effectiveFontPx));
          check(minFont >= 14, 'concept-svg-readable-font', { key: figure.key, minFont }, where);
          for (let a = 0; a < figure.texts.length; a++) for (let b = a + 1; b < figure.texts.length; b++) {
            const first = figure.texts[a], second = figure.texts[b], u = first.bbox, v = second.bbox;
            const width = Math.min(u.x + u.width, v.x + v.width) - Math.max(u.x, v.x);
            const height = Math.min(u.y + u.height, v.y + v.height) - Math.max(u.y, v.y);
            if (width > 1 && height > 1 && width * height > 12 && width * height > .12 * Math.min(u.width * u.height, v.width * v.height)) {
              report.candidates.push({ code: 'concept-svg-text-collision', ...where, key: figure.key, first: first.text, second: second.text, width, height });
            }
          }
        }
        if (where.page === 'invariants.html' && state.width === 320) {
          const minFont = Math.min(...figure.texts.map(text => text.effectiveFontPx));
          if (minFont < 12) report.candidates.push({ code: 'static-svg-effective-font-under-12px', ...where, minFont });
        }
      }
      for (const table of state.conceptTables) {
        check(!!table.key && !!table.caption && table.headers > 0 && table.unscoped === 0 && !!table.wrapper
          && table.wrapper.tabindex === 0 && table.wrapper.role === 'region' && !!table.wrapper.label,
          'concept-table-accessibility', table, where);
        check(table.brokenMathGroups.length === 0, 'concept-table-math-units-stay-whole', { key: table.key, groups: table.brokenMathGroups }, where);
        check(table.transforms.every(value => value === 'none'), 'concept-table-preserves-math-case', table, where);
        check(table.fontPx >= 14 && table.wrapper.rect.width <= state.width + 1,
          'concept-table-readable-contained', table, where);
        check(table.captionRect && table.captionRect.x >= table.wrapper.rect.x - 1
          && table.captionRect.x + table.captionRect.width <= table.wrapper.rect.x + table.wrapper.rect.width + 1,
          'concept-table-caption-stays-visible', table, where);
        if (where.width === 1280) check(table.wrapper.scrollWidth <= table.wrapper.clientWidth + 1,
          'desktop-concept-table-fits-reading-column', table, where);
      }
      if (where.page !== 'index.html') check(state.staticFigures.some(figure => figure.key) || state.conceptTables.length > 0,
        'every-chapter-has-concept-visual', null, where);
      report.states.push({ ...where, ...state });
      return state;
    }
    phase = 'page-states';
    for (const width of [1280, 390, 320]) for (const theme of ['light', 'dark']) {
      await page.setViewportSize({ width, height: 900 });
      for (const name of known) await section('page-states', async () => {
        await go(name); await page.locator('#theme-select').selectOption(theme);
        await inspect('initial');
      });
      console.log(`Page states: ${width}px ${theme}, ${report.states.length}/${expectedStates}.`);
      await fs.writeFile(path.join(config.output, 'browser-qa.json'), JSON.stringify(report, null, 2) + '\n');
    }
    await section('responsive-menu-resize', async () => {
      await page.setViewportSize({ width: 320, height: 900 });
      await go('gradient.html');
      const steps = [];
      // Keep this document loaded: a reload would hide stale native details state.
      for (const width of [320, 1280, 320]) {
        await page.setViewportSize({ width, height: 900 });
        await page.waitForFunction(wide => ['.chapter-menu', '.section-menu'].every(selector =>
          document.querySelector(selector)?.open === wide), width > 760);
        for (const selector of ['.chapter-menu', '.section-menu']) {
          const menu = page.locator(selector), summary = menu.locator(':scope > summary'), nav = menu.locator('nav');
          const open = await menu.getAttribute('open') !== null;
          check(open === (width > 760), 'menu-state-after-resize', { selector, width, open }, current);
          if (width > 760) {
            check(await summary.isVisible() && await nav.isVisible(), 'wide-menu-readable-after-resize', { selector, width }, current);
          } else {
            check(await summary.isVisible() && !await nav.isVisible(), 'narrow-menu-operable-after-resize', { selector, width }, current);
            await summary.focus(); await summary.press('Enter');
            check(await menu.getAttribute('open') !== null && await nav.isVisible(), 'narrow-resized-menu-enter-open', { selector, width }, current);
            await summary.press('Enter');
            check(await menu.getAttribute('open') === null && !await nav.isVisible(), 'narrow-resized-menu-enter-close', { selector, width }, current);
          }
          steps.push({ selector, width, open, visibleNavigationExpected: width > 760 });
        }
      }
      check(new URL(page.url()).pathname === '/gradient.html', 'resize-keeps-document-url', page.url());
      report.interactions.push({ kind: 'responsive-menu-resize', page: 'gradient.html', reloadsBetweenWidths: 0, steps });
    });
    await section('navigation-and-details', async () => {
      await page.setViewportSize({ width: 390, height: 900 });
      for (const chapter of catalog.chapters) {
        const name = chapter.slug + '.html'; await go(name);
        const links = page.locator('.chapter-pagination a');
        for (const index of [0, 1]) {
          const href = await links.nth(index).getAttribute('href');
          if (index === 1 && chapter.slug === catalog.chapters.at(-1).slug) {
            check(href === 'index.html#learning-map' && (await links.nth(index).innerText()).trim() === 'その先の数学へ →',
              'last-chapter-learning-map', { href, label: await links.nth(index).innerText() }, { page: name });
          }
          await links.nth(index).click();
          check(page.url() === new URL(href, origin + '/' + name).href, 'pagination-click', { index, href, actual: page.url() }, { page: name });
          await go(name);
        }
        const details = page.locator('article.exercise details');
        const count = await details.count();
        for (let index = 0; index < count; index++) {
          const detail = details.nth(index), summary = detail.locator('summary');
          await summary.click();
          check(await detail.getAttribute('open') !== null && (await detail.innerText()).length > (await summary.innerText()).length, 'exercise-detail-open', index, { page: name });
          await summary.click();
          check(await detail.getAttribute('open') === null, 'exercise-detail-close', index, { page: name });
        }
        const menu = page.locator('.chapter-menu');
        await menu.locator('summary').focus(); await page.keyboard.press('Enter');
        check(await menu.getAttribute('open') !== null, 'mobile-menu-enter-open', null, { page: name });
        await page.keyboard.press('Enter');
        check(await menu.getAttribute('open') === null, 'mobile-menu-enter-close', null, { page: name });
        await page.locator('#theme-select').selectOption('dark');
        const dark = await page.locator('body').evaluate(element => getComputedStyle(element).backgroundColor);
        await page.locator('#theme-select').selectOption('light');
        const light = await page.locator('body').evaluate(element => getComputedStyle(element).backgroundColor);
        check(dark !== light, 'theme-colors-change', { dark, light }, { page: name });
        await page.locator('#theme-select').selectOption('auto');
        check(await page.locator('html').getAttribute('data-theme') === null, 'theme-auto', null, { page: name });
        report.interactions.push({ kind: 'chapter-ui', page: name, paginationClicks: 2, detailsToggled: count, menuEnter: true, theme: true });
      }
    });
    for (const width of [390, 320]) await section('section-menu-navigation', async () => {
      await page.setViewportSize({ width, height: 900 });
      for (const chapter of catalog.chapters) {
        const name = chapter.slug + '.html'; await go(name);
        const menu = page.locator('details.section-menu');
        const summary = menu.locator(':scope > summary');
        const nav = page.getByRole('navigation', { name: 'この章の目次', exact: true });
        const where = { page: name, width };
        check(await summary.isVisible() && (await summary.innerText()).includes('この章の目次'), 'section-menu-visible-summary', null, where);
        check(await menu.getAttribute('open') === null && !await nav.isVisible(), 'section-menu-mobile-initial-closed', null, where);
        await summary.focus(); await summary.press('Enter');
        check(await menu.getAttribute('open') !== null && await nav.isVisible(), 'section-menu-enter-open', null, where);
        const links = nav.locator('a[href^="#"]');
        const link = links.nth(Math.min(1, (await links.count()) - 1));
        const href = await link.getAttribute('href'), label = await link.innerText();
        await link.click();
        const target = page.locator(href);
        const targetTop = await target.evaluate(element => element.getBoundingClientRect().top);
        check(new URL(page.url()).hash === href && targetTop >= -2 && targetTop < 900,
          'section-menu-link-reaches-section', { href, label, targetTop, actualHash: new URL(page.url()).hash }, where);
        await summary.focus(); await summary.press('Enter');
        check(await menu.getAttribute('open') === null && !await nav.isVisible(), 'section-menu-enter-close', null, where);
        const footerLink = page.locator('.site-footer').getByRole('link', { name: 'ページの先頭へ ↑', exact: true });
        await footerLink.click();
        const positions = await page.locator('.site-header,.chapter-menu > summary,.section-menu > summary').evaluateAll(elements => elements.map(element => {
          const box = element.getBoundingClientRect();
          return { text: element.textContent.trim(), top: box.top, bottom: box.bottom, width: box.width };
        }));
        const footerHash = new URL(page.url()).hash;
        check(footerHash === '#top' && positions.length === 3 && positions.every(position => position.width > 0 && position.top >= -2 && position.bottom <= 900),
          'footer-returns-header-and-menu-summaries', { footerHash, positions }, where);
        check(await page.locator('.skip-link').getAttribute('href') === '#main', 'skip-link-still-targets-main', null, where);
        report.interactions.push({ kind: 'section-menu-ui', ...where, href, label, targetTop, enterOpenClose: true,
          footerReturn: { hash: footerHash, positions } });
      }
      console.log(`Section menu navigation: ${width}px, ${catalog.chapters.length} chapters.`);
    });
    async function snapshot(host) {
      return host.evaluate(element => ({ markup: element.innerHTML,
        values: [...element.querySelectorAll('input,select')].map(control => ({ id: control.id, value: control.value })) }));
    }
    async function setRange(host, key, value) {
      const control = host.locator(`input[data-key="${key}"]`);
      await control.fill(String(value)); await control.dispatchEvent('input');
      check(Number(await control.inputValue()) === Number(value), 'range-value', { key, value }, current);
    }
    async function healthy(host, operation) {
      const state = await host.evaluate(element => ({ svg: element.querySelectorAll('svg').length, text: element.querySelector('.lab-readout')?.textContent,
        labError: element.dataset.labError, domainState: element.dataset.domainState, invalid: /\b(?:NaN|Infinity|undefined)\b/.test(element.innerHTML), unavailable: /この数値範囲では計算できません/.test(element.textContent) }));
      check(state.svg > 0 && !state.invalid && !state.unavailable && state.labError !== 'true', 'lab-operation-healthy', { operation, ...state }, current);
      report.interactions.push({ kind: 'lab-operation', ...current, operation, ...state });
    }
    async function firstNumber(host, expected, operation) {
      const text = await host.locator('.lab-readout strong').first().innerText();
      check(Math.abs(Number(text.replace('約', '')) - expected) <= .000051, 'lab-known-value', { operation, text, expected }, current);
    }
    async function rawValue(host, key, expected, operation) {
      const field = host.locator('.lab-readout span[data-value="' + key + '"]');
      const raw = await field.getAttribute('data-raw');
      const actual = raw === 'null' ? null : Number(raw);
      check(expected === null ? raw === 'null' : raw !== null && raw !== 'null' && Number.isFinite(actual) && Math.abs(actual - expected) <= 1e-11,
        'probability-known-value', { key, raw, expected, operation }, current);
    }
    const newLabs = new Set(['linear-core-map','linear-core-least-squares','linear-core-spectral','opt-gradient','opt-projection','opt-kkt','vector-work','vector-flux','vector-stokes','numerical-root','numerical-difference','numerical-ode','complex-difference', 'complex-log', 'complex-residue', 'discrete-modular', 'discrete-recurrence', 'discrete-shortest', 'multivariable-compass', 'multivariable-curvature', 'multivariable-constraint', 'multivariable-double-integral', 'multivariable-polar', 'probability-bayes', 'probability-independence', 'probability-binomial', 'probability-density', 'probability-lln']);
    for (const chapter of catalog.chapters.filter(item => item.lab)) await section('labs-and-keyboard', async () => {
      await go(chapter.slug + '.html');
      const host = page.locator('[data-lab]'), initial = await snapshot(host);
      const reset = host.getByRole('button', { name: '初期状態に戻す', exact: true });
      const controls = host.locator('input[type="range"],select');
      for (let index = 0; index < await controls.count(); index++) {
        // Controls can intentionally disable others (e.g. a path without coefficient c).
        // Exercise each control from its usable initial state, then test the combined reset.
        await reset.click();
        const control = controls.nth(index);
        if (await control.evaluate(element => element.tagName) === 'SELECT') {
          const values = await control.locator('option').evaluateAll(elements => elements.map(element => element.value));
          await control.selectOption(values.find(value => value !== initial.values[index].value));
        } else {
          await control.focus();
          const old = await control.inputValue(), max = await control.getAttribute('max');
          await control.press(Number(old) === Number(max) ? 'ArrowLeft' : 'ArrowRight');
          check(await control.inputValue() !== old, 'range-arrow-changes-value', await control.getAttribute('id'), current);
        }
        await healthy(host, 'generic-control-' + index);
      }
      await reset.click();
      check(JSON.stringify(await snapshot(host)) === JSON.stringify(initial), 'lab-reset-restores-markup-and-values', chapter.lab, current);
      if (newLabs.has(chapter.lab)) {
        const ranges = host.locator('input[type="range"]');
        for (let index = 0; index < await ranges.count(); index++) {
          const range = ranges.nth(index);
          for (const [key, attribute] of [['Home', 'min'], ['End', 'max']]) {
            await range.focus(); await range.press(key);
            check(Number(await range.inputValue()) === Number(await range.getAttribute(attribute)), 'range-key-endpoint', { index, key }, current);
            await healthy(host, `range-${index}-${key}`);
          }
          const end = Number(await range.inputValue()), step = Number(await range.getAttribute('step'));
          await range.press('ArrowLeft');
          check(Math.abs(Number(await range.inputValue()) - (end - step)) < 1e-8, 'range-key-step', index, current);
          await healthy(host, `range-${index}-ArrowLeft`);
        }
        await reset.click();
        if (chapter.lab === 'multivariable-compass') {
          await setRange(host, 'a', 0); await setRange(host, 'b', 0);
          check((await host.innerText()).includes('一意に定まらない（勾配0）'), 'zero-gradient-message', null, current);
          await firstNumber(host, 0, 'zero-gradient'); await healthy(host, 'zero-gradient');
        } else if (chapter.lab === 'multivariable-curvature') {
          for (const example of ['bowl', 'saddle', 'flat-min', 'flat-saddle']) {
            await host.locator('select').selectOption(example);
            for (const t of [-1, -.01, 0, .01, 1]) {
              await setRange(host, 't', t); await healthy(host, `${example}-t=${t}`);
              await firstNumber(host, example.startsWith('flat') ? t ** 4 : t ** 2, `${example}-t=${t}`);
            }
            check((await host.innerText()).includes(example.startsWith('flat') ? '判定不能（D = 0）' : example === 'bowl' ? '厳密局所最小' : '鞍点'), 'curvature-verdict', example, current);
          }
        } else if (chapter.lab === 'multivariable-constraint') {
          for (const [action, sign] of [['maximum', 1], ['minimum', -1]]) {
            await host.locator(`[data-action="${action}"]`).click();
            await firstNumber(host, sign * Math.sqrt(5), action); await healthy(host, action);
            check((await host.locator('[data-angle-note]').innerText()).includes('表示中'), 'constraint-analytic-angle', action, current);
            await host.locator('input').press('ArrowRight');
            check(!(await host.locator('[data-angle-note]').innerText()).includes('表示中'), 'constraint-slider-leaves-analytic-mode', action, current);
          }
        } else if (chapter.lab === 'multivariable-double-integral') {
          for (const n of [1, 2, 20, 32]) for (const rule of ['lower', 'upper', 'midpoint']) {
            await setRange(host, 'n', n); await host.locator('select').selectOption(rule);
            const expected = rule === 'lower' ? (n - 1) * (2 * n - 1) / (3 * n * n)
              : rule === 'upper' ? (n + 1) * (2 * n + 1) / (3 * n * n) : 2 / 3 - 1 / (6 * n * n);
            await firstNumber(host, expected, `${n}-${rule}`); await healthy(host, `${n}-${rule}`);
            const cellGrid = await host.locator('svg').first().evaluate((svg, n) => {
              // The unit-square grid excludes its hollow highlight and any lower comparison bars.
              const side = 254 / 1.16, left = 112 + .08 * side, top = 290 - 1.08 * side, step = side / n;
              const near = (a, b) => Math.abs(a - b) < 1e-8;
              const cells = [...svg.querySelectorAll('rect')].filter(rect => {
                const x = Number(rect.getAttribute('x')), y = Number(rect.getAttribute('y'));
                return rect.style.fill !== 'none' && near(Number(rect.getAttribute('width')), step)
                  && near(Number(rect.getAttribute('height')), step) && x >= left - 1e-8 && y >= top - 1e-8
                  && x + step <= left + side + 1e-8 && y + step <= top + side + 1e-8;
              });
              const indices = cells.map(rect => {
                const x = Number(rect.getAttribute('x')), y = Number(rect.getAttribute('y'));
                return { i: Math.round((x - left) / step), j: Math.round((y - top) / step), x, y };
              });
              return { count: cells.length, unique: new Set(indices.map(({ i, j }) => i + ',' + j)).size,
                aligned: indices.every(({ i, j, x, y }) => i >= 0 && i < n && j >= 0 && j < n
                  && near(x, left + i * step) && near(y, top + j * step)),
                area: cells.reduce((sum, rect) => sum + Number(rect.getAttribute('width')) * Number(rect.getAttribute('height')), 0),
                expectedArea: side * side };
            }, n);
            check(cellGrid.count === n * n && cellGrid.unique === n * n && cellGrid.aligned
              && Math.abs(cellGrid.area - cellGrid.expectedArea) < 1e-8, 'double-integral-cell-count', { n, rule, ...cellGrid }, current);
          }
        } else if (chapter.lab === 'multivariable-polar') {
          for (const r of [0, 1.5]) for (const dr of [.1, .5]) for (const angle of [-180, 180]) for (const width of [5, 90]) {
            for (const [key, value] of Object.entries({ innerRadius: r, radialWidth: dr, angle, angularWidth: width })) await setRange(host, key, value);
            const expected = ((r + dr) ** 2 - r ** 2) * width * Math.PI / 360;
            await firstNumber(host, expected, 'polar-endpoints'); await healthy(host, `polar-${r}-${dr}-${angle}-${width}`);
          }
        }
        await reset.click();
        check(JSON.stringify(await snapshot(host)) === JSON.stringify(initial), 'new-lab-final-reset', chapter.lab, current);
      }
      if (chapter.lab.startsWith('probability-')) {
        if (chapter.lab === 'probability-bayes') {
          for (const values of [
            { prior: .01, sensitivity: .9, falsePositive: .05 },
            { prior: .99, sensitivity: .9, falsePositive: .05 },
            { prior: .01, sensitivity: 0, falsePositive: 0 },
            { prior: .01, sensitivity: 1, falsePositive: 0 },
            { prior: .01, sensitivity: 0, falsePositive: 1 },
          ]) {
            for (const [key, value] of Object.entries(values)) await setRange(host, key, value);
            const yes = values.prior * values.sensitivity, positive = yes + (1 - values.prior) * values.falsePositive;
            await rawValue(host, 'positive', positive, 'bayes-endpoints');
            await rawValue(host, 'posterior', positive === 0 ? null : yes / positive, 'bayes-endpoints');
            await healthy(host, 'bayes-endpoints');
          }
        } else if (chapter.lab === 'probability-independence') {
          for (const [a, b] of [[.1, .1], [.1, .9], [.9, .1], [.9, .9], [.5, .5], [.8, .8], [.15, .9]]) {
            await setRange(host, 'a', a); await setRange(host, 'b', b);
            const joint = host.locator('input[data-key="joint"]');
            for (const attribute of ['min', 'max']) {
              const value = Number(await joint.getAttribute(attribute));
              await setRange(host, 'joint', value);
              await rawValue(host, 'difference', value - a * b, 'joint-feasible-endpoints');
              await rawValue(host, 'conditional', value / b, 'joint-feasible-endpoints');
              await healthy(host, 'joint-feasible-endpoints');
            }
          }
          await reset.click();
          await rawValue(host, 'difference', 0, 'independence-product');
          await rawValue(host, 'conditional', .5, 'independence-product');
        } else if (chapter.lab === 'probability-binomial') {
          check(await host.locator('svg').count() === 2, 'binomial-pmf-and-cdf-figures', null, current);
          for (const n of [1, 10, 40]) for (const p of [0, .5, 1]) {
            await setRange(host, 'n', n); await setRange(host, 'p', p);
            await rawValue(host, 'mean', n * p, 'binomial-endpoints');
            await rawValue(host, 'variance', n * p * (1 - p), 'binomial-endpoints');
            await healthy(host, 'binomial-endpoints');
            if (n === 40) {
              const points = await host.locator('svg').nth(1).evaluate(svg => {
                const circles = [...svg.querySelectorAll('circle')];
                return { count: circles.length,
                  minRadiusPx: Math.min(...circles.map(c => Number(c.getAttribute('r')) * svg.getBoundingClientRect().width / svg.viewBox.baseVal.width)) };
              });
              check(points.count > 0 && points.count <= 41 && points.minRadiusPx >= 2.5,
                'cdf-mobile-point-readability', points, current);
            }
          }
        } else if (chapter.lab === 'probability-density') {
          for (const b of [0, .5, 1]) {
            await setRange(host, 'b', b);
            await rawValue(host, 'probability', b * b, 'density-endpoints');
            await rawValue(host, 'density', 2 * b, 'density-endpoints');
            await healthy(host, 'density-endpoints');
          }
        } else if (chapter.lab === 'probability-lln') {
          for (const n of [10, 100, 200]) for (const p of [.1, .5, .9]) for (const epsilon of [.05, .1, .5]) {
            for (const [key, value] of Object.entries({ n, p, epsilon })) await setRange(host, key, value);
            let state = 42, count = 0;
            for (let i = 0; i < n; i++) {
              state = (Math.imul(1664525, state) + 1013904223) >>> 0;
              if (state / 4294967296 < p) count++;
            }
            const bound = Math.min(1, p * (1 - p) / (n * epsilon * epsilon));
            // UI p and epsilon are decimal multiples of .05, so integer units give an independent >= comparison.
            const center = n * Math.round(p * 100), radius = n * Math.round(epsilon * 100);
            let tail = 0, choose = 1;
            for (let k = 0; k <= n; k++) {
              if (k > 0) choose = choose * (n - k + 1) / k;
              if (Math.abs(100 * k - center) >= radius) tail += choose * p ** k * (1 - p) ** (n - k);
            }
            await rawValue(host, 'mean', count / n, 'lln-prefix');
            await rawValue(host, 'bound', bound, 'lln-bound');
            await rawValue(host, 'exactTail', tail, 'lln-exact-tail');
            await healthy(host, 'lln-controls');
          }
        }
        await reset.click();
        check(JSON.stringify(await snapshot(host)) === JSON.stringify(initial), 'probability-lab-final-reset', chapter.lab, current);
      }
      if (chapter.lab.startsWith('discrete-')) {
        async function expectRaw(key, expected, operation) {
          const raw = await host.locator('span[data-value="' + key + '"]').getAttribute('data-raw');
          check(raw === String(expected), 'discrete-known-value', { key, raw, expected, operation }, current);
        }
        if (chapter.lab === 'discrete-modular') {
          for (const m of [2, 8, 12]) for (const a of [0, 1, m - 1]) for (const x of [0, m - 1]) {
            await setRange(host, 'm', m); await setRange(host, 'a', a); await setRange(host, 'x', x);
            const residues = Array.from({ length: m }, (_, k) => a * k % m);
            const inverse = residues.indexOf(1);
            await expectRaw('value', a * x % m, 'modular-endpoints');
            await expectRaw('imageSize', new Set(residues).size, 'modular-image');
            await expectRaw('inverse', inverse < 0 ? null : inverse, 'modular-inverse');
            await healthy(host, 'modular-endpoints');
          }
          await setRange(host, 'm', 12); await setRange(host, 'a', 11); await setRange(host, 'x', 11); await setRange(host, 'm', 2);
          for (const key of ['a', 'x']) {
            const input = host.locator('input[data-key="' + key + '"]');
            check(await input.inputValue() === '1' && await input.getAttribute('max') === '1', 'modular-dependent-range-clamped', { key }, current);
          }
          await expectRaw('value', 1, 'modular-clamped');
        } else if (chapter.lab === 'discrete-recurrence') {
          function choose(n, k) { let c = 1; for (let i = 1; i <= k; i++) c = c * (n - k + i) / i; return c; }
          for (const n of [0, 1, 2, 5, 20]) {
            await setRange(host, 'n', n);
            let ways = 0; for (let k = 0; k <= Math.floor(n / 2); k++) ways += choose(n - k, k);
            await expectRaw('value', ways, 'tilings-independent-count');
            await expectRaw('additions', Math.max(0, n - 1), 'tilings-additions');
            check(n >= 2 || await host.locator('span[data-value="left"],span[data-value="right"]').count() === 0,
              'tilings-basecase-has-no-negative-subproblem', { n }, current);
            await healthy(host, 'tilings-boundaries');
          }
          await host.locator('details').first().locator('summary').click();
          check(await host.locator('[data-table] table').isVisible(), 'recurrence-table-opens', null, current);
          await host.locator('details').first().locator('summary').click();
        } else if (chapter.lab === 'discrete-shortest') {
          const expected = {
            normal: { distance: 5, route: 'A-B-E-F', distances: [0, 2, 4, 4, 3, 5], settled: 6 },
            zeroTie: { distance: 3, route: 'A-B-E-F', distances: [0, 0, 2, 2, 1, 3], settled: 6 },
            disconnected: { distance: 'unreachable', route: null, distances: [0, 2, 4, 4, 3, 'unreachable'], settled: 5 }
          };
          for (const [preset, result] of Object.entries(expected)) {
            await host.locator('select[data-key="preset"]').selectOption(preset);
            await expectRaw('step', 0, 'shortest-preset-resets-step');
            const slider = host.locator('input[data-key="step"]');
            for (let step = 0; step <= Number(await slider.getAttribute('max')); step++) {
              await setRange(host, 'step', step); await healthy(host, 'shortest-step-' + preset + '-' + step);
              await expectRaw('settled', step, 'shortest-settled-count');
            }
            await expectRaw('distance', result.distance, 'shortest-final-distance');
            await expectRaw('route', result.route, 'shortest-final-route');
            await expectRaw('settled', result.settled, 'shortest-final-settled');
            for (const [index, id] of ['A','B','C','D','E','F'].entries()) await expectRaw('distance-' + id, result.distances[index], 'shortest-final-all-distances');
            if (preset === 'zeroTie') await expectRaw('parent-D', 'A', 'shortest-tie-keeps-parent');
            await slider.focus(); await slider.press('Home'); await expectRaw('step', 0, 'shortest-keyboard-home');
          }
        }
        await reset.click();
        check(JSON.stringify(await snapshot(host)) === JSON.stringify(initial), 'discrete-lab-final-reset', chapter.lab, current);
      }
      if (chapter.lab.startsWith('complex-')) {
        async function complexValue(key, expected, operation) {
          const raw = await host.locator('span[data-value="' + key + '"]').getAttribute('data-raw');
          let value; try { value = JSON.parse(raw); } catch { value = raw; }
          const ok = expected === null ? value === null : typeof expected === 'object'
            ? value !== null && Number.isFinite(value.re) && Number.isFinite(value.im)
              && Math.abs(value.re - expected.re) < 1e-10 && Math.abs(value.im - expected.im) < 1e-10
            : typeof expected === 'number' ? Number.isFinite(value) && Math.abs(value - expected) < 1e-10 : value === expected;
          check(ok, 'complex-known-value', { key, raw, expected, operation }, current);
        }
        async function domain(expected, operation) {
          check(await host.getAttribute('data-domain-state') === expected && await host.getAttribute('data-lab-error') === 'false',
            'complex-domain-state', { expected, operation }, current);
          await healthy(host, operation);
        }
        if (chapter.lab === 'complex-difference') {
          for (const kind of ['square', 'conjugate', 'absSquare']) for (const [x,y] of [[0,0],[.5,-.5]]) for (const h of [.05,1]) for (const theta of [0,45,90,360]) {
            await host.locator('select[data-key="function"]').selectOption(kind);
            for (const [key,value] of Object.entries({x,y,h,theta})) await setRange(host,key,value);
            const t=theta*Math.PI/180,c=Math.cos(t),v=Math.sin(t),c2=Math.cos(2*t),v2=Math.sin(2*t);
            const expected=kind==='square'?{re:2*x+h*c,im:2*y+h*v}:kind==='conjugate'?{re:c2,im:-v2}
              :{re:x+x*c2+y*v2+h*c,im:-y+y*c2-x*v2-h*v};
            const derivative=kind==='square'?{re:2*x,im:2*y}:kind==='absSquare'&&x===0&&y===0?{re:0,im:0}:null;
            await complexValue('selected',expected,'difference-independent-formula');
            await complexValue('derivative',derivative,'derivative-existence');
            await complexValue('error',derivative===null?null:h,'finite-difference-error');
            if(derivative===null||derivative.re===0&&derivative.im===0) await complexValue('derivativeRotation',null,'zero-or-missing-rotation');
            await domain('defined','difference-directions');
          }
        } else if(chapter.lab==='complex-log') {
          for(const radius of [.5,2])for(const theta of [-360,-185,-180,-175,0,175,180,185,360]){
            await setRange(host,'radius',radius);await setRange(host,'theta',theta);
            const t=theta*Math.PI/180,onCut=Math.abs(theta)===180,point={re:radius*Math.cos(t),im:radius*Math.sin(t)};
            const angle=onCut?null:Math.atan2(point.im,point.re);
            await complexValue('point',point,'log-input');
            await complexValue('tracked',{re:Math.log(radius),im:t},'log-path-lift');
            await complexValue('principal',onCut?null:{re:Math.log(radius),im:angle},'principal-branch');
            await complexValue('principalAngle',angle,'principal-angle');
            check((await host.locator('path[data-curve="principal"]').getAttribute('d')).match(/M/g).length===3,'log-curve-breaks-at-cut',null,current);
            await domain(onCut?'cut':'defined','log-cut-and-revisit');
          }
        } else if(chapter.lab==='complex-residue'){
          for(const a of [-2,-1,-.99,0,.5,.99,1,1.01,2])for(const orientation of [1,-1])for(const n of [16,64]){
            await host.locator('select[data-key="orientation"]').selectOption(String(orientation));
            await setRange(host,'a',a);await setRange(host,'n',n);
            const boundary=Math.abs(a)===1,inside=Math.abs(a)<1;
            const exact=boundary?null:{re:0,im:inside?orientation*2*Math.PI:0};
            const numeric=boundary?null:{re:0,im:orientation*2*Math.PI/(1+a**n)};
            await complexValue('exact',exact,'circle-integral-exact');
            await complexValue('numeric',numeric,'midpoint-independent-formula');
            await complexValue('error',boundary?null:Math.abs(numeric.im-exact.im),'circle-quadrature-error');
            await complexValue('region',boundary?'boundary':inside?'inside':'outside','pole-region');
            await domain(boundary?'boundary':'defined','pole-on-inside-outside');
          }
        }
        await reset.click();
        check(JSON.stringify(await snapshot(host))===JSON.stringify(initial),'complex-lab-final-reset',chapter.lab,current);
      }

      if (chapter.lab.startsWith('vector-') || chapter.lab.startsWith('numerical-') || chapter.lab.startsWith('opt-') || chapter.lab.startsWith('linear-core-')) {
        async function read(key) {
          const raw = await host.locator('.lab-readout span[data-value="' + key + '"]').getAttribute('data-raw');
          try { return JSON.parse(raw); } catch { return raw; }
        }
        function close(actual, expected) {
          if (typeof expected === 'number') return typeof actual === 'number' && Number.isFinite(actual) && Math.abs(actual - expected) <= 1e-10 * (1 + Math.abs(expected));
          if (Array.isArray(expected)) return Array.isArray(actual) && actual.length === expected.length && actual.every((v,i) => close(v,expected[i]));
          return actual === expected;
        }
        async function expect(key, expected, operation) {
          const actual = await read(key);
          check(close(actual,expected), chapter.lab.startsWith('linear-core-')?'linear-core-known-value':chapter.lab.startsWith('opt-')?'optimization-known-value':'vector-numerical-known-value', {key,actual,expected,operation}, current);
        }
        async function defined(operation, expectedDomain) {
          check(await host.getAttribute('data-lab-error') === 'false' && (!expectedDomain || await host.getAttribute('data-domain-state') === expectedDomain),
            'vector-numerical-domain', {operation,expectedDomain},current);
          await healthy(host,operation);
        }

        async function projectedOrientation(orientation) {
          const metrics=await host.locator('[data-figures] svg').first().evaluate(svg=>{
            const texts=[...svg.querySelectorAll('text')],find=s=>texts.find(t=>t.textContent.trim()===s);
            const normalLegends=texts.filter(t=>/^(?:実線矢印n ／ 破線矢印F|nは視線方向（点に投影）|青い矢印n：選んだ法線)$/.test(t.textContent.trim()));
            const x=find('x'),y=find('y'),n=find('n')||(normalLegends.length===1?normalLegends[0]:null),z=find('z');
            const nb=n?.getBoundingClientRect(),zb=z?.getBoundingClientRect();
            const clear=nb&&zb&&(nb.right+.5<zb.left||zb.right+.5<nb.left||nb.bottom+.5<zb.top||zb.bottom+.5<nb.top);
            const dets=[...svg.querySelectorAll('line')].filter(e=>e.style.stroke==='var(--series-1)').map(e=>{
              const [x1,y1,x2,y2]=['x1','y1','x2','y2'].map(k=>Number(e.getAttribute(k)));
              return (x1-180)*(y2-190)-(y1-190)*(x2-180);
            });
            return {x:x?Number(x.getAttribute('x')):null,y:y?Number(y.getAttribute('x')):null,normalClear:!!clear,dets};
          });
          check(metrics.x!==null&&metrics.y!==null&&metrics.x<metrics.y,'projection-right-handed-axis-labels',metrics,current);
          check(metrics.normalClear,'projection-normal-z-label-separation',metrics,current);
          if(orientation!==null)check(metrics.dets.length===3&&metrics.dets.every(det=>orientation*det<0),
            'stokes-projected-boundary-orientation',{orientation,...metrics},current);
        }
        if (chapter.lab === 'vector-work') {
          for (const field of ['gradient','rotation']) for (const pathName of ['straight','parabola','x-first','y-first']) for (const orientation of [1,-1]) for (const n of [16,128]) {
            await host.locator('select[data-key="field"]').selectOption(field);
            await host.locator('select[data-key="path"]').selectOption(pathName);
            await host.locator('select[data-key="orientation"]').selectOption(String(orientation));
            await setRange(host,'n',n);
            const base=field==='gradient'?1:pathName==='straight'?0:pathName==='parabola'?1/3:pathName==='x-first'?1:-1;
            const correction=pathName==='parabola'?(field==='gradient'?1/(4*n*n):1/(12*n*n)):0;
            await expect('exact',orientation*base,'work-analytic');
            await expect('numeric',orientation*(base-correction),'work-midpoint-closed-form');
            await expect('error',correction,'work-error');
            await expect('start',orientation===1?[0,0]:[1,1],'work-oriented-start');
            await expect('end',orientation===1?[1,1]:[0,0],'work-oriented-end');
            await defined('work-'+field+'-'+pathName,'defined');
          }
        } else if (chapter.lab === 'vector-flux') {
          for (const [a,b,c] of [[0,0,0],[1,-1,-2],[-1,1,2],[.5,.25,1]]) for (const orientation of [1,-1]) {
            for (const [key,value] of Object.entries({a,b,c})) await setRange(host,key,value);
            await host.locator('select[data-key="orientation"]').selectOption(String(orientation));
            const norm=Math.hypot(a,b,1);
            await expect('area',4*norm,'plane-area');
            await expect('projectedArea',4,'plane-projection');
            await expect('unitNormal',[-orientation*a/norm,-orientation*b/norm,orientation/norm],'plane-oriented-unit-normal');
            await expect('flux',orientation*4*c,'plane-flux');
            await expect('normalDensity',orientation*c/norm,'plane-normal-density');
            await defined('plane-flux','defined');
            await projectedOrientation(null);
          }
        } else if (chapter.lab === 'vector-stokes') {
          for (const height of [-1.5,0,1.5]) for (const alpha of [-1,0,1]) for (const orientation of [1,-1]) for (const n of [8,128]) {
            for (const [key,value] of Object.entries({height,alpha,n})) await setRange(host,key,value);
            await host.locator('select[data-key="orientation"]').selectOption(String(orientation));
            const exact=orientation*Math.PI*(1+alpha),correction=Math.PI*alpha/(2*n*n);
            await expect('circulationExact',exact,'stokes-boundary');
            await expect('surfaceExact',exact,'stokes-surface');
            await expect('surfaceNumeric',exact-orientation*correction,'stokes-midpoint-cubic');
            await expect('error',Math.abs(correction),'stokes-midpoint-error');
            await expect('boundaryHeight',0,'stokes-fixed-boundary');
            await expect('centerNormalArea',[0,0,orientation],'stokes-graph-normal');
            await defined('stokes-height-and-cancellation','defined');
            await projectedOrientation(orientation);
          }
        } else if (chapter.lab === 'numerical-root') {
          await host.locator('select[data-key="method"]').selectOption('bisection');
          for (const kind of ['square','cycle']) for (const steps of [0,1,4,12]) {
            await host.locator('select[data-key="function"]').selectOption(kind);
            await setRange(host,'steps',steps);
            const bracket=await read('bracket'),estimate=await read('estimate'),bound=1/(2**steps);
            const f=x=>kind==='square'?x*x-2:x*x*x-2*x+2;
            check(Array.isArray(bracket)&&bracket.length===2&&Math.abs(bracket[1]-bracket[0]-2*bound)<1e-12&&f(bracket[0])*f(bracket[1])<=0,
              'bisection-sign-and-width',{kind,steps,bracket,bound},current);
            check(Math.abs(estimate-(bracket[0]+bracket[1])/2)<1e-12,'bisection-midpoint',null,current);
            await expect('bound',bound,'bisection-half-width');
            await defined('bisection-guarantee','bracket');
          }
          await host.locator('select[data-key="method"]').selectOption('newton');
          for (const [kind,x0,steps,estimate,status] of [['square',1,1,1.5,'steps'],['square',-1,1,-1.5,'steps'],['square',0,4,0,'derivative-zero'],['cycle',0,1,1,'steps'],['cycle',0,2,0,'steps']]) {
            await host.locator('select[data-key="function"]').selectOption(kind);
            await setRange(host,'x0',x0);await setRange(host,'steps',steps);
            await expect('estimate',estimate,'newton-independent-rational-or-cycle');
            await expect('bracket',null,'newton-no-bracket');
            await expect('bound',null,'newton-no-guaranteed-error');
            await expect('status',status,'newton-stop-reason');
            await defined('newton-stop-and-cycle',status);
          }
        } else if (chapter.lab === 'numerical-difference') {
          for (const x of [-2,0,2]) for (const exponent of [0,4,8,12,16]) {
            await setRange(host,'x',x);await setRange(host,'exponent',exponent);
            const h=10**(-exponent),exact=Math.exp(x),plus=Math.exp(x+h),minus=Math.exp(x-h);
            // Rounded execution is checked separately from mathematical truncation bounds.
            await expect('h',h,'difference-step');
            await expect('exact',exact,'difference-reference');
            await expect('forward',(plus-exact)/h,'difference-executed-forward');
            await expect('central',(plus-minus)/(2*h),'difference-executed-central');
            await expect('actualForwardStep',(x+h)-x,'difference-rounded-input-step');
            await expect('actualBackwardStep',x-(x-h),'difference-rounded-input-step');
            await expect('forwardTruncationBound',Math.exp(x+h)*h/2,'difference-Taylor-bound');
            await expect('centralTruncationBound',Math.exp(x+h)*h*h/6,'difference-Taylor-bound');
            const resolved=x+h!==x&&x-h!==x;
            await expect('inputResolved',resolved,'difference-input-resolution');
            if (exponent<=4) {
              const realForward=exact*Math.expm1(h)/h,realCentral=exact*(Math.expm1(h)-Math.expm1(-h))/(2*h);
              const actualForward=await read('forward'),actualCentral=await read('central');
              check(Math.abs(actualForward-realForward)<1e-9&&Math.abs(actualCentral-realCentral)<1e-9,'difference-independent-expm1-oracle',{x,exponent},current);
            }
            await defined('difference-rounding',resolved?'resolved':'rounded-input');
          }
        } else if (chapter.lab === 'numerical-ode') {
          for (const [lambda,n] of [[-4,1],[-4,4],[-1,1],[-1,8],[0,8],[2,1],[2,64]]) for (const y0 of [-2,0,2]) {
            for (const [key,value] of Object.entries({lambda,n,y0})) await setRange(host,key,value);
            const h=2/n,q=1+h*lambda,stability=Math.abs(q)<1?'decay':Math.abs(q)===1?'boundary':'growth';
            await expect('factor',q,'Euler-amplification');
            await expect('final',y0*q**n,'Euler-closed-form');
            await expect('exact',y0*Math.exp(2*lambda),'ODE-exact');
            await expect('error',Math.abs(y0*q**n-y0*Math.exp(2*lambda)),'Euler-global-error');
            await expect('stability',stability,'Euler-stability-boundary');
            await defined('Euler-positive-negative-zero',stability);
          }
        }

        if(chapter.lab==='opt-gradient'){
          const cases=[
            [1,.5,0,1,-1],[1,.5,40,2,2],[4,.15,12,1,1],[4,.5,8,1,1],
            [4,.5,8,1,0],[16,.125,8,1,1],[16,.025,40,-2,2],[16,.5,40,2,2],
            [16,.5,40,0,0],[16,0,40,1,1],[16,.25,1,1,1],[16,.25,20,1,0]];
          for(const [kappa,alpha,n,x0,y0] of cases){
            for(const [key,value] of Object.entries({kappa,alpha,n,x0,y0}))await setRange(host,key,value);
            const qx=1-alpha,qy=1-alpha*kappa,rho=Math.max(Math.abs(qx),Math.abs(qy));
            const x=x0*qx**n,y=y0*qy**n,f0=(x0*x0+kappa*y0*y0)/2,fn=(x*x+kappa*y*y)/2;
            const all=rho<1?'contracting':rho===1?'boundary':'unstable';
            const converges=(x0===0||Math.abs(qx)<1)&&(y0===0||Math.abs(qy)<1);
            await expect('factors',[qx,qy],'gradient-independent-factors');
            await expect('final',[x,y],'gradient-closed-form');
            await expect('rho',rho,'gradient-operator-factor');
            await expect('criticalAlpha',2/kappa,'gradient-critical-step');
            await expect('contractsAll',alpha>0&&alpha<2/kappa,'gradient-all-starts-condition');
            await expect('allInitialState',all,'gradient-worst-case');
            await expect('trajectoryConverges',converges,'gradient-special-initial-state');
            await expect('initialObjective',f0,'gradient-initial-objective');
            await expect('objective',fn,'gradient-closed-objective');
            await expect('objectiveRatio',f0===0?null:fn/f0,'gradient-zero-ratio');
            await expect('iterations',n,'gradient-finite-steps');
            await defined('gradient-finite-and-asymptotic','defined');
          }
        } else if(chapter.lab==='opt-projection'){
          for(const kind of ['disk','box'])for(const [x,y,radius] of [[0,0,1],[1,0,1],[2,2,.5],[-2,0,1.5],[.25,.25,1]]){
            await host.locator('select[data-key="kind"]').selectOption(kind);
            for(const [key,value] of Object.entries({x,y,radius}))await setRange(host,key,value);
            const norm=Math.hypot(x,y),q=kind==='disk'?(norm<=radius?[x,y]:[radius*x/norm,radius*y/norm])
              :[Math.max(-radius,Math.min(radius,x)),Math.max(-radius,Math.min(radius,y))];
            const residual=[x-q[0],y-q[1]],distance=Math.hypot(...residual);
            await expect('projected',q,'projection-closest-point');
            await expect('residual',residual,'projection-residual');
            await expect('distance',distance,'projection-distance');
            await expect('objective',distance*distance/2,'projection-squared-distance');
            await expect('residualUnit',distance===0?null:residual.map(v=>v/distance),'projection-zero-direction');
            const support=kind==='disk'?radius*Math.hypot(...residual):radius*(Math.abs(residual[0])+Math.abs(residual[1]));
            const maximum=support-residual[0]*q[0]-residual[1]*q[1];
            check(maximum<=1e-10,'projection-support-variational-inequality',{kind,x,y,radius,maximum},current);
            await defined('projection-inside-boundary-outside','defined');
          }
        } else if(chapter.lab==='opt-kkt'){
          for(const [a,b,lambda] of [[0,1,0],[0,1,1],[0,1,4],[1,0,0],[1,0,1],[0,0,0],[-2,1.5,3.5],[2,-1.5,4],[.1,.3,.2],[-2,-1.4,.6],[-.1,.2,.3],[1.5,1.5,0]]){
            for(const [key,value] of Object.entries({a,b,lambda}))await setRange(host,key,value);
            const delta=b-a,xStar=Math.max(a,b),lambdaStar=Math.max(delta,0),primal=lambdaStar*lambdaStar/2;
            const dual=lambda*delta-lambda*lambda/2,gap=delta>=0?(lambda-delta)**2/2:lambda*lambda/2-delta*lambda;
            const stationarity=xStar-a-lambda,gValue=b-xStar,slack=xStar-b,comp=lambda*gValue;
            await expect('xStar',xStar,'KKT-primal-optimum');
            await expect('lambdaStar',lambdaStar,'KKT-optimal-multiplier');
            await expect('primalOptimal',primal,'KKT-primal-value');
            await expect('dualValue',dual,'KKT-independent-Lagrangian-infimum');
            await expect('dualGap',gap,'KKT-stable-gap-formula');
            await expect('stationarity',stationarity,'KKT-stationarity');
            await expect('gValue',gValue,'KKT-inequality-sign');
            await expect('slack',slack,'KKT-positive-slack');
            await expect('complementarity',comp,'KKT-multiplier-times-g');
            await expect('active',xStar===b,'KKT-active-not-positive-multiplier');
            await expect('kktSatisfied',stationarity===0&&comp===0,'KKT-computed-residual-zero');
            check((await read('dualGap'))>=0,'KKT-weak-duality',null,current);
            if(a===.1&&b===.3&&lambda===.2)check((await read('dualGap'))>0&&(await read('stationarity'))!==0,'KKT-retains-tiny-nonzero',null,current);
            const gridOptimal=Math.round(lambda*10)===Math.max(Math.round(b*10)-Math.round(a*10),0);
            const status=await host.locator('.lab-status').innerText();
            if(gridOptimal&&(stationarity!==0||comp!==0))check(status.includes('丸め')&&status.includes('最適乗数'),'KKT-exact-tenths-vs-computed-rounding',{a,b,lambda,status},current);
            if(!gridOptimal)check(status.includes('最適乗数と異なり'),'KKT-genuine-multiplier-mismatch',{a,b,lambda,status},current);
            await defined('KKT-feasible-dual-certificate','defined');
          }
        }

        if(chapter.lab==='linear-core-map'){
          const cases=[
            [.5,1,1,1,1,1],[0,0,2,-2,2,-2],[-2,2,1,-1,-2,2],
            [1,1,1,-1,1,1],[1,1,2,2,1,-1],[-1,-1,-1,1,1,-1],
            [-2,-.5,2,-2,.5,-1],[-2,-.5,0,0,.5,1],
            [.5,2,-2,1,2,1],[2,.5,1,1,.5,1],[.25,2,0,-2,-1,2]];
          for(const [s,t,x,y,b1,b2] of cases){
            for(const [key,value] of Object.entries({s,t,x,y,b1,b2}))await setRange(host,key,value);
            const det=1-s*t,rank=det===0?1:2;
            const kind=det!==0?'unique':b2===s*b1?'infinite':'none';
            const solution=kind==='unique'?[(b1-t*b2)/det,(b2-s*b1)/det]:kind==='infinite'?[b1,0]:null;
            await expect('matrix',[[1,t],[s,1]],'map-matrix');
            await expect('columns',[[1,s],[t,1]],'map-basis-images');
            await expect('transformed',[x+t*y,s*x+y],'map-linear-combination');
            await expect('determinant',det,'map-exact-dyadic-determinant');
            await expect('rank',rank,'map-nonzero-diagonal-no-rank-zero');
            await expect('solutionKind',kind,'map-consistency-classification');
            await expect('representativeSolution',solution,'map-Cramer-or-affine-solution');
            await expect('kernelDirection',rank===1?[-t,1]:null,'map-null-direction');
            if(solution)check(close([solution[0]+t*solution[1],s*solution[0]+solution[1]],[b1,b2]),'map-substitution',{solution,b1,b2},current);
            await defined('map-invertible-singular','defined');
          }
        } else if(chapter.lab==='linear-core-least-squares'){
          for(const [y0,y1,y2] of [[0,0,0],[-2,0,2],[1,0,2],[2,-2,2],[.25,.5,.75],[-2,-2,-2]]){
            for(const [deltaA,deltaB] of [[0,0],[1,0],[0,-1],[-.25,.75]]){
              for(const [key,value] of Object.entries({y0,y1,y2,deltaA,deltaB}))await setRange(host,key,value);
              const d=y0-2*y1+y2,residual=[d/6,-d/3,d/6],observed=[y0,y1,y2];
              const fitted=observed.map((v,i)=>v-residual[i]),a=fitted[1],b=(fitted[2]-fitted[0])/2,sse=d*d/6;
              const ca=a+deltaA,cb=b+deltaB,cf=[ca-cb,ca,ca+cb],csse=observed.reduce((z,v,i)=>z+(v-cf[i])**2,0),excess=3*deltaA**2+2*deltaB**2;
              await expect('observed',observed,'least-squares-observations');
              await expect('a',a,'least-squares-orthogonal-decomposition');
              await expect('b',b,'least-squares-odd-component');
              await expect('fitted',fitted,'least-squares-independent-second-difference');
              await expect('residual',residual,'least-squares-discrete-curvature');
              await expect('normalResiduals',[0,0],'least-squares-normal-equations-tolerance');
              if(y0===2&&y1===-2&&y2===2)check((await read('normalResiduals'))[0]!==0,'least-squares-retains-computed-tiny-residual',null,current);
              await expect('sse',sse,'least-squares-independent-minimum-SSE');
              await expect('candidateA',ca,'least-squares-candidate-intercept');
              await expect('candidateB',cb,'least-squares-candidate-slope');
              await expect('candidateFitted',cf,'least-squares-candidate-fit');
              await expect('candidateSSE',csse,'least-squares-direct-candidate-error');
              await expect('excess',excess,'least-squares-stable-excess');
              const obsNorm=observed.reduce((z,v)=>z+v*v,0),fitNorm=fitted.reduce((z,v)=>z+v*v,0);
              await expect('observedNormSquared',obsNorm,'least-squares-data-norm');
              await expect('fitNormSquared',fitNorm,'least-squares-prediction-norm');
              await expect('pythagoreanResidual',0,'least-squares-Pythagoras-tolerance');
              check(Math.abs(csse-sse-excess)<1e-10,'least-squares-excess-identity',{csse,sse,excess},current);
              await defined('least-squares-exact-and-inconsistent-data','defined');
            }
          }
        } else if(chapter.lab==='linear-core-spectral'){
          for(const [lambda1,lambda2] of [[2,.5],[1,1],[0,0],[0,2],[0,-2],[-1,-2],[2,-2],[-2,2]]){
            for(const theta of [0,15,45,90,180]){
              const x=theta===90?0:1,y=theta===180?-2:1;
              for(const [key,value] of Object.entries({lambda1,lambda2,theta,x,y}))await setRange(host,key,value);
              const rad=theta*Math.PI/180,c=theta===0?1:theta===90?0:theta===180?-1:Math.cos(rad),s=theta===0||theta===180?0:theta===90?1:Math.sin(rad);
              const u=[c,s],v=[-s,c],a=lambda1*c*c+lambda2*s*s,d=lambda1*s*s+lambda2*c*c,off=(lambda1-lambda2)*s*c;
              const transformed=[a*x+off*y,off*x+d*y],rank=Number(lambda1!==0)+Number(lambda2!==0);
              const form=lambda1===0&&lambda2===0?'zero':lambda1>0&&lambda2>0?'positive-definite':lambda1<0&&lambda2<0?'negative-definite':lambda1*lambda2<0?'indefinite':lambda1>=0&&lambda2>=0?'positive-semidefinite':'negative-semidefinite';
              await expect('matrix',[[a,off],[off,d]],'spectral-independent-outer-products');
              await expect('eigenvalues',[lambda1,lambda2],'spectral-unsorted-construction-labels');
              await expect('directions',[u,v],'spectral-chosen-orthonormal-directions');
              await expect('transformed',transformed,'spectral-matrix-action');
              await expect('quadraticForm',x*transformed[0]+y*transformed[1],'spectral-quadratic-form');
              await expect('trace',lambda1+lambda2,'spectral-model-trace');
              await expect('determinant',lambda1*lambda2,'spectral-model-determinant');
              await expect('rank',rank,'spectral-exact-model-rank');
              await expect('formKind',form,'spectral-sign-classification');
              await expect('repeatedEigenvalue',lambda1===lambda2,'spectral-repeated-eigenvalue');
              await expect('eigenDirectionsUnique',lambda1!==lambda2,'spectral-directions-as-lines');
              await expect('singularValues',[Math.max(Math.abs(lambda1),Math.abs(lambda2)),Math.min(Math.abs(lambda1),Math.abs(lambda2))],'spectral-sorted-singular-values');
              await expect('singularDirectionsUnique',Math.abs(lambda1)!==Math.abs(lambda2),'spectral-absolute-eigenvalue-tie');
              if(lambda1===lambda2)check(JSON.stringify(await read('matrix'))===JSON.stringify([[lambda1,0],[0,lambda1]]),'spectral-repeated-exact-scalar',null,current);
              await defined('spectral-positive-negative-zero-repeated','defined');
            }
          }
        }
        await reset.click();
        check(JSON.stringify(await snapshot(host))===JSON.stringify(initial),'vector-numerical-lab-final-reset',chapter.lab,current);
      }
      report.interactions.push({ kind: 'lab-complete', lab: chapter.lab, page: chapter.slug + '.html', controls: initial.values.length, exactReset: true });
    });
    await section('no-javascript', async () => {
      const nojs = await context({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
      const staticPage = await nojs.newPage();
      let exerciseCount = 0, answerCount = 0;
      for (const name of known) {
        current = { page: name };
        await staticPage.goto(origin + '/' + name, { waitUntil: 'load' });
        const record = await staticPage.evaluate(() => ({ page: location.pathname.slice(1), h1: document.querySelector('h1')?.innerText,
          bodyLength: document.querySelector('main')?.innerText.length, exercises: document.querySelectorAll('article.exercise').length,
          answers: [...document.querySelectorAll('article.exercise details')].filter(element => element.querySelector('summary')?.textContent === '解答').length,
          noscripts: [...document.querySelectorAll('main noscript')].map(element => element.innerText),
          mathCount: document.querySelectorAll('main math').length,
          mathHint: [...document.querySelectorAll('.chapter-header .math-scroll-hint')].map(element => ({
            text: element.textContent.trim(), visible: element.getBoundingClientRect().width > 0 && element.getBoundingClientRect().height > 0 })),
          labCount: document.querySelectorAll('[data-lab]').length,
          conceptFigures: [...document.querySelectorAll('figure.concept-figure svg')].map(svg => ({ width: svg.getBoundingClientRect().width, height: svg.getBoundingClientRect().height, title: svg.querySelector('title')?.textContent })),
          conceptTables: [...document.querySelectorAll('table.concept-table')].map(table => ({ width: table.getBoundingClientRect().width, caption: table.caption?.textContent.trim() })) }));
        check(!!record.h1 && record.bodyLength > 150, 'nojs-readable-body', record, current);
        check(record.answers === record.exercises, 'nojs-answers-present', record, current);
        check(record.labCount === 0 || record.noscripts.length >= record.labCount && record.noscripts.every(text => text.trim().length > 20), 'nojs-lab-fallback', record, current);
        if (record.mathCount > 0) check(record.mathHint.length === 1 && record.mathHint[0].visible && record.mathHint[0].text === mathScrollHintText,
          'nojs-math-scroll-hint-visible', record.mathHint, current);
        if (name !== 'index.html') {
          check(record.conceptFigures.length + record.conceptTables.length > 0
            && record.conceptFigures.every(v => v.width > 0 && v.height > 0 && v.title)
            && record.conceptTables.every(v => v.width > 0 && v.caption), 'nojs-concepts-readable', record, current);
          const menu = staticPage.locator('details.section-menu');
          const summary = menu.locator(':scope > summary');
          const nav = staticPage.getByRole('navigation', { name: 'この章の目次', exact: true });
          const nativeOpen = await menu.count() === 1 && await menu.getAttribute('open') !== null;
          const readable = await summary.isVisible() && await nav.isVisible() && await nav.locator('a').count() > 0;
          check(nativeOpen && readable, 'nojs-native-section-menu-open-readable', { nativeOpen, readable }, current);
          await summary.click();
          check(await menu.getAttribute('open') === null && !await nav.isVisible(), 'nojs-section-menu-native-close', null, current);
          await summary.click();
          check(await menu.getAttribute('open') !== null && await nav.isVisible(), 'nojs-section-menu-native-open', null, current);
          record.sectionMenu = { nativeOpen, readable, nativeToggle: true };
        }
        const answers = staticPage.locator('article.exercise details').filter({ has: staticPage.locator('summary', { hasText: /^解答$/ }) });
        for (let index = 0; index < await answers.count(); index++) {
          await answers.nth(index).locator('summary').click();
          check((await answers.nth(index).innerText()).length > 10, 'nojs-answer-open-readable', index, current);
        }
        exerciseCount += record.exercises; answerCount += record.answers; report.noJavaScript.push(record);
      }
      check(exerciseCount === catalog.chapters.length * 3 && answerCount === catalog.chapters.length * 3, 'nojs-all-exercises-and-answers', { exerciseCount, answerCount });
      await staticPage.setViewportSize({ width: 320, height: 900 });
      current = { page: 'gradient.html' };
      await staticPage.goto(origin + '/gradient.html', { waitUntil: 'load' });
      const resizeSteps = [];
      for (const selector of ['.chapter-menu', '.section-menu']) {
        const menu = staticPage.locator(selector);
        await menu.locator(':scope > summary').click();
        check(await menu.getAttribute('open') === null, 'nojs-320-menu-closed-before-resize', selector, current);
      }
      await staticPage.setViewportSize({ width: 1280, height: 900 });
      for (const selector of ['.chapter-menu', '.section-menu']) {
        const menu = staticPage.locator(selector), summary = menu.locator(':scope > summary');
        const visibleSummary = await summary.isVisible();
        check(visibleSummary && await menu.getAttribute('open') === null, 'nojs-wide-closed-menu-summary-visible', selector, current);
        await summary.focus(); await summary.press('Enter');
        const reopened = await menu.getAttribute('open') !== null && await menu.locator('nav').isVisible();
        check(reopened, 'nojs-wide-menu-can-reopen', selector, current);
        resizeSteps.push({ selector, closedAt320: true, wideSummaryVisible: visibleSummary, reopened });
      }
      report.interactions.push({ kind: 'nojs-menu-resize', page: 'gradient.html', widths: [320, 1280], reloadsBetweenWidths: 0, steps: resizeSteps });
      await nojs.close();
    });
    await section('representative-screenshots', async () => {
      async function shot(name, width, theme, filename, selector, openSectionMenu = false) {
        await page.setViewportSize({ width, height: 900 }); await go(name);
        await page.locator('#theme-select').selectOption(theme);
        if (openSectionMenu) {
          const summary = page.locator('details.section-menu > summary');
          await summary.focus(); await summary.press('Enter');
          check(await page.getByRole('navigation', { name: 'この章の目次', exact: true }).isVisible(), 'screenshot-mobile-section-menu-open', null, current);
          const headerBottom = await page.locator('.chapter-header').evaluate(element => Math.ceil(element.getBoundingClientRect().bottom));
          await page.setViewportSize({ width, height: Math.max(900, headerBottom + 40) });
        }
        await page.evaluate(() => document.activeElement?.blur());
        const file = path.join(config.output, filename);
        if (selector) {
          // Avoid Chromium's captureBeyondViewport compositing of offscreen fixed links.
          // A taller viewport fits the target without changing its width or its DOM/CSS.
          const target = page.locator(selector);
          const height = await target.evaluate(element => Math.ceil(element.getBoundingClientRect().height));
          await page.setViewportSize({ width, height: Math.max(900, height + 80) });
          if (name === 'taylor.html') {
            // Native block MathML is the inner scroll container; the wrapper can fit.
            const formula = page.locator('#taylor-remainder .formula math');
            const measure = element => {
              const box = element.getBoundingClientRect();
              const leaves = [...element.querySelectorAll('*')].filter(child => !child.children.length);
              const tail = leaves.at(-1).getBoundingClientRect();
              return { scrollLeft: element.scrollLeft, maxScroll: element.scrollWidth - element.clientWidth,
                clientWidth: element.clientWidth, scrollWidth: element.scrollWidth,
                formulaRight: box.right, tailLeft: tail.left, tailRight: tail.right,
                viewportWidth: innerWidth, pageScrollWidth: document.documentElement.scrollWidth };
            };
            const before = await formula.evaluate(measure);
            check(before.maxScroll > 0 && before.scrollLeft === 0, 'long-mathml-local-overflow', before, current);
            await formula.hover();
            await page.mouse.wheel(2400, 0);
            await page.waitForFunction(() => {
              const element = document.querySelector('#taylor-remainder .formula math');
              return element.scrollLeft > 0 && element.scrollLeft >= element.scrollWidth - element.clientWidth - 1;
            });
            const after = await formula.evaluate(measure);
            check(after.scrollLeft > before.scrollLeft && Math.abs(after.maxScroll - after.scrollLeft) <= 1
              && after.tailRight <= after.formulaRight + 1, 'long-mathml-wheel-reaches-tail', after, current);
            check(before.pageScrollWidth <= width + 1 && after.pageScrollWidth <= width + 1, 'long-mathml-scroll-keeps-page-width', { before, after }, current);
            report.interactions.push({ kind: 'mathml-horizontal-scroll', page: name, width, theme,
              input: 'real mouse.wheel(2400, 0); no scrollLeft assignment', before, after });
          }
          await target.screenshot({ path: file });
        }
        else await page.screenshot({ path: file });
        const metadata = await page.evaluate(() => ({ scrollY, viewportHeight: innerHeight,
          focused: document.activeElement?.tagName, skipLinkTop: document.querySelector('.skip-link').getBoundingClientRect().top }));
        report.screenshots.push({ file, page: name, width, theme, selector: selector || 'viewport', openSectionMenu, ...metadata });
      }
      await shot('index.html', 1280, 'light', '01-index-desktop.png');
      await shot('invariants.html', 320, 'light', '02-static-board-320.png', '#invariants-board figure');
      for (const [index, name] of ['gradient', 'hessian-extrema', 'lagrange', 'double-integrals', 'change-of-variables'].entries()) {
        await shot(name + '.html', 320, index % 2 ? 'dark' : 'light', `${index + 3}-${name}-320.png`, '[data-lab]');
      }
      await shot('taylor.html', 390, 'dark', '08-mathml-390-dark.png', '#taylor-remainder');
      await shot('integration.html', 1280, 'light', '09-integration-bounds-1280.png', '[data-lab]');
      await shot('double-integrals.html', 1280, 'dark', '10-double-integral-bounds-1280.png', '[data-lab]');
      await shot('gradient.html', 320, 'light', '11-section-menu-open-320.png', undefined, true);
      for (const [index, name] of ['conditional-probability', 'independence', 'random-variables', 'probability-density', 'law-of-large-numbers'].entries()) {
        await shot(name + '.html', 320, index % 2 ? 'dark' : 'light', (index + 12) + '-' + name + '-320.png', '[data-lab]');
      }
      for (const [index, name] of ['modular-arithmetic', 'recurrence-relations', 'shortest-paths'].entries()) {
        await shot(name + '.html', 320, index % 2 ? 'dark' : 'light', (index + 17) + '-' + name + '-320.png', '[data-lab]');
      }
      for (const [index, name] of ['complex-differentiation', 'complex-logarithm', 'complex-residues'].entries()) {
        await shot(name + '.html', 320, index % 2 ? 'dark' : 'light', (index + 20) + '-' + name + '-320.png', '[data-lab]');
      }
      for (const [index, name] of ['vector-line-integrals','vector-flux','vector-stokes','numerical-bisection','numerical-differentiation','numerical-ode'].entries()) {
        await shot(name + '.html',320,index % 2 ? 'dark' : 'light',(index+23)+'-'+name+'-320.png','[data-lab]');
      }
      for(const [index,name]of ['optimization-gradient','optimization-projections','optimization-kkt'].entries()){
        await shot(name+'.html',320,index%2?'dark':'light',(index+29)+'-'+name+'-320.png','[data-lab]');
      }
      for(const [index,name]of ['linear-elimination','linear-least-squares','linear-symmetric'].entries()){
        await shot(name+'.html',320,index%2?'dark':'light',(index+32)+'-'+name+'-320.png','[data-lab]');
      }
    });
    await section('concept-screenshots-and-table-scroll', async () => {
      const directory = path.join(config.output, 'concepts'); await fs.mkdir(directory, { recursive: true });
      for (const theme of ['light', 'dark']) for (const chapter of catalog.chapters) {
        await page.setViewportSize({ width: 320, height: 900 }); await go(chapter.slug + '.html');
        await page.locator('#theme-select').selectOption(theme);
        const figures = page.locator('figure.concept-figure');
        async function capture(target, key, kind, edge = 'whole') {
          const height = await target.evaluate(element => Math.ceil(element.getBoundingClientRect().height));
          await page.setViewportSize({ width: 320, height: Math.max(900, height + 80) });
          await page.evaluate(() => document.activeElement?.blur());
          const name = key.replace(/[^a-zA-Z0-9-]/g, '-') + '-' + theme + (edge === 'whole' ? '' : '-' + edge) + '.png';
          const file = path.join(directory, name);
          await target.screenshot({ path: file });
          report.conceptScreenshots.push({ file, page: chapter.slug + '.html', key, kind, edge, width: 320, theme });
        }
        for (let index = 0; index < await figures.count(); index++) {
          const target = figures.nth(index), key = await target.getAttribute('data-visual');
          await capture(target, key, 'figure');
        }
        const tables = page.locator('table.concept-table:not([data-lab] table)');
        for (let index = 0; index < await tables.count(); index++) {
          const table = tables.nth(index), key = await table.getAttribute('data-visual');
          const wrapper = table.locator('..');
          await capture(wrapper, key, 'table', 'left');
          const start = await wrapper.evaluate(element => ({ left: element.scrollLeft, max: element.scrollWidth - element.clientWidth }));
          if (start.max > 1) {
            await wrapper.focus(); await wrapper.press('ArrowRight');
            await page.waitForFunction(element => element.scrollLeft > 0, await wrapper.elementHandle());
            const keyboard = await wrapper.evaluate(element => element.scrollLeft);
            await page.waitForTimeout(200); // Let the native key scroll animation settle before a wheel input.
            check(keyboard > 0, 'concept-table-keyboard-scroll', { key, keyboard }, current);
            await wrapper.hover(); await page.mouse.wheel(5000, 0);
            await page.waitForFunction(element => element.scrollLeft >= element.scrollWidth - element.clientWidth - 1, await wrapper.elementHandle());
            const end = await wrapper.evaluate(element => {
              const caption = element.querySelector('caption').getBoundingClientRect(), box = element.getBoundingClientRect();
              return { left: element.scrollLeft, max: element.scrollWidth - element.clientWidth,
                captionVisible: caption.left >= box.left - 1 && caption.right <= box.right + 1,
                focused: document.activeElement === element };
            });
            check(end.left >= end.max - 1, 'concept-table-scroll-reaches-end', { key, end }, current);
            check(end.captionVisible && end.focused, 'concept-table-caption-and-focus-after-scroll', { key, end }, current);
            report.interactions.push({ kind: 'concept-table-scroll', page: chapter.slug + '.html', key, theme, keyboard, ...end });
            await capture(wrapper, key, 'table', 'right');
          }
        }
      }
      console.log('Concept screenshots: ' + report.conceptScreenshots.length);
    });
    check(report.states.length === expectedStates, 'complete-all-page-states', report.states.length);
    check(report.interactions.filter(item => item.kind === 'chapter-ui').length === catalog.chapters.length, 'complete-all-chapter-ui', null);
    check(report.interactions.filter(item => item.kind === 'section-menu-ui').length === catalog.chapters.length * 2, 'complete-all-mobile-section-menus', null);
    check(report.interactions.filter(item => item.kind === 'responsive-menu-resize').length === 1, 'complete-responsive-menu-resize', null);
    check(report.interactions.filter(item => item.kind === 'nojs-menu-resize').length === 1, 'complete-nojs-menu-resize', null);
    check(report.interactions.filter(item => item.kind === 'lab-complete').length === expectedLabs, 'complete-all-labs', null);
    check(report.noJavaScript.length === known.size, 'complete-all-nojs-pages', report.noJavaScript.length);
    check(report.screenshots.length === 34, 'complete-34-screenshots', report.screenshots.length);
    check(report.noJavaScript.reduce((sum, item) => sum + item.conceptFigures.length, 0) === expectedFigures, 'complete-nojs-all-concept-figures', null);
    check(report.noJavaScript.reduce((sum, item) => sum + item.conceptTables.length, 0) === expectedTables, 'complete-nojs-all-concept-tables', null);
    check(report.conceptScreenshots.filter(item => item.kind === 'figure').length === expectedFigures * 2, 'complete-all-concept-figure-shots', null);
    check(report.conceptScreenshots.filter(item => item.kind === 'table' && item.edge === 'left').length === expectedTables * 2, 'complete-all-concept-table-shots', null);
    await ctx.close();
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise(resolve => server.close(resolve));
    report.finishedAt = new Date().toISOString();
    report.status = report.harnessErrors.length ? 'incomplete' : 'finished';
    report.summary = { states: report.states.length, checks: report.checks, failures: report.failures.length,
      candidates: report.candidates.length, harnessErrors: report.harnessErrors.length, console: report.console.length,
      pageErrors: report.pageErrors.length, requestFailures: report.requestFailures.length, httpErrors: report.httpErrors.length,
      blockedRequests: report.blockedRequests.length, labs: report.interactions.filter(item => item.kind === 'lab-complete').length,
      noJavaScriptPages: report.noJavaScript.length, screenshots: report.screenshots.length, conceptScreenshots: report.conceptScreenshots.length };
    const file = path.join(config.output, 'browser-qa.json');
    await fs.writeFile(file, JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report.summary));
    console.log('Report: ' + displayPath(file));
    for (const item of report.screenshots) console.log('PNG: ' + displayPath(item.file));
    if (report.failures.length || report.harnessErrors.length || report.pageErrors.length || report.blockedRequests.length
      || report.httpErrors.length || report.requestFailures.length || report.console.some(event => event.type === 'error')) process.exitCode = 1;
  }
}

if (process.argv.includes('--self-test')) selfTest();
else main(options()).catch(error => { console.error(errorText(error)); process.exitCode = 2; });
