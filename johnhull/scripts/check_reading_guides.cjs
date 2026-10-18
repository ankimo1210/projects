// Re-run from the worktree root after `make hull-book`.
// source /home/kazumasa/projects/_data/johnhull/reading-guide/env.sh
// node johnhull/scripts/check_reading_guides.cjs
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL, fileURLToPath } = require('node:url');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const modulePath = process.env.PLAYWRIGHT_MODULE;
assert.equal(require(path.join(modulePath, 'package.json')).version, '1.56.0');
const { chromium } = require(modulePath);
const project = path.resolve(process.env.READING_GUIDE_PROJECT || 'johnhull');
const output = process.env.READING_GUIDE_OUTPUT_DIR || '/home/kazumasa/projects/_data/johnhull/reading-guide';
const results = [];
let browserVersion;
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN });
  browserVersion = browser.version();
  fs.mkdirSync(path.join(output, 'screenshots'), {recursive: true});
  for (const width of [1280, 390]) {
    const context = await browser.newContext({viewport: {width, height: 900}, locale: 'ja-JP', timezoneId: 'Asia/Tokyo', colorScheme: 'light'});
    for (const chapter of ['08', '13']) {
      const page = await context.newPage();
      const external = [], errors = [];
      page.on('request', request => {
        if (!/^(file:|data:|about:)/.test(request.url())) external.push(request.url());
      });
      page.on('pageerror', error => errors.push(String(error)));
      await page.route(/^https?:/, route => route.abort());
      const url = pathToFileURL(path.join(project, 'book/_build/html/notebooks/guide', `ch${chapter}.html`)).href;
      await page.goto(url, {waitUntil: 'load'});
      await page.evaluate(async () => {
        if (window.MathJax?.startup) await MathJax.startup.promise;
        await document.fonts.ready;
      });
      const info = await page.evaluate(() => {
        const article = document.querySelector('article.bd-article');
        return {
          title: article.querySelector('h1').innerText,
          width: window.innerWidth,
          document_width: document.documentElement.scrollWidth,
          mathjax: window.MathJax?.version,
          rendered: article.querySelectorAll('mjx-container').length,
          math_errors: article.querySelectorAll('mjx-merror, .merror').length,
          raw_math: article.querySelectorAll('.math:not(:has(mjx-container))').length,
          math_overflow: [...article.querySelectorAll('div.math, mjx-container[display="true"]')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => ({text: e.innerText, width: e.clientWidth, scroll: e.scrollWidth})),
          links: [...article.querySelectorAll('a[href]')].map(a => ({text: a.innerText, href: a.href})),
        };
      });
      const badLinks = [];
      let localLinks = 0;
      for (const link of info.links) {
        const parsed = new URL(link.href);
        if (parsed.protocol !== 'file:') continue;
        localLinks++;
        const target = fileURLToPath(parsed);
        if (!fs.existsSync(target)) {badLinks.push(link); continue;}
        if (parsed.hash) {
          const anchor = decodeURIComponent(parsed.hash.slice(1));
          const source = fs.readFileSync(target, 'utf8');
          if (!source.includes(`id="${anchor}"`) && !source.includes(`id='${anchor}'`)) badLinks.push(link);
        }
      }
      delete info.links;
      const prefix = path.join(output, 'screenshots', `ch${chapter}-${width}`);
      await page.screenshot({path: prefix + '-full.png', fullPage: true});
      await page.screenshot({path: prefix + '-top.png'});
      const equations = page.locator('article.bd-article div.math');
      if (await equations.count()) {
        await equations.first().scrollIntoViewIfNeeded();
        await page.screenshot({path: prefix + '-math.png'});
      }
      const result = {chapter, ...info, local_links: localLinks, bad_links: badLinks, external, errors, html_sha256: sha(fileURLToPath(url)), screenshots: [prefix+'-full.png',prefix+'-top.png',prefix+'-math.png'].filter(fs.existsSync).map(file => ({path:file,sha256:sha(file)}))};
      results.push(result);
      console.log(JSON.stringify({...result,screenshots:undefined}));
      await page.close();
    }
    await context.close();
  }
  await browser.close();
  const report = {playwright: '1.56.0', chromium: browserVersion, checked_at: new Date().toISOString(), results};
  fs.writeFileSync(path.join(output, 'guide-browser.json'), JSON.stringify(report,null,2)+'\n');
  assert(results.every(r => r.width === r.document_width && r.mathjax === '3.2.2' && r.rendered > 0 && !r.math_errors && !r.raw_math && !r.math_overflow.length && !r.bad_links.length && !r.external.length && !r.errors.length), 'Guide browser checks failed; inspect guide-browser.json');
})().catch(error => {console.error(error); process.exitCode=1;});
