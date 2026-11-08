'use strict';

// No dependencies or browsers are installed. Pass the existing Playwright
// module and Chromium, as for browser_qa.cjs. This supplements, not replaces,
// layout QA: candidates still require a human visual adjudication.
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const displayPath = value => process.platform === 'linux' && value.startsWith('/home/')
  ? '\\\\wsl.localhost\\Ubuntu' + value.replaceAll('/', '\\') : value;
const safeError = error => String(error.stack || error).replaceAll('/home/kazumasa/projects/', '\\\\wsl.localhost\\Ubuntu\\home\\kazumasa\\projects\\');

function options() {
  const values = {}, flags = new Set();
  for (let i = 2; i < process.argv.length; i++) {
    const key = process.argv[i];
    if (key === '--self-test') { flags.add(key); continue; }
    if (!['--module', '--browser', '--site', '--output', '--pages', '--width', '--theme'].includes(key) || !process.argv[i + 1]) {
      throw new Error('Use --module PATH --browser PATH [--site DIRECTORY] [--output DIRECTORY] [--pages slug1,slug2] [--width 1280] [--theme light|dark] [--self-test].');
    }
    values[key.slice(2)] = process.argv[++i];
  }
  const width = Number(values.width || process.env.MATH_QA_WIDTH || 1280);
  const theme = values.theme || process.env.MATH_QA_THEME || 'light';
  if (!Number.isInteger(width) || width < 240 || width > 4096) throw new RangeError('Width must be an integer from 240 through 4096.');
  if (!['light', 'dark'].includes(theme)) throw new RangeError('Theme must be light or dark.');
  const pages = values.pages ? values.pages.split(',').map(value => value.endsWith('.html') ? value : value + '.html') : null;
  if (pages && pages.some(value => !/^[a-z0-9-]+\.html$/.test(value))) throw new Error('Each page must be a local slug or HTML basename.');
  return {
    module: values.module || process.env.MATH_QA_MODULE,
    browser: values.browser || process.env.MATH_QA_BROWSER,
    site: path.resolve(values.site || process.env.MATH_QA_SITE || path.join(__dirname, '../site')),
    output: path.resolve(values.output || process.env.MATH_QA_OUTPUT || path.join(__dirname, '../../../_data/math-foundations/figure-messages-2026-11-08/ink')),
    pages, width, theme, selfTest: flags.has('--self-test'),
  };
}

