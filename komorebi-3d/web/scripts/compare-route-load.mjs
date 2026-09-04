import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';

// Audit each full site's initial JS payload with an isolated browser cache.
// gzip is a reproducible estimate, not a claim about a deployment's encoding.
const origin = process.argv[2] ?? 'http://localhost:3101';
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  args: [
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader',
  ],
});
const results = [];
try {
  for (const route of ['/', '/babylon']) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      reducedMotion: 'reduce',
    });
    const page = await context.newPage();
    const pending = [];
    page.on('response', (response) => {
      if (
        !response.url().startsWith(origin) ||
        !new URL(response.url()).pathname.endsWith('.js')
      )
        return;
      pending.push(
        response.body().then((body) => ({
          url: new URL(response.url()).pathname,
          decodedBytes: body.byteLength,
          gzipBytes: gzipSync(body).byteLength,
        })),
      );
    });
    await page.goto(new URL(route, origin).href);
    await page.waitForFunction(() =>
      document.querySelector('.scene-index')?.textContent?.includes('LIVE 3D'),
    );
    await page.locator('canvas').screenshot();
    const files = await Promise.all(pending);
    results.push({
      route,
      jsFiles: files.length,
      jsDecodedBytes: files.reduce((sum, file) => sum + file.decodedBytes, 0),
      jsGzipEstimateBytes: files.reduce((sum, file) => sum + file.gzipBytes, 0),
      files,
    });
    await context.close();
  }
} finally {
  await browser.close();
}
const report = {
  measuredAt: new Date().toISOString(),
  origin,
  note: 'Full route, initial core scene, fresh context per route. Shared UI included; GLB/HDR/PNG/fonts excluded. Sum of individually gzipped JavaScript responses; actual HTTP transfer compression may differ.',
  results,
};
await mkdir('outputs', { recursive: true });
await writeFile(
  'outputs/engine-route-load.json',
  JSON.stringify(report, null, 2),
);
console.log(
  JSON.stringify(
    results.map(({ files: _files, ...summary }) => summary),
    null,
    2,
  ),
);
