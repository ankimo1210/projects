'use strict';

// Optional integration check: native MathML in a standalone file, NoJS and print.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const crypto = require('node:crypto');
const options = {};
for (let i = 2; i < process.argv.length; i += 2) {
  assert(['--module', '--browser', '--site', '--output'].includes(process.argv[i]) && process.argv[i + 1],
    'Use --module PATH --browser PATH [--site PATH] --output PATH');
  options[process.argv[i].slice(2)] = process.argv[i + 1];
}
assert(options.module && options.browser && options.output, 'Existing Playwright, Chromium and an output directory are required.');
const site = path.resolve(options.site || path.join(__dirname, '../site'));
const output = path.resolve(options.output);
const displayPath = value => value.replaceAll('/home/kazumasa/projects/', '\\\\wsl.localhost\\Ubuntu\\home\\kazumasa\\projects\\');

async function main() {
  await fs.mkdir(output, { recursive: true });
  const browser = await require(options.module).chromium.launch({ executablePath: options.browser, headless: true });
  const failures = [], inputs = {}, screenshots = [], states = [];
  try {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 }, colorScheme: 'light' });
    await context.route('**/*', async route => {
      if (new URL(route.request().url()).protocol === 'file:') await route.continue();
      else { failures.push({ networkProtocol: new URL(route.request().url()).protocol }); await route.abort(); }
    });
    const page = await context.newPage();
    page.on('pageerror', error => failures.push({ pageError: error.message }));
    page.on('console', message => { if (message.type() === 'error') failures.push({ console: message.text() }); });
    const cases = [
      { name: 'linear-eigenvalues.html', mathIndex: 4 },
      { name: 'variance.html', mathIndex: 0 },
      { name: 'joint-distributions.html', mathIndex: 0 },
      { name: 'linear-orthogonality.html', mathIndex: 1 },
      { name: 'discrete-counting.html', mathIndex: 0 },
      { name: 'vector-surfaces.html', mathIndex: 0 },
      { name: 'conditional-probability.html', mathIndex: 0 },
      { name: 'numerical-bisection.html', mathIndex: 0 },
      { name: 'approximation.html', mathIndex: 0 },
    ];
    for (const { name, mathIndex } of cases) {
      const file = path.join(site, name);
      inputs[name] = crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex');
      await page.goto(pathToFileURL(file).href);
      await page.evaluate(() => document.fonts.ready);
      for (const media of ['screen', 'print']) {
        await page.emulateMedia({ media });
        // Switching media invalidates font/layout state; resolve the print layout before checking.
        await page.evaluate(() => { void document.body.offsetHeight; return document.fonts.ready; });
        const state = await page.evaluate(mathIndex => {
          const math = [...document.querySelectorAll('main math')];
          const sample = math[mathIndex];
          const fences = sample ? [...sample.querySelectorAll('mo')].filter(element =>
            ['(', ')', '[', ']', '|', '‖'].includes(element.textContent.trim())).map(element => {
              const box = element.getBoundingClientRect(), em = parseFloat(getComputedStyle(element).fontSize);
              return { token: element.textContent.trim(), heightEm: box.height / em, widthEm: box.width / em };
            }) : [];
          return { fences, status: document.fonts.status, faces: [...document.fonts].map(face => ({family:face.family,status:face.status})), loaded: [...document.fonts].some(face => face.family.replaceAll('"', '') === 'Latin Modern Math' && face.status === 'loaded'),
            count: math.length, families: [...new Set(math.map(element => getComputedStyle(element).fontFamily))],
            invalid: math.some(element => element.getBoundingClientRect().height <= 0 || element.getBoundingClientRect().width <= 0) };
        }, mathIndex);
        assert(state.fences.length > 0 && state.fences.every(fence => fence.heightEm <= 1.5 && fence.widthEm <= 0.65),
          JSON.stringify({name,media,problem:'Simple fences must keep their ordinary glyph size and spacing.',fences:state.fences}));
        assert(state.loaded && state.count > 0 && !state.invalid && state.families.every(family => family.startsWith('"Latin Modern Math"')), JSON.stringify({media,state,failures}));
        states.push({ page: name, protocol: 'file:', javaScriptEnabled: false, media, ...state });
      }
      if (name === 'linear-eigenvalues.html') {
        await page.emulateMedia({ media: 'screen' });
        for (const [id, filename] of [
          ['linear-eigenvalues-population', 'math-font-matrix.png'],
          ['linear-eigenvalues-directions', 'math-font-simple-fences.png'],
        ]) {
          const formula = page.locator('#' + id + ' > .formula').first();
          await formula.screenshot({ path: path.join(output, filename) });
          screenshots.push(filename);
        }
      }
    }
    assert.deepEqual(failures, []);
  } finally { await browser.close(); }
  const report = { status: 'passed', inputs, states, screenshots, failures,
    scope: 'Standalone file:// pages, JavaScript disabled, native screen and print rendering; not a physical printout.' };
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'passed', states: states.length, screenshots, networkRequests: 0 }));
}
main().catch(error => { console.error(displayPath(error.stack || String(error))); process.exitCode = 1; });
