import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const ready = '.vol-surface-card[data-ready="true"]';
const csv =
  'tenor_years,moneyness,iv\n2,1.1,0.34\n0.25,0.9,0.22\n2,0.9,0.31\n0.25,1.1,0.25\n';
const fixture = (text: string) => ({
  name: 'surface.csv',
  mimeType: 'text/csv',
  buffer: Buffer.from(text),
});
async function drag(page: Page, engine: string) {
  const box = await page
    .locator(`.vol-surface-card[data-engine="${engine}"] .vol-canvas`)
    .boundingBox();
  if (!box) throw new Error('Surface has no viewport');
  await page.mouse.move(box.x + box.width * 0.48, box.y + box.height * 0.48);
  await page.mouse.down();
  // Exercise a real gesture across camera interpolation and rendered frames.
  for (let step = 1; step <= 8; step++) {
    await page.mouse.move(
      box.x + box.width * (0.48 + (0.22 * step) / 8),
      box.y + box.height * (0.48 + (0.07 * step) / 8),
    );
    await page.evaluate(
      () =>
        new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        ),
    );
  }
  await page.mouse.up();
  await page.mouse.move(5, 5);
}

test('demo quotes and slices follow keyboard selection, preset and parameter changes', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto('/volatility');
  await expect(page.locator(ready)).toHaveCount(1);
  await expect(page.getByTestId('selected-iv')).toHaveText('20.00');
  const tenor = page.getByRole('slider', { name: '満期', exact: true });
  await tenor.press('Home');
  await tenor.press('ArrowRight');
  await tenor.press('ArrowRight');
  await expect(page.getByTestId('selected-tenor')).toHaveText('3M');
  await expect(page.getByTestId('selected-iv')).toHaveText('18.50');
  await expect(page.getByTestId('smile-slice').locator('svg')).toHaveAttribute(
    'aria-label',
    /3M.*18.50%/,
  );
  const shapeBefore = await page
    .getByTestId('smile-slice')
    .locator('path[stroke]')
    .getAttribute('d');
  await page.getByRole('button', { name: 'Symmetric smile' }).click();
  await expect(page.getByTestId('selected-iv')).toHaveText('17.00');
  await expect(
    page.getByTestId('smile-slice').locator('path[stroke]'),
  ).not.toHaveAttribute('d', shapeBefore!);
  await page
    .getByRole('slider', { name: 'ATM・1年', exact: true })
    .press('ArrowRight');
  await expect(page.getByTestId('selected-iv')).toHaveText('18.00');
  for (const [name, engine] of [
    ['Three.js', 'three'],
    ['Babylon.js', 'babylon'],
  ]) {
    await page.getByRole('tab', { name, exact: true }).click();
    await expect(page.locator(`${ready}[data-engine="${engine}"]`)).toHaveCount(
      1,
    );
    await expect(page.getByTestId('selected-iv')).toHaveText('18.00');
  }
  expect(errors).toEqual([]);
});

test('all three real canvases respond to synchronized cameras and wireframe', async ({
  page,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/volatility');
  await page.getByRole('tab', { name: '3つ比較' }).click();
  await expect(page.locator(ready)).toHaveCount(3);
  const cards = page.locator('.vol-surface-card');
  expect(
    new Set(
      await cards.evaluateAll((es) =>
        es.map((el) => el.getAttribute('data-grid-id')),
      ),
    ).size,
  ).toBe(1);
  const canvases = cards.locator('canvas');
  await expect(canvases).toHaveCount(3);
  for (const engine of ['three', 'babylon', 'plotly']) {
    const beforeView = await cards.first().getAttribute('data-view');
    const beforeQuote = await page.getByTestId('selected-iv').innerText();
    const before: Buffer[] = [];
    for (let i = 0; i < 3; i++) before.push(await canvases.nth(i).screenshot());
    await drag(page, engine);
    await expect(
      cards.first(),
      `${engine} drag must update the shared camera`,
    ).not.toHaveAttribute('data-view', beforeView!);
    await expect(page.getByTestId('selected-iv')).toHaveText(beforeQuote);
    expect(
      new Set(
        await cards.evaluateAll((es) =>
          es.map((el) => el.getAttribute('data-view')),
        ),
      ).size,
    ).toBe(1);
    for (let i = 0; i < 3; i++)
      await expect
        .poll(async () =>
          (await canvases.nth(i).screenshot()).equals(before[i]),
        )
        .toBe(false);
  }
  const plotlyCanvas = cards.first().locator('canvas');
  await plotlyCanvas.hover();
  for (let i = 0; i < 2; i++) {
    await page.mouse.wheel(0, 2500);
    await expect(cards.first()).toHaveAttribute('data-view', /,22\.000$/);
    await expect
      .poll(() =>
        page.locator('.vol-plotly-scene').evaluate((el) => {
          const graph = el as HTMLElement & {
            _fullLayout: {
              scene: {
                _scene: {
                  getCamera: () => { eye: { x: number; y: number; z: number } };
                };
              };
            };
          };
          const eye = graph._fullLayout.scene._scene.getCamera().eye;
          return Math.hypot(eye.x, eye.y, eye.z);
        }),
      )
      .toBeCloseTo(22, 2);
  }
  await page.getByRole('button', { name: '視点リセット' }).click();
  await expect(cards.first()).toHaveAttribute(
    'data-view',
    '-0.820,0.560,11.800',
  );
  const solid: Buffer[] = [];
  for (let i = 0; i < 3; i++) solid.push(await canvases.nth(i).screenshot());
  await page.getByRole('switch', { name: 'ワイヤー' }).click();
  for (let i = 0; i < 3; i++)
    await expect
      .poll(async () => (await canvases.nth(i).screenshot()).equals(solid[i]))
      .toBe(false);
  await page.getByRole('switch', { name: 'ワイヤー' }).click();
  await page.getByRole('button', { name: 'Short-end stress' }).click();
  await expect(page.locator(ready)).toHaveCount(3);
  await page.screenshot({
    path: 'outputs/volatility-comparison.png',
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test('each renderer supports native hover and point selection', async ({
  page,
}) => {
  await page.goto('/volatility');
  for (const [name, engine] of [
    ['Plotly', 'plotly'],
    ['Three.js', 'three'],
    ['Babylon.js', 'babylon'],
  ]) {
    await page.getByRole('tab', { name, exact: true }).click();
    const card = page.locator(`.vol-surface-card[data-engine="${engine}"]`);
    await expect(card).toHaveAttribute('data-ready', 'true');
    const box = await card.locator('.vol-canvas').boundingBox();
    if (!box) throw new Error('Missing surface');
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.63);
    await expect(page.locator('.vol-hover-readout')).toContainText('カーソル');
    const readout = await page.locator('.vol-hover-readout').innerText();
    const quote = readout.match(/IV ([\d.]+)%/)?.[1];
    expect(quote).toBeDefined();
    // Plotly's native gl3d click is sampled on a render frame while the button is down.
    await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.63, {
      delay: 120,
    });
    await expect(page.getByTestId('selected-iv')).toHaveText(quote!);
  }
});

test('initially unavailable WebGL leaves an accessible numerical viewer', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = Object.getOwnPropertyDescriptor(
      HTMLCanvasElement.prototype,
      'getContext',
    )!.value as typeof HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      kind: string,
      ...args: unknown[]
    ) {
      if (kind.startsWith('webgl') || kind === 'experimental-webgl')
        return null;
      return Reflect.apply(original, this, [kind, ...args]);
    } as typeof original;
  });
  await page.goto('/volatility');
  await page.getByRole('tab', { name: 'Three.js', exact: true }).click();
  await expect(page.locator('.vol-unavailable')).toContainText(
    '3Dの描画に失敗',
  );
  await expect(page.locator('.vol-loading')).toHaveCount(0);
  await expect(page.getByTestId('selected-iv')).toHaveText('20.00');
  await page.getByRole('slider', { name: '満期', exact: true }).press('Home');
  await expect(page.getByTestId('selected-tenor')).toHaveText('1M');
});

