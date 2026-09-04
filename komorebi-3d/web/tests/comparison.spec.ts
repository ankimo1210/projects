import { expect, test } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const views = '.engine-view[data-ready="true"]';

test('both engines share assets, synchronized rotation, wireframe, and café switching', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/compare');
  await expect(page.locator(views)).toHaveCount(2);
  await expect(page.locator('.engine-readout').first()).toContainText('15,344');
  await expect(page.locator('.engine-readout').last()).toContainText('15,344');
  const canvases = page.locator('canvas');
  const before = await Promise.all([
    canvases.nth(0).screenshot(),
    canvases.nth(1).screenshot(),
  ]);
  const surface = page.locator('.compare-canvas').first();
  const box = await surface.boundingBox();
  if (!box) throw new Error('No comparison surface');
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.6, {
    steps: 10,
  });
  await page.mouse.up();
  await expect(
    page.getByRole('slider', { name: /横方向/ }),
  ).not.toHaveAttribute('aria-valuenow', '0');
  for (let index = 0; index < 2; index++)
    expect((await canvases.nth(index).screenshot()).equals(before[index])).toBe(
      false,
    );
  await page.getByRole('button', { name: '両方の角度をリセット' }).click();
  await expect(page.getByRole('slider', { name: /横方向/ })).toHaveAttribute(
    'aria-valuenow',
    '0',
  );
  await page
    .getByRole('switch', { name: '両方をワイヤーフレーム表示' })
    .click();
  await expect(page.getByRole('switch')).toBeChecked();
  await page.getByRole('switch').click();
  await page.screenshot({
    path: 'outputs/orbit-comparison.png',
    fullPage: true,
  });
  await page.getByRole('tab', { name: /Komorebi/ }).click();
  await expect(page.locator(views)).toHaveCount(2);
  await expect(page.locator('.engine-readout').first()).toContainText('655');
  await expect(page.locator('.engine-readout').last()).toContainText('655');
  const readouts = await page.locator('.engine-readout').allTextContents();
  expect(readouts[0]).toBe(readouts[1]);
  await page.screenshot({
    path: 'outputs/orbit-comparison-cafe.png',
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test('benchmark renders only one engine at a time and reports matching buffer sizes', async ({
  page,
}) => {
  test.setTimeout(90000);
  await page.goto('/compare');
  await expect(page.locator(views)).toHaveCount(2);
  await page.getByRole('button', { name: 'この端末で計測する' }).click();
  await expect(page.locator('canvas')).toHaveCount(1);
  await expect(page.getByRole('tab', { name: /Komorebi/ })).toBeDisabled();
  await expect(page.getByRole('switch')).toBeDisabled();
  await expect(page.getByText('Babylon.js を計測中…')).toBeVisible({
    timeout: 40000,
  });
  await expect(page.locator('canvas')).toHaveCount(1);
  await expect(page.getByTestId('three-fps')).not.toHaveText('—fps', {
    timeout: 40000,
  });
  const three = parseFloat(await page.getByTestId('three-fps').innerText());
  const babylon = parseFloat(await page.getByTestId('babylon-fps').innerText());
  expect(three).toBeGreaterThan(0);
  expect(babylon).toBeGreaterThan(0);
  const dimensions = await page
    .getByRole('row')
    .filter({ hasText: '描画バッファ' })
    .locator('td')
    .allTextContents();
  expect(dimensions[0]).toMatch(/\d+ × \d+/);
  expect(dimensions[0]).toBe(dimensions[1]);
  await expect(page.locator(views)).toHaveCount(2);
  await writeFile(
    'outputs/engine-comparison-measurement.json',
    JSON.stringify(
      {
        measuredAt: new Date().toISOString(),
        browser: 'Chromium / SwiftShader',
        collection: 'core',
        threeFps: three,
        babylonFps: babylon,
        dimensions,
        table: await page.locator('.measurement-table').innerText(),
        gpu: await page.locator('.gpu-info').innerText(),
      },
      null,
      2,
    ),
  );
  await page.screenshot({
    path: 'outputs/orbit-comparison-measured.png',
    fullPage: true,
  });
  // Resizing must invalidate the current run and discard partial measurements.
  await page.getByRole('button', { name: 'この端末で計測する' }).click();
  await expect(page.locator('canvas')).toHaveCount(1);
  await page.setViewportSize({ width: 1200, height: 900 });
  await expect(
    page.getByText('画面サイズが変わったため計測を中止しました。'),
  ).toBeVisible();
  await expect(page.getByTestId('three-fps')).toHaveText('—fps');
});

test('Babylon version keeps the original site controls and recovers from a failed asset', async ({
  page,
}) => {
  await page.route('**/orbit-core.glb', (route) => route.abort());
  await page.goto('/babylon');
  await expect(page.locator('.scene-index')).toContainText('PREVIEW MODE');
  await expect(page.locator('.scene-fallback')).not.toHaveClass(/is-hidden/);
  await page.locator('.workspace-link').filter({ hasText: 'RESEARCH' }).click();
  await page.getByRole('button', { name: 'Komorebi caféを表示' }).click();
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await page.unroute('**/orbit-core.glb');
  await page.locator('.workspace-link').filter({ hasText: 'RESEARCH' }).click();
  await page.getByRole('button', { name: 'Orbital coreを表示' }).click();
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await expect(page.locator('.spatial-node')).toHaveCount(3);
  await page.getByRole('button', { name: 'CODEを開く', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('switch', { name: 'Wireframe' }).click();
  await expect(page.locator('.config-preview')).toContainText(
    '"wireframe": true',
  );
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '自動回転を再生' }).click();
  await expect(
    page.getByRole('button', { name: '自動回転を停止' }),
  ).toBeVisible();
  await page.getByRole('button', { name: '自動回転を停止' }).click();
  await page.getByRole('button', { name: 'CODEを開く', exact: true }).click();
  await page.getByRole('switch', { name: 'Wireframe' }).click();
  await page.keyboard.press('Escape');
  await page.screenshot({ path: 'outputs/orbit-babylon.png', fullPage: true });
});

test('comparison fits mobile and keyboard sliders control both engines', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/compare');
  await expect(page.locator(views)).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    390,
  );
  await page.getByRole('slider', { name: /横方向/ }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('slider', { name: /横方向/ })).toHaveAttribute(
    'aria-valuenow',
    '1',
  );
  await page.screenshot({
    path: 'outputs/orbit-comparison-mobile.png',
    fullPage: true,
  });
});

for (const engine of ['three', 'babylon'] as const) {
  test(`lost WebGL context aborts ${engine} measurement`, async ({ page }) => {
    await page.goto('/compare');
    await expect(page.locator(views)).toHaveCount(2);
    await page.getByRole('button', { name: 'この端末で計測する' }).click();
    const name = engine === 'three' ? 'Three.js' : 'Babylon.js';
    await expect(page.getByText(`${name} を計測中…`)).toBeVisible();
    const view = page.locator(`.engine-view[data-engine="${engine}"]`);
    await expect(view).toHaveAttribute('data-ready', 'true');
    await view.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
      const gl = canvas.getContext('webgl2');
      const extension = gl?.getExtension('WEBGL_lose_context');
      if (!extension)
        throw new Error('Context loss test extension unavailable');
      extension.loseContext();
    });
    await expect(
      page.getByText(
        '3Dを読み込めませんでした。作品を切り替えて再試行できます。',
      ),
    ).toBeVisible({ timeout: 3000 });
    await expect(page.getByTestId('three-fps')).toHaveText('—fps');
    await expect(page.getByTestId('babylon-fps')).toHaveText('—fps');
  });
}
