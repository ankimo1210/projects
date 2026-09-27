// Observe browser and rendering inputs that a static fingerprint cannot know.
// Usage: node probe_render_runtime.cjs <project-root> <book-page> <portal-page> <figure-key>
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

function fontCatalog() {
  const output = execFileSync('fc-list', ['-f', '%{family}\t%{postscriptname}\t%{file}\n'], { encoding: 'utf8' });
  return output.trimEnd().split('\n').map(line => {
    const [families, postscript, file] = line.split('\t');
    return { families: (families || '').split(',').map(name => name.trim()), postscript, file };
  });
}

function resolveFonts(observed, catalog) {
  if (!Array.isArray(observed) || observed.length === 0) throw new Error('no platform fonts observed');
  return observed.map(font => {
    if (font.isCustomFont) throw new Error(`cannot map custom font ${font.familyName}`);
    const matches = catalog.filter(entry => font.postScriptName
      ? entry.postscript === font.postScriptName
      : (entry.families || [entry.family]).includes(font.familyName));
    const files = [...new Set(matches.map(entry => entry.file))];
    if (files.length !== 1 || !files[0]) {
      throw new Error(`cannot map platform font ${font.familyName} (${font.postScriptName || 'no PostScript name'}) to one file`);
    }
    const data = fs.readFileSync(files[0]);
    return {
      family: font.familyName,
      postscript: font.postScriptName || null,
      file: path.basename(files[0]),
      sha256: crypto.createHash('sha256').update(data).digest('hex'),
    };
  }).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
}

function digestScripts(scripts) {
  if (!Array.isArray(scripts) || scripts.length === 0) throw new Error('no MathJax script response');
  return scripts.map(({ url, body }) => {
    if (!url || !Buffer.isBuffer(body) || body.length === 0) throw new Error('MathJax script bytes unavailable');
    return { url, sha256: crypto.createHash('sha256').update(body).digest('hex') };
  }).sort((a, b) => a.url.localeCompare(b.url));
}

async function platformFonts(page, selector, catalog) {
  const session = await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable');
    await session.send('CSS.enable');
    const { root: documentNode } = await session.send('DOM.getDocument', { depth: -1 });
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: documentNode.nodeId, selector });
    if (!nodeId) throw new Error(`font selector not found: ${selector}`);
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    return resolveFonts(fonts, catalog);
  } finally {
    await session.detach();
  }
}

async function main() {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  const [root, bookPage, portalPage, figureKey] = process.argv.slice(2);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
  const result = { browser_version: browser.version(), mathjax_version: null, mathjax_scripts: null, fonts: {} };
  try {
    const catalog = fontCatalog();
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const book = await context.newPage();
    const mathjaxResponses = [];
    book.on('response', response => {
      if (response.request().resourceType() === 'script' && /mathjax/i.test(response.url())
          && response.status() >= 200 && response.status() < 300) {
        mathjaxResponses.push(response);
      }
    });
    await book.goto('file://' + path.join(root, bookPage));
    await book.waitForFunction(() => !!window.MathJax?.startup?.promise);
    await book.evaluate(() => window.MathJax.startup.promise);
    result.mathjax_version = await book.evaluate(() => window.MathJax.version || null);
    if (!result.mathjax_version) throw new Error('MathJax version unavailable');
    result.mathjax_scripts = digestScripts(await Promise.all(mathjaxResponses.map(async response => ({
      url: response.url(), body: await response.body(),
    }))));
    result.fonts.book_heading = await platformFonts(book, 'article h1', catalog);
    result.fonts.book_body = await platformFonts(book, 'article p', catalog);
    const portal = await context.newPage();
    await portal.route(/^https?:/, route => route.abort());
    await portal.goto('file://' + path.join(root, portalPage));
    await portal.waitForFunction(key => document.getElementById('fig-' + key)?._fullLayout, figureKey);
    result.fonts.portal_heading = await platformFonts(portal, 'figure.fig-card h3', catalog);
    result.fonts.portal_plot_text = await platformFonts(portal, `#fig-${figureKey} text.gtitle, #fig-${figureKey} text`, catalog);
    result.status = 'PASS';
  } catch (error) {
    result.status = 'FAIL';
    result.error = error.message;
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ runtime: result }));
}

if (require.main === module) main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

module.exports = { resolveFonts, digestScripts };
