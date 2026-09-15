// §26.9 distribution check. Uses an existing Playwright installation, no npm install.
// PLAYWRIGHT_MODULE=/path/to/playwright CHROMIUM_BIN=/path/to/chrome \
//   node johnhull/scripts/verify_barrier_pilot_browser.cjs
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const root = path.resolve(__dirname, "..");
const out = path.join(root, "docs/validation/section-26-9");
fs.mkdirSync(out, { recursive: true });
function check(ok, message) { if (!ok) throw new Error(message); }
const result = {
  checked_at: new Date().toISOString(),
  viewport: { width: 1440, height: 1000 },
  pages: {},
  source_sha256: {},
  artifact_sha256: {},
};
for (const file of [
  "volumes/10_exotics_martingales/build_exotics_notebook.py",
  "volumes/10_exotics_martingales/exotics.ipynb",
  "hullkit/src/hullkit/exotics.py", "hullkit/src/hullkit/plotly_viz.py",
  "hullkit/tests/test_barrier_reference.py",
  "report/report_builder/figures.py", "report/report_builder/render.py",
  "book/_config.yml", "book/_ext/book_runtime.py", "scripts/verify_barrier_pilot_browser.cjs",
]) result.source_sha256[file] = crypto.createHash("sha256").update(fs.readFileSync(path.join(root, file))).digest("hex");

// Synthetic default-input pins from the independent Brownian-bridge integral
// in test_barrier_reference.py (S=K=100,r=.05,q=0,sigma=.2,T=1).
const INDEPENDENT_PRICES = {
  "call / down-and-out": {
    "H": 90,
    "price": 8.665471658245668
  },
  "call / down-and-in": {
    "H": 90,
    "price": 1.7851119139399
  },
  "call / up-and-out": {
    "H": 110,
    "price": 0.11861405278910797
  },
  "call / up-and-in": {
    "H": 110,
    "price": 10.33196951939646
  },
  "put / down-and-out": {
    "H": 90,
    "price": 0.1512203764398823
  },
  "put / down-and-in": {
    "H": 90,
    "price": 5.4223056458170875
  },
  "put / up-and-out": {
    "H": 110,
    "price": 4.198193810925504
  },
  "put / up-and-in": {
    "H": 110,
    "price": 1.375332211331466
  }
};
for (const file of [
  "report/site/exotics.html", "report/site/assets/style.css", "report/site/assets/plotly.min.js",
  "book/_build/html/notebooks/10_exotics.html",
]) result.artifact_sha256[file] = crypto.createHash("sha256").update(fs.readFileSync(path.join(root, file))).digest("hex");

