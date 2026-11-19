// Dev helper: tile screenshots into contact sheets so many can be reviewed at once.
//   node e2e/sheet.mjs <dir> <outPrefix> [cols=3] [filter]
import { readdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "playwright-core";

const dir = resolve(process.argv[2]);
const out = process.argv[3];
const cols = Number(process.argv[4] ?? 3);
const filter = process.argv[5] ?? "";
const files = readdirSync(dir)
  .filter((f) => f.endsWith(".png") && f.includes(filter))
  .sort();
const per = cols * 2;
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 640 * cols, height: 720 }, deviceScaleFactor: 1 });
for (let n = 0; n < files.length; n += per) {
  const chunk = files.slice(n, n + per);
  const html = `<body style="margin:0;background:#000;display:grid;grid-template-columns:repeat(${cols},640px)">${chunk
    .map(
      (f) =>
        `<div style="position:relative;height:360px"><img src="file://${join(dir, f)}" style="width:640px;height:360px;display:block"><span style="position:absolute;left:6px;top:4px;font:12px monospace;color:#ff5;text-shadow:0 0 3px #000">${f.slice(0, -4)}</span></div>`,
    )
    .join("")}</body>`;
  const tmp = join(dir, "_sheet.html");
  writeFileSync(tmp, html);
  await page.goto(`file://${tmp}`);
  await page.waitForTimeout(300);
  const path = `${out}-${n / per + 1}.jpg`;
  await page.screenshot({ path, type: "jpeg", quality: 88, clip: { x: 0, y: 0, width: 640 * cols, height: 360 * Math.ceil(chunk.length / cols) } });
  console.log(path, chunk.length);
}
await browser.close();
