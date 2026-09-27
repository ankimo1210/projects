// Observe runtime rendering facts a static fingerprint cannot know: the Chromium version,
// the MathJax version the Book actually loaded, and the platform fonts used for text.
// Usage: node probe_render_runtime.cjs <project-root> <book-page> <portal-page> <figure-key>
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const [root, bookPage, portalPage, figureKey] = process.argv.slice(2);

async function platformFonts(page, selector) {
  const session = await page.context().newCDPSession(page);
  await session.send('DOM.enable');
  await session.send('CSS.enable');
  const { root: documentNode } = await session.send('DOM.getDocument', { depth: -1 });
  const { nodeId } = await session.send('DOM.querySelector', { nodeId: documentNode.nodeId, selector });
  if (!nodeId) return null;
  const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
  await session.detach();
  return fonts.map(font => font.familyName).sort();
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN, args: ['--no-sandbox'] });
  const result = { browser_version: browser.version(), mathjax_version: null, fonts: {} };
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const book = await context.newPage();
    await book.goto('file://' + path.join(root, bookPage));
    await book.waitForFunction(() => !!window.MathJax?.startup?.promise);
    await book.evaluate(() => window.MathJax.startup.promise);
    result.mathjax_version = await book.evaluate(() => window.MathJax.version || null);
    result.fonts.book_heading = await platformFonts(book, 'article h1');
    result.fonts.book_body = await platformFonts(book, 'article p');
    const portal = await context.newPage();
    await portal.route(/^https?:/, route => route.abort());
    await portal.goto('file://' + path.join(root, portalPage));
    await portal.waitForFunction(key => document.getElementById('fig-' + key)?._fullLayout, figureKey);
    result.fonts.portal_heading = await platformFonts(portal, 'figure.fig-card h3');
    result.fonts.portal_plot_text = await platformFonts(portal, `#fig-${figureKey} text.gtitle, #fig-${figureKey} text`);
    result.status = 'PASS';
  } catch (error) {
    result.status = 'FAIL';
    result.error = error.message;
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ runtime: result }));
})();