test('CSV quotes remain exact, invalid uploads preserve the view, and export round trips', async ({
  page,
}) => {
  await page.goto('/volatility');
  await expect(page.locator(ready)).toHaveCount(1);
  const input = page.getByLabel('サーフェスCSV', { exact: true });
  await input.setInputFiles(fixture(csv));
  await expect(page.locator('.vol-badge')).toHaveText('CSVデータ');
  await expect(page.getByTestId('selected-iv')).toHaveText('22.00');
  await expect(
    page.getByRole('slider', { name: 'ATM・1年', exact: true }),
  ).toBeDisabled();
  await page.getByRole('slider', { name: '満期', exact: true }).press('End');
  await page
    .getByRole('slider', { name: 'マネーネス K/F', exact: true })
    .press('End');
  await expect(page.getByTestId('selected-iv')).toHaveText('34.00');
  await expect
    .poll(() =>
      page
        .locator('.vol-plotly-scene')
        .evaluate(
          (el) =>
            (el as HTMLElement & { data?: { z: number[][] }[] }).data?.[0]?.z,
        ),
    )
    .toEqual([
      [22, 25],
      [31, 34],
    ]);
  await expect(page.getByTestId('term-slice').locator('svg')).toHaveAttribute(
    'aria-label',
    /110.0%.*34.00%/,
  );
  const id = await page.locator(ready).getAttribute('data-grid-id');
  await input.setInputFiles(fixture(csv + '2,1.1,0.9\n'));
  await expect(page.getByRole('alert')).toContainText('重複');
  await expect(page.locator(ready)).toHaveAttribute('data-grid-id', id!);
  await expect(page.getByTestId('selected-iv')).toHaveText('34.00');
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'CSVを保存' }).click();
  const path = await (await downloaded).path();
  expect(await readFile(path!, 'utf8')).toBe(
    'tenor_years,moneyness,iv\n0.25,0.9,0.22\n0.25,1.1,0.25\n2,0.9,0.31\n2,1.1,0.34\n',
  );
  await page.getByRole('button', { name: 'Equity smile', exact: true }).click();
  await expect(page.locator('.vol-badge')).toHaveText('模擬データ');
  await expect(
    page.getByRole('slider', { name: 'ATM・1年', exact: true }),
  ).toBeEnabled();
});

test('mobile viewer fits the page and the numerical view survives WebGL loss', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/volatility');
  await expect(page.locator(ready)).toHaveCount(1);
  await page.screenshot({
    path: 'outputs/volatility-mobile.png',
    fullPage: true,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.getByRole('tab', { name: 'Three.js', exact: true }).click();
  await expect(page.locator(`${ready}[data-engine="three"]`)).toHaveCount(1);
  await page
    .locator('.vol-canvas canvas')
    .evaluate((canvas) => canvas.dispatchEvent(new Event('webglcontextlost')));
  await expect(page.locator('.vol-unavailable')).toContainText(
    '3Dの描画に失敗',
  );
  await page.getByRole('slider', { name: '満期', exact: true }).press('Home');
  await expect(page.getByTestId('selected-tenor')).toHaveText('1M');
  await expect(page.getByTestId('smile-slice').locator('svg')).toHaveAttribute(
    'aria-label',
    /1M/,
  );
  await page.getByRole('tab', { name: 'Babylon.js', exact: true }).click();
  await expect(page.locator(`${ready}[data-engine="babylon"]`)).toHaveCount(1);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});
