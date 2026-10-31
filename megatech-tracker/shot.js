// Spike helper: screenshot each view and report page errors.
// NODE_PATH=<dir with playwright> CH=<chrome binary> node shot.js <html> <outdir> [dark]
const { chromium } = require("playwright");

(async () => {
  const [html, outdir, scheme] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: process.env.CH });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    colorScheme: scheme === "dark" ? "dark" : "light",
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  for (const view of (process.env.VIEWS || "overview,season,world,co/MSFT,co/TSLA").split(",")) {
    await page.goto(`file://${html}#${view}`);
    await page.waitForTimeout(600);
    const name = view.replace("/", "-") + (scheme === "dark" ? "-dark" : "");
    await page.screenshot({ path: `${outdir}/${name}.png`, fullPage: true });
  }
  await browser.close();
  console.log(errors.length ? "ERRORS:\n" + errors.join("\n") : "no page errors");
})();