// Runs in Chromium. Each layer is an SVG clone with computed font/paint
// styles, rasterized on a transparent Canvas at three pixels per CSS pixel.
// Large fills are omitted as ink but preserve occlusion of strokes behind
// them; outlines and small filled markers/arrowheads remain. Only summary
// counts leave the browser.
async function detectInk(svg) {
  const density = 3, alphaThreshold = 48;
  const bounds = svg.getBoundingClientRect();
  if (!(bounds.width > 0 && bounds.height > 0)) throw new Error('SVG has no visible area.');
  const width = Math.max(1, Math.ceil(bounds.width * density)), height = Math.max(1, Math.ceil(bounds.height * density));
  if (width * height > 24000000) throw new Error('SVG exceeds the in-memory raster cap (24 million pixels).');
  const properties = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray', 'stroke-dashoffset',
    'stroke-linecap', 'stroke-linejoin', 'paint-order', 'font-family', 'font-size', 'font-weight', 'font-style', 'font-variant',
    'font-stretch', 'letter-spacing', 'word-spacing', 'text-anchor', 'dominant-baseline', 'alignment-baseline', 'opacity', 'color', 'visibility', 'display'];
  const original = [svg, ...svg.querySelectorAll('*')];
  const boxes = [...svg.querySelectorAll('text')].map((text, index) => {
    const r = text.getBoundingClientRect();
    return { index, text: text.textContent, x: r.x - bounds.x, y: r.y - bounds.y, width: r.width, height: r.height };
  });
  function cloneLayer(mode) {
    const clone = svg.cloneNode(true), nodes = [clone, ...clone.querySelectorAll('*')];
    original.forEach((node, i) => {
      const style = getComputedStyle(node), target = nodes[i];
      properties.forEach(property => target.style.setProperty(property, style.getPropertyValue(property)));
      const tag = node.localName;
      if (mode === 'text' && ['line', 'path', 'circle', 'ellipse', 'rect', 'polyline', 'polygon', 'image', 'use', 'foreignObject'].includes(tag)) {
        target.style.setProperty('visibility', 'hidden', 'important');
      }
      if (mode === 'geometry') {
        if (node.closest('text')) target.style.setProperty('visibility', 'hidden', 'important');
        if (style.stroke !== 'none') target.style.setProperty('stroke', 'rgb(0,0,0)', 'important');
        if (['circle', 'ellipse', 'rect', 'path', 'polygon', 'polyline'].includes(tag)) {
          let small = false;
          try { const b = node.getBBox(); small = b.width <= 24 && b.height <= 24 && b.width > 0 && b.height > 0; } catch (_) { /* no shape bbox */ }
          // White areas do not count as geometric ink, but preserve the
          // occlusion of a stroke behind a filled label background.
          if (style.fill !== 'none') target.style.setProperty('fill', small ? 'rgb(0,0,0)' : 'rgb(255,255,255)', 'important');
        }
        if (['image', 'foreignObject'].includes(tag)) target.style.setProperty('visibility', 'hidden', 'important');
      }
    });
    clone.querySelectorAll('script,style').forEach(node => node.remove());
    clone.querySelectorAll('[href]').forEach(node => {
      if (!node.getAttribute('href').startsWith('#')) node.remove();
    });
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', bounds.width); clone.setAttribute('height', bounds.height);
    clone.style.removeProperty('max-width'); clone.style.setProperty('width', bounds.width + 'px'); clone.style.setProperty('height', bounds.height + 'px');
    clone.style.setProperty('background', 'transparent', 'important');
    return new XMLSerializer().serializeToString(clone);
  }
  async function pixels(source) {
    const image = new Image();
    image.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(source)));
    await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = () => reject(new Error('SVG layer could not be rasterized.')); });
    const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(image, 0, 0, width, height);
    return context.getImageData(0, 0, width, height).data;
  }
  const textPixels = await pixels(cloneLayer('text')), geometryPixels = await pixels(cloneLayer('geometry'));
  const hits = boxes.map(() => 0);
  let overlapPixels = 0, textInkPixels = 0, geometryInkPixels = 0;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const index = (y * width + x) * 4 + 3;
    const a = textPixels[index] >= alphaThreshold;
    // Black coverage after compositing white area fills: an opaque label
    // background erases hidden lines without itself becoming a hit.
    const b = geometryPixels[index] * (255 - geometryPixels[index - 3]) / 255 >= alphaThreshold;
    if (a) textInkPixels++; if (b) geometryInkPixels++;
    if (a && b) {
      overlapPixels++;
      const px = (x + .5) / density, py = (y + .5) / density;
      boxes.forEach((box, k) => { if (px >= box.x && px <= box.x + box.width && py >= box.y && py <= box.y + box.height) hits[k]++; });
    }
  }
  return { cssWidth: bounds.width, cssHeight: bounds.height, rasterWidth: width, rasterHeight: height, density, alphaThreshold,
    overlapPixels, textInkPixels, geometryInkPixels, texts: boxes.map((box, i) => ({ ...box, overlapPixels: hits[i] })),
    hits: boxes.flatMap((box, i) => hits[i] ? [{ index: box.index, text: box.text, overlapPixels: hits[i], bbox: { x: box.x, y: box.y, width: box.width, height: box.height } }] : []) };
}

function selfTestHTML() {
  const svg = (id, shape) => '<svg id="' + id + '" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150" style="width:300px;height:150px">'
    + '<text x="90" y="80" style="fill:rgb(0,0,0);font-family:sans-serif;font-size:32px"><tspan>MATH</tspan></text>' + shape + '</svg>';
  return '<!doctype html><html><head><meta charset="utf-8"><title>Ink detector self-test</title></head><body><main>'
    + svg('positive-line', '<line x1="50" y1="70" x2="260" y2="70" stroke="rgb(0,0,0)" stroke-width="4"/>')
    + svg('negative-line', '<line x1="50" y1="115" x2="260" y2="115" stroke="rgb(0,0,0)" stroke-width="4"/>')
    + svg('large-filled-area', '<line x1="50" y1="70" x2="260" y2="70" stroke="rgb(0,0,0)" stroke-width="4"/><rect x="40" y="30" width="230" height="80" fill="rgb(80,80,80)"/>')
    + svg('small-filled-marker', '<circle cx="94" cy="69" r="6" fill="rgb(0,0,0)"/>')
    + '</main></body></html>';
}

