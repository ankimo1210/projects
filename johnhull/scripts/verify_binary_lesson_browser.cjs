// §26.10 rendered acceptance. Uses existing Playwright/Chromium; no npm install.
// PLAYWRIGHT_MODULE=/path/to/playwright CHROMIUM_BIN=/path/to/chrome node this-file.cjs
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const root = path.resolve(__dirname, "..");
const out = path.join(root, "docs/validation/section-26-10");
fs.mkdirSync(out, { recursive: true });
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ["binary_payoffs", "binary_replication", "binary_spreads", "binary_delta"];
// Independent GBM density integrals. Delta uses Richardson symmetric differences
// with spot increments .01 and .005, rather than the plotted delta formula.
const reference = {
  "market": {
    "spot": 100,
    "strike": 100,
    "rate": 0.05,
    "volatility": 0.2,
    "expiry": 1,
    "dividend": 0.02
  },
  "payout": 100,
  "prices": {
    "cash_call": 49.45810910532236,
    "asset_call": 58.68511461347642,
    "cash_put": 45.66483334474906,
    "asset_put": 39.334752717199144
  },
  "delta": [
    {
      "T": 1,
      "S": 100,
      "delta": 1.8950578754952356
    },
    {
      "T": 0.0821917808219178,
      "S": 100,
      "delta": 6.92845632885124
    },
    {
      "T": 0.0027397260273972603,
      "S": 100,
      "delta": 38.10355729155859
    }
  ],
  "method": "Discounted log-return density integral, with Richardson-extrapolated symmetric differences for delta at S=100; h=.01 and .005."
};
function check(ok, message) { if (!ok) throw new Error(message); }
function close(actual, expected, message, tolerance = 2e-8) {
  check(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
        message + ": actual=" + actual + ", expected=" + expected);
}
const result = { checked_at: new Date().toISOString(), reference, pages: {},
                 source_sha256: {}, artifact_sha256: {} };

async function plotFor(page, key) {
  await page.waitForFunction(key => Array.from(document.querySelectorAll(".plotly-graph-div"))
    .some(el => el.layout?.meta?.figure === key && el._fullLayout), key, { timeout });
  const ids = await page.locator(".plotly-graph-div").evaluateAll((elements, key) =>
    elements.filter(el => el.layout?.meta?.figure === key).map(el => el.id), key);
  check(ids.length === 1, "Expected one rendered " + key + "; got " + ids.length);
  return page.locator('[id="' + ids[0] + '"]');
}

async function traces(plot) {
  return plot.evaluate(el => el._fullData
    .filter(t => t.visible === true)
    .map(t => ({ name: t.name, meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []) })));
}