async function verifyExplorer(page, plot, labelPrefix) {
  await plot.waitFor({ state: "visible" });
  await page.waitForFunction(el => !!el._fullLayout, await plot.elementHandle());
  await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 2,
                            await plot.elementHandle());
  const buttons = await plot.evaluate(el => el.layout.updatemenus[0].buttons.map(b => b.label));
  check(buttons.length === 8 && new Set(buttons).size === 8 &&
        buttons.every(label => Object.hasOwn(INDEPENDENT_PRICES, label)), "Expected eight contracts");
  await plot.screenshot({ path: path.join(out, labelPrefix + "-initial.png") });
  const views = [];
  for (const label of buttons) {
    await plot.locator(".updatemenu-header").click();
    const escaped = label.replace(/[.*+?^$()|[\]\\]/g, "\\$&");
    await plot.locator(".updatemenu-dropdown-button").filter({ hasText: new RegExp("^" + escaped + "$") }).click();
    await page.waitForFunction(({ id, label }) => document.getElementById(id)._fullLayout.title.text.includes(label),
                              { id: await plot.getAttribute("id"), label });
    // Plotly fades the menu after updating the title; wait for that visual state.
    await page.waitForFunction(el => Array.from(el.querySelectorAll(".updatemenu-dropdown-button")).every(button => {
      for (let node = button; node && node !== el; node = node.parentElement) {
        const style = getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return true;
      }
      return false;
    }), await plot.elementHandle());
    const reference = INDEPENDENT_PRICES[label];
    const state = await plot.evaluate((el, referenceH) => {
      const shown = el._fullData.filter(t => t.visible === true);
      const a = shown[0], b = shown[1], v = shown[2];
      return {
        title: el._fullLayout.title.text,
        names: shown.map(t => t.name),
        points: a.x.length,
        range: [a.x[0], a.x[a.x.length - 1]],
        parity_error: Math.max(...Array.from(a.y, (value, i) => Math.abs(value + b.y[i] - v.y[i]))),
        minimum: Math.min(...a.y),
        vanilla: v.y[0],
        maximum: Math.max(...a.y),
        reference_H: referenceH,
        reference_price: a.y[Array.from(a.x).findIndex(x => Math.abs(x - referenceH) < 1e-8)],
      };
    }, reference.H);
    const [kind, contract] = label.split(" / ");
    check(state.names.length === 3, "Expected three visible curves: " + label);
    check(state.names[0] === contract && state.names[2] === "vanilla " + kind, "Wrong selected contract: " + label);
    check(state.points >= 50 && state.parity_error < 1e-9 && state.minimum >= -1e-9, "Invalid plot data: " + label);
    check(contract.startsWith("down") ? state.range[1] === 100 : state.range[0] === 100, "Wrong H axis: " + label);
    check(state.maximum <= state.vanilla + 1e-9, "Price exceeds vanilla: " + label);
    check(Number.isFinite(state.reference_price) && Math.abs(state.reference_price - reference.price) < 2e-8,
          "Independent price mismatch: " + label);
    views.push({ label, ...state, independent_reference: reference.price });
  }
  await plot.screenshot({ path: path.join(out, labelPrefix + "-put-up-in.png") });
  return views;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_BIN || undefined,
    args: ["--no-sandbox"],
  });
  result.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: result.viewport });
    const portal = await context.newPage();
    const portalErrors = [];
    const portalNetwork = [];
    portal.on("pageerror", e => portalErrors.push(e.message));
    await portal.route(/^https?:/, route => { portalNetwork.push(route.request().url()); return route.abort(); });
    await portal.goto("file://" + path.join(root, "report/site/exotics.html"));
    result.pages.portal = {
      external_network_blocked: true,
      attempted_external_requests: portalNetwork,
      views: await verifyExplorer(portal, portal.locator("#fig-barrier_knockout"), "portal"),
      page_errors: portalErrors,
    };
    check(portalErrors.length === 0, "Portal JS errors: " + portalErrors);
    check(portalNetwork.length === 0, "Portal tried external resources");

    const book = await context.newPage();
    const bookErrors = [];
    const bookNetwork = new Set();
    book.on("pageerror", e => bookErrors.push(e.message));
    book.on("request", r => { if (/^https?:/.test(r.url())) bookNetwork.add(r.url()); });
    await book.goto("file://" + path.join(root, "book/_build/html/notebooks/10_exotics.html"));
    const section = book.locator("#ge-pp-620622");
    await section.waitFor();
    await book.waitForFunction(() => !!window.MathJax?.startup?.promise, null, { timeout: 30000 });
    await book.evaluate(() => window.MathJax.startup.promise);
    const images = section.locator(".cell_output img");
    check(await images.count() === 5, "Expected path / eight contracts / BGK / vega / Parisian figures");
    const names = ["path", "eight", "bgk", "vega", "parisian"];
    for (let i = 0; i < names.length; i++) {
      check(await images.nth(i).evaluate(img => img.complete && img.naturalWidth > 0), "Broken book image");
      await images.nth(i).screenshot({ path: path.join(out, "book-" + names[i] + ".png") });
    }
    const math = await section.evaluate(el => ({
      typeset: el.querySelectorAll("mjx-container").length,
      errors: el.querySelectorAll("mjx-merror, .MathJax_Error").length,
      display_blocks: Array.from(el.querySelectorAll("div.math")).map(n => ({
        width: n.clientWidth, scroll_width: n.scrollWidth,
      })),
    }));
    check(math.typeset >= 40 && math.errors === 0, "Math typesetting failed");
    check(math.display_blocks.every(block => block.scroll_width <= block.width + 2), "Formula overflow");
    const formulas = section.locator("div.math").nth(2);
    await formulas.screenshot({ path: path.join(out, "book-formulas.png") });
    result.pages.book = {
      external_network_blocked: false,
      external_requests: [...bookNetwork],
      images: names,
      math,
      views: await verifyExplorer(book, section.locator(".plotly-graph-div"), "book-explorer"),
      page_errors: bookErrors,
    };
    check(bookErrors.length === 0, "Book JS errors: " + bookErrors);
    result.status = "PASS";
    fs.writeFileSync(path.join(out, "browser-check.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify({
      status: result.status, portal_contracts: result.pages.portal.views.length,
      book_contracts: result.pages.book.views.length, book_images: names.length, math,
      book_external_requests: result.pages.book.external_requests, output: out,
    }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {
  result.status = "FAIL";
  result.error = error.message;
  fs.writeFileSync(path.join(out, "browser-check.json"), JSON.stringify(result, null, 2) + "\n");
  console.error(error);
  process.exitCode = 1;
});