async function main(config) {
  if (!config.module || !config.browser) throw new Error('Existing --module and --browser paths are required.');
  const { chromium } = require(path.resolve(config.module));
  await fs.mkdir(config.output, { recursive: true });
  const bytes = new Map();
  if (config.selfTest) bytes.set('ink-self-test.html', Buffer.from(selfTestHTML()));
  else {
    for (const name of (await fs.readdir(config.site)).sort()) if (/^[a-z0-9-]+\.html$/.test(name)) {
      bytes.set(name, await fs.readFile(path.join(config.site, name)));
    }
  }
  if (!bytes.size) throw new Error('No known HTML pages to audit.');
  const selected = config.selfTest ? ['ink-self-test.html'] : config.pages || [...bytes.keys()];
  if (selected.some(name => !bytes.has(name))) throw new Error('A selected page is not in the start-time HTML snapshot.');
  const report = {
    startedAt: new Date().toISOString(), status: 'running', kind: 'SVG text/stroke ink-overlap candidates',
    platform: process.platform, nodeVersion: process.version,
    inputs: { site: config.selfTest ? 'synthetic self-test fixtures' : displayPath(config.site), pageHashes: Object.fromEntries([...bytes].map(([name, data]) => [name, digest(data)])),
      toolHash: digest(await fs.readFile(__filename)), selectedPages: selected, width: config.width, theme: config.theme, deviceScaleFactor: 3 },
    policy: { largeFilledAreasExcluded: true, smallFilledMarkerMaxSVGUnits: 24, alphaThreshold: 48, rasterDensity: 3,
      largeFillsPreserveStrokeOcclusion: true, candidateVerdict: 'unadjudicated; overlap can be intended. Do not call candidates product failures or automatic approval.' },
    figures: [], candidates: [], skipped: [], harnessErrors: [], consoleErrors: [], pageErrors: [], requestFailures: [], blockedRequests: [],
    limitations: ['Initial lab states only; other boundary states remain covered separately by browser QA.',
      'Large area fills are omitted as ink while preserving their stroke occlusion; external images/foreignObject are excluded. Strokes and small filled markers/arrowheads are checked.',
      'Per-text hits use text bounding boxes; overlapping text boxes can attribute one pixel to more than one label.',
      'This detects text versus geometry, not every text-versus-text collision or mathematical/educational defect.',
      'Computed-style SVG clones and system fonts are rasterized in Linux Chromium; visual adjudication uses the original candidate SVG PNG.'],
  };
  const server = http.createServer((request, response) => {
    const name = (request.url || '').split(/[?#]/)[0].slice(1);
    const allowed = ['GET', 'HEAD'].includes(request.method) && /^[a-z0-9-]+\.html$/.test(name) && bytes.has(name);
    response.writeHead(allowed ? 200 : 404, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    response.end(request.method === 'HEAD' ? '' : allowed ? bytes.get(name) : 'Not found');
  });
  let browser, context;
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    const origin = 'http://127.0.0.1:' + server.address().port; report.origin = origin;
    browser = await chromium.launch({ executablePath: config.browser, headless: true, args: ['--no-sandbox', '--disable-background-networking', '--no-first-run'] });
    report.browserVersion = browser.version();
    context = await browser.newContext({ viewport: { width: config.width, height: 1000 }, colorScheme: config.theme, deviceScaleFactor: 3 });
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin === origin) return route.continue();
      report.blockedRequests.push({ url: route.request().url(), reason: 'outside local snapshot origin' });
      return route.abort();
    });
    const page = await context.newPage();
    page.on('console', message => { if (message.type() === 'error') report.consoleErrors.push(message.text()); });
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('requestfailed', request => report.requestFailures.push({ url: request.url(), error: request.failure()?.errorText }));
    for (const name of selected) {
      const response = await page.goto(origin + '/' + name, { waitUntil: 'load' });
      if (response.status() !== 200) throw new Error('Known snapshot page returned ' + response.status());
      await page.evaluate(async theme => { document.documentElement.dataset.theme = theme; await document.fonts.ready; }, config.theme);
      const descriptors = await page.locator('svg').evaluateAll(elements => elements.map((svg, index) => {
        const lab = svg.closest('[data-lab]'), owner = svg.closest('[data-visual],figure');
        return { index, nested: !!svg.parentElement?.closest('svg'), id: svg.id || owner?.dataset.visual || owner?.id || svg.getAttribute('aria-labelledby')?.split(' ')[0] || 'svg-' + index,
          lab: lab?.dataset.lab || null, title: svg.querySelector('title')?.textContent || '', fragment: svg.outerHTML };
      }));
      for (const item of descriptors) {
        if (item.nested) continue;
        const element = page.locator('svg').nth(item.index);
        if (!await element.isVisible()) { report.skipped.push({ page: name, id: item.id, reason: 'SVG hidden in initial state' }); continue; }
        await element.scrollIntoViewIfNeeded();
        const ink = await element.evaluate(detectInk);
        const entry = { page: name, id: item.id, svgIndex: item.index, kind: item.lab ? 'lab' : 'static', lab: item.lab, title: item.title,
          pageHash: report.inputs.pageHashes[name], fragmentHash: digest(item.fragment), ...ink };
        report.figures.push(entry);
        if (ink.overlapPixels > 0) {
          const filename = name.slice(0, -5) + '-svg-' + String(item.index).padStart(2, '0') + '-' + config.width + '-' + config.theme + '.png';
          await element.screenshot({ path: path.join(config.output, filename), animations: 'disabled' });
          report.candidates.push({ page: name, id: item.id, svgIndex: item.index, kind: entry.kind, lab: item.lab, fragmentHash: entry.fragmentHash,
            overlapPixels: ink.overlapPixels, hits: ink.hits, png: filename, verdict: 'unadjudicated' });
        }
      }
    }
    if (config.selfTest) {
      const wants = { 'positive-line': true, 'negative-line': false, 'large-filled-area': false, 'small-filled-marker': true };
      const cases = Object.entries(wants).map(([name, expected]) => ({ name, expected, detected: report.figures.find(entry => entry.id === name)?.overlapPixels > 0 }));
      report.selfTest = { passed: cases.every(entry => entry.detected === entry.expected), cases };
      if (!report.selfTest.passed) report.harnessErrors.push('Detector positive/negative/fill-exclusion/marker self-test failed.');
    }
  } catch (error) {
    report.harnessErrors.push(safeError(error));
  } finally {
    if (context) await context.close().catch(error => report.harnessErrors.push(safeError(error)));
    if (browser) await browser.close().catch(error => report.harnessErrors.push(safeError(error)));
    if (server.listening) await new Promise(resolve => server.close(resolve));
    report.finishedAt = new Date().toISOString(); report.status = report.harnessErrors.length ? 'failed' : 'finished';
    report.summary = { pages: selected.length, figures: report.figures.length, staticSVG: report.figures.filter(entry => entry.kind === 'static').length,
      initialLabSVG: report.figures.filter(entry => entry.kind === 'lab').length, candidates: report.candidates.length,
      overlapPixels: report.figures.reduce((sum, entry) => sum + entry.overlapPixels, 0), skipped: report.skipped.length,
      harnessErrors: report.harnessErrors.length, consoleErrors: report.consoleErrors.length, pageErrors: report.pageErrors.length,
      requestFailures: report.requestFailures.length, blockedRequests: report.blockedRequests.length };
    const filename = config.selfTest ? 'figure-ink-self-test.json' : 'figure-ink-qa-' + config.width + '-' + config.theme + '.json';
    await fs.writeFile(path.join(config.output, filename), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ ...report.summary, selfTestPassed: report.selfTest?.passed }));
    console.log('Report: ' + displayPath(path.join(config.output, filename)));
    if (report.harnessErrors.length || report.consoleErrors.length || report.pageErrors.length || report.requestFailures.length || report.blockedRequests.length) process.exitCode = 1;
  }
}
try { main(options()).catch(error => { console.error(safeError(error)); process.exitCode = 1; }); }
catch (error) { console.error(safeError(error)); process.exitCode = 1; }
