// Shared-runtime browser check: open every built Book notebook page offline and
// confirm that MathJax typesets locally (scripts/shared_runtime.py).
// Usage: CHROMIUM_BIN=<chrome> PLAYWRIGHT_MODULE=<playwright-core dir> \
//   node johnhull/scripts/check_book_math.cjs johnhull/book/_build/html
// Prints one JSON row per page; exits 1 if any page has no MathJax, an
// untypeset or erroneous formula, an external request, or a page error.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const root = path.resolve(process.argv[2]);
  const pages = fs.readdirSync(path.join(root, 'notebooks')).filter(n => n.endsWith('.html')).sort();
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN });
  const results = [];
  for (const name of pages) {
    const page = await browser.newPage();
    const external = [], errors = [];
    page.on('request', r => { if (!r.url().startsWith('file://') && !r.url().startsWith('data:')) external.push(r.url()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('file://' + path.join(root, 'notebooks', name), { waitUntil: 'load' });
    const info = await page.evaluate(async () => {
      if (!window.MathJax || !MathJax.startup) return { mathjax: false };
      await MathJax.startup.promise;
      return {
        mathjax: true,
        version: MathJax.version,
        rendered: document.querySelectorAll('mjx-container').length,
        merror: document.querySelectorAll('mjx-merror, .merror').length,
        raw: document.querySelectorAll('.math:not(:has(mjx-container))').length,
      };
    });
    results.push({ name, ...info, external: external.length, errors: errors.length });
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(results));
  const bad = results.filter(r => !r.mathjax || r.merror || r.raw || r.external || r.errors);
  if (bad.length) {
    console.error(`FAIL: ${bad.map(r => r.name).join(', ')}`);
    process.exit(1);
  }
})().catch(e => { console.error(e); process.exit(1); });