async function settleLayout(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => !document.getAnimations().some(a => a.playState === "running"),
                            null, { timeout });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function centerForScreenshot(page, locator) {
  await locator.evaluate(el => el.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
  await settleLayout(page);
  const shift = await locator.evaluate(el => {
    const headerBottom = Math.max(0, ...Array.from(document.querySelectorAll(".topbar,.bd-header-article"))
      .map(n => n.getBoundingClientRect()).filter(r => r.top >= -1 && r.top < 150).map(r => r.bottom));
    return Math.min(0, el.getBoundingClientRect().top - headerBottom - 12);
  });
  if (shift < 0) {
    await page.evaluate(dy => window.scrollBy(0, dy), shift);
    await settleLayout(page);
  }
}

function valuesAt(rows, predicate, x) {
  return rows.filter(predicate).flatMap(row => row.x.flatMap((v, i) =>
    typeof v === "number" && Math.abs(v - x) < 1e-10 && typeof row.y[i] === "number"
      ? [row.y[i]] : []));
}

function oneValue(rows, predicate, x, expected, message, tolerance) {
  const matches = valuesAt(rows, predicate, x);
  check(matches.length > 0, "Missing plotted point: " + message);
  for (const value of matches) close(value, expected, message, tolerance);
}

function verifyPayoffs(rows) {
  for (const terminal of [80, 100, 120]) {
    const call = terminal >= 100;
    const expected = { cash_call: call ? 100 : 0, cash_put: call ? 0 : 100,
                       asset_call: call ? terminal : 0, asset_put: call ? 0 : terminal };
    for (const [contract, payoff] of Object.entries(expected)) {
      oneValue(rows, t => t.meta?.role === "payoff" && t.meta.contract === contract,
               terminal, payoff, contract + " settlement at " + terminal);
    }
  }
}

function verifyReplication(rows, kind) {
  const actual = [];
  for (const terminal of [80, 100, 120]) {
    const event = kind === "call" ? terminal >= 100 : terminal < 100;
    const sign = kind === "call" ? 1 : -1;
    const expected = { cash_leg: event ? -sign * 100 : 0,
                       asset_leg: event ? sign * terminal : 0,
                       reconstructed: Math.max(sign * (terminal - 100), 0),
                       vanilla: Math.max(sign * (terminal - 100), 0) };
    for (const [role, payoff] of Object.entries(expected)) {
      oneValue(rows, t => t.meta?.role === role && t.meta.kind === kind,
               terminal, payoff, kind + " " + role + " at " + terminal);
    }
    actual.push({ terminal, ...expected });
  }
  return actual;
}

function verifySpreads(rows) {
  for (const width of [1, 5, 15]) {
    for (const terminal of [80, 100, 120]) {
      const call = strike => Math.max(terminal - strike, 0);
      const spread = (call(100 - width / 2) - call(100 + width / 2)) / width;
      const butterfly = (call(100 - width) - 2 * call(100) + call(100 + width)) / width ** 2;
      oneValue(rows, t => t.meta?.role === "spread" && t.meta.width === width,
               terminal, spread, "spread width=" + width + " at " + terminal);
      oneValue(rows, t => t.meta?.role === "butterfly" && t.meta.width === width,
               terminal, butterfly, "butterfly width=" + width + " at " + terminal);
    }
  }
}

function verifyDelta(rows) {
  for (const pin of reference.delta) {
    oneValue(rows, t => t.meta?.role === "cash_delta" && Math.abs(t.meta.T - pin.T) < 1e-12,
             pin.S, pin.delta, "independent delta T=" + pin.T, 2e-6);
  }
  for (const trace of rows.filter(t => t.meta?.role === "cash_delta")) {
    check(trace.y.every(value => Number.isFinite(value) && value >= 0), "Nonfinite/negative delta");
  }
}

async function selectKind(page, plot, kind) {
  await plot.locator(".updatemenu-header").click();
  await plot.locator(".updatemenu-dropdown-button").filter({ hasText: new RegExp("^" + kind + "$") }).click();
  await page.waitForFunction(({ id, kind }) => document.getElementById(id)._fullLayout.title.text.includes(kind),
                            { id: await plot.getAttribute("id"), kind }, { timeout });
}

async function rejectMisallocation(plot, kind) {
  const saved = await plot.evaluate(async (el, kind) => {
    const cash = el._fullData.findIndex(t => t.visible === true && t.meta?.role === "cash_leg" && t.meta.kind === kind);
    const asset = el._fullData.findIndex(t => t.visible === true && t.meta?.role === "asset_leg" && t.meta.kind === kind);
    const cashY = Array.from(el._fullData[cash].y), assetY = Array.from(el._fullData[asset].y);
    const index = Array.from(el._fullData[cash].x).findIndex(v => Math.abs(v - 100) < 1e-10);
    const cashBad = [...cashY], assetBad = [...assetY];
    cashBad[index] += 1;
    assetBad[index] -= 1;
    await Plotly.restyle(el, { y: [cashBad, assetBad] }, [cash, asset]);
    return { cash, asset, cashY, assetY, index,
             original_sum: cashY[index] + assetY[index],
             mutated_sum: cashBad[index] + assetBad[index] };
  }, kind);
  let rejected = false;
  try {
    close(saved.original_sum, saved.mutated_sum, "Negative control preserves total payoff");
    try { verifyReplication(await traces(plot), kind); }
    catch (error) {
      check(error.message.includes("cash_leg"), "Negative control failed for an unrelated reason");
      rejected = true;
    }
    check(rejected, "Wrong individual legs passed the rendered check");
  } finally {
    await plot.evaluate(async (el, saved) =>
      Plotly.restyle(el, { y: [saved.cashY, saved.assetY] }, [saved.cash, saved.asset]), saved);
  }
  verifyReplication(await traces(plot), kind);
  return { type: "offset_cash_and_asset_legs", total_payoff_unchanged: true, rejected };
}

async function verifySurface(page, label) {
  const plots = {};
  for (const key of keys) plots[key] = await plotFor(page, key);
  verifyPayoffs(await traces(plots.binary_payoffs));
  verifySpreads(await traces(plots.binary_spreads));
  verifyDelta(await traces(plots.binary_delta));
  const labels = await plots.binary_replication.evaluate(el => el.layout.updatemenus[0].buttons.map(b => b.label));
  check(labels.length === 2 && labels.includes("call") && labels.includes("put"), "Replication menu contract mismatch");
  const states = [];
  for (const kind of ["call", "put"]) {
    await selectKind(page, plots.binary_replication, kind);
    states.push({ kind, points: verifyReplication(await traces(plots.binary_replication), kind) });
  }
  const negative_control = await rejectMisallocation(plots.binary_replication, "put");
  const screenshots = [];
  for (const width of [1440, 1000]) {
    await page.setViewportSize({ width, height: 1050 });
    await settleLayout(page);
    for (const key of keys) {
      const plot = plots[key];
      await centerForScreenshot(page, plot);
      await page.waitForFunction(el => Math.abs(el.clientWidth - el._fullLayout.width) < 3,
                                await plot.elementHandle(), { timeout });
      check(await plot.evaluate(el => el.scrollWidth <= el.clientWidth + 3),
            "Horizontal overflow: " + label + "/" + key);
      const clipped = await plot.evaluate(el => {
        const frame = el.getBoundingClientRect();
        return Array.from(el.querySelectorAll(".annotation-text,.gtitle,.xtitle,.ytitle,.legend"))
          .filter(node => {
            const box = node.getBoundingClientRect();
            return box.width > 0 && box.height > 0 &&
              (box.left < frame.left - 3 || box.right > frame.right + 3 ||
               box.top < frame.top - 3 || box.bottom > frame.bottom + 3);
          }).map(node => node.textContent.slice(0, 100));
      });
      check(clipped.length === 0, "Clipped chart text: " + label + "/" + key + ": " + clipped.join("; "));
      const overlapping = await plot.evaluate(el => {
        const legend = el.querySelector(".legend")?.getBoundingClientRect();
        if (!legend) return [];
        return Array.from(el.querySelectorAll(".annotation-text")).filter(node => {
          const box = node.getBoundingClientRect();
          return box.width > 0 && box.height > 0 && box.left < legend.right - 2 &&
            box.right > legend.left + 2 && box.top < legend.bottom - 2 && box.bottom > legend.top + 2;
        }).map(node => node.textContent.slice(0, 100));
      });
      check(overlapping.length === 0, "Annotation overlaps legend: " + label + "/" + key);
      const axisOverlap = await plot.evaluate(el => {
        const labels = Array.from(el.querySelectorAll(".xtitle,.ytitle,.xtick text,.ytick text"));
        const legends = Array.from(el.querySelectorAll(".legendtext"));
        return labels.some(axis => legends.some(legend => {
          const a = axis.getBoundingClientRect(), b = legend.getBoundingClientRect();
          return a.width > 0 && b.width > 0 && a.left < b.right - 1 && a.right > b.left + 1 &&
            a.top < b.bottom - 1 && a.bottom > b.top + 1;
        }));
      });
      check(!axisOverlap, "Axis text overlaps legend: " + label + "/" + key);
      const relative = "docs/validation/section-26-10/" + label + "-" + key + "-" + width + ".png";
      await plot.screenshot({ path: path.join(root, relative) });
      screenshots.push(relative);
    }
  }
  return { figures: keys, replication_states: states, negative_control, screenshots };
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_BIN || undefined,
                                        args: ["--no-sandbox"] });
  result.browser_version = browser.version();
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const portal = await context.newPage();
    const portalErrors = [], portalRequests = [];
    portal.on("pageerror", error => portalErrors.push(error.message));
    await portal.route(/^https?:/, route => { portalRequests.push(route.request().url()); return route.abort(); });
    await portal.goto("file://" + path.join(root, "report/site/exotics.html"));
    result.pages.portal = { ...(await verifySurface(portal, "portal")), external_network_blocked: true,
                            external_requests: portalRequests, page_errors: portalErrors };
    check(portalErrors.length === 0 && portalRequests.length === 0, "Portal errors or external dependencies");

    const book = await context.newPage();
    const bookErrors = [], bookRequests = new Set();
    book.on("pageerror", error => bookErrors.push(error.message));
    book.on("request", request => { if (/^https?:/.test(request.url())) bookRequests.add(request.url()); });
    await book.goto("file://" + path.join(root, "book/_build/html/notebooks/10_exotics.html"));
    const heading = book.locator("h2").filter({ hasText: /バイナリ.*26\.10/ });
    check(await heading.count() === 1, "Missing binary section heading");
    const section = heading.locator("xpath=..");
    await book.waitForFunction(() => !!window.MathJax?.startup?.promise, null, { timeout });
    await book.evaluate(() => window.MathJax.startup.promise);
    const math = await section.evaluate(el => ({
      typeset: el.querySelectorAll("mjx-container").length,
      errors: el.querySelectorAll("mjx-merror,.MathJax_Error").length,
      blocks: Array.from(el.querySelectorAll("div.math")).map(n => ({ width: n.clientWidth, scroll_width: n.scrollWidth })),
      headings: Array.from(el.querySelectorAll("h3")).map(n => n.textContent),
      rows: Array.from(el.querySelectorAll("tr")).map(n => n.textContent),
      text: el.textContent,
    }));
    check(math.typeset >= 12 && math.errors === 0, "Binary section math typesetting failed");
    check(math.blocks.every(b => b.scroll_width <= b.width + 3), "Binary formula overflow");
    for (let i = 1; i <= 6; i++) check(math.headings.some(h => h.includes("2." + i)), "Missing teaching section 2." + i);
    math.prices = {};
    for (const [contract, price] of Object.entries(reference.prices)) {
      const label = contract.replace("_", " ");
      const rows = math.rows.filter(row => row.includes(label) && row.includes(price.toFixed(6)));
      check(rows.length === 1, "Missing/mislabelled independent Book price: " + label + " = " + price.toFixed(6));
      math.prices[contract] = price.toFixed(6);
    }
    delete math.text;
    delete math.rows;
    math.price_screenshots = [];
    for (const width of [1440, 1000]) {
      await book.setViewportSize({ width, height: 1050 });
      await settleLayout(book);
      const blocks = await section.evaluate(el => Array.from(el.querySelectorAll("div.math"))
        .map(n => ({ width: n.clientWidth, scroll_width: n.scrollWidth })));
      check(blocks.every(b => b.scroll_width <= b.width + 3), "Binary formula overflow at " + width);
      const priceSection = section.locator("h3").filter({ hasText: /2\.2/ }).locator("xpath=..");
      // Fit the entire subsection below sticky navigation while preserving the
      // tested width. Enlarging height avoids clipped/offscreen locator captures.
      const height = Math.ceil((await priceSection.boundingBox()).height) + 240;
      await book.setViewportSize({ width, height: Math.max(1050, height) });
      await settleLayout(book);
      await centerForScreenshot(book, priceSection);
      const relative = "docs/validation/section-26-10/book-binary-prices-" + width + ".png";
      await priceSection.screenshot({ path: path.join(root, relative) });
      math.price_screenshots.push(relative);
    }
    result.pages.book = { ...(await verifySurface(book, "book")), math, external_network_blocked: false,
                          external_requests: [...bookRequests], page_errors: bookErrors };
    check(bookErrors.length === 0, "Book JS errors: " + bookErrors);

    for (const file of [
      "hullkit/src/hullkit/_binary_lesson.py", "hullkit/tests/test_binary_lesson.py",
      "hullkit/src/hullkit/exotics.py", "hullkit/src/hullkit/bsm.py", "hullkit/tests/test_binary_reference.py",
      "volumes/10_exotics_martingales/build_exotics_notebook.py", "volumes/10_exotics_martingales/exotics.ipynb",
      "report/report_builder/figures.py", "report/report_builder/render.py", "report/assets/style.css",
      "book/_ext/book_runtime.py", "book/_config.yml",
      "scripts/verify_binary_lesson_browser.cjs",
    ]) result.source_sha256[file] = crypto.createHash("sha256").update(fs.readFileSync(path.join(root, file))).digest("hex");
    for (const file of ["report/site/exotics.html", "report/site/assets/style.css", "report/site/assets/plotly.min.js",
                        "book/_build/html/notebooks/10_exotics.html"]) {
      result.artifact_sha256[file] = crypto.createHash("sha256").update(fs.readFileSync(path.join(root, file))).digest("hex");
    }
    result.status = "PASS";
    console.log(JSON.stringify({ status: "PASS", surfaces: 2, figures_per_surface: 4, tested_viewports: [1440,1000],
                                book_math: math.typeset, output: out }, null, 2));
  } finally { await browser.close(); }
})().catch(error => {
  result.status = "FAIL";
  result.error = error.message;
  console.error(error.message);
  process.exitCode = 1;
}).finally(() => fs.writeFileSync(path.join(out, "browser-check.json"), JSON.stringify(result, null, 2) + "\n"));
