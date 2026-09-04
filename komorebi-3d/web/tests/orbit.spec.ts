import { expect, test, type Page } from '@playwright/test';

async function loadScene(page: Page) {
  await page.goto('/');
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await expect(page.locator('canvas')).toBeVisible();
}

test('real 3D responds to dragging and accessible scene controls', async ({
  page,
  context,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await loadScene(page);
  await expect(
    page.getByRole('button', { name: '自動回転を再生' }),
  ).toBeVisible();
  const canvas = page.locator('canvas');
  const before = await canvas.screenshot();
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Canvas has no bounds');
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.5, {
    steps: 12,
  });
  await page.mouse.up();
  const after = await canvas.screenshot();
  expect(after.equals(before)).toBe(false);

  await page.getByRole('button', { name: '空間をあそぶ' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('switch', { name: 'Wireframe' }).click();
  await page.getByRole('slider').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.config-preview')).toContainText(
    '"rotationSpeed": 1.1',
  );
  await expect(page.locator('.config-preview')).toContainText(
    '"wireframe": true',
  );
  await page.getByRole('button', { name: 'シーン設定をコピー' }).click();
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(JSON.parse(clipboard)).toMatchObject({
    collection: 'core',
    rotationSpeed: 1.1,
    wireframe: true,
  });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: '空間をあそぶ' }),
  ).toBeFocused();
  expect((await canvas.screenshot()).equals(after)).toBe(false);
  await page.getByRole('button', { name: '自動回転を再生' }).click();
  await expect(
    page.getByRole('button', { name: '自動回転を停止' }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test('both Blender assets load and telemetry measures the selected scene', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await loadScene(page);
  await page.locator('.workspace-link').filter({ hasText: 'RESEARCH' }).click();
  const asset = page.waitForResponse((response) =>
    response.url().endsWith('/komorebi.glb'),
  );
  await page.getByRole('button', { name: 'Komorebi caféを表示' }).click();
  expect((await asset).status()).toBe(200);
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await expect(page.locator('.model-name')).toHaveText('Komorebi café');
  await expect(page.locator('.spatial-node')).toHaveCount(0);
  await page.locator('.workspace-link').filter({ hasText: 'DATA' }).click();
  await expect(page.locator('.stats-list dd').first()).not.toHaveText('—');
  expect(
    Number(
      (await page.locator('.stats-list dd').first().innerText()).replaceAll(
        ',',
        '',
      ),
    ),
  ).toBeGreaterThan(100);
  expect(
    Number(await page.locator('.fps-reading strong').innerText()),
  ).toBeGreaterThan(0);
  await page.screenshot({ path: 'outputs/orbit-data.png' });
  await page.keyboard.press('Escape');
  await page.screenshot({ path: 'outputs/orbit-cafe.png', fullPage: true });
  await page.locator('.workspace-link').filter({ hasText: 'RESEARCH' }).click();
  await page.getByRole('button', { name: 'Orbital coreを表示' }).click();
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await expect(page.locator('.spatial-node')).toHaveCount(3);
  await page.getByRole('button', { name: '3Dを大きく表示' }).click();
  await expect(page.locator('main')).toHaveClass(/is-immersive/);
  await page.keyboard.press('Escape');
  await expect(page.locator('main')).not.toHaveClass(/is-immersive/);
  await page.screenshot({ path: 'outputs/orbit-desktop.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('mobile layout fits and touch controls remain usable', async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('http://localhost:3101');
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    390,
  );
  await page.getByRole('button', { name: '空間をあそぶ' }).tap();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('switch', { name: 'Wireframe' }).tap();
  await expect(page.getByRole('switch', { name: 'Wireframe' })).toBeChecked();
  await page.getByRole('button', { name: 'パネルを閉じる' }).tap();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: '空間をあそぶ' }).tap();
  await page.getByRole('switch', { name: 'Wireframe' }).tap();
  await page.getByRole('button', { name: 'パネルを閉じる' }).tap();
  await page.screenshot({ path: 'outputs/orbit-mobile.png', fullPage: true });
  expect(errors).toEqual([]);
  await context.close();
});

test('a failed 3D download leaves a usable preview and clear status', async ({
  page,
}) => {
  await page.route('**/orbit-core.glb', (route) => route.abort());
  await page.goto('/');
  await expect(page.locator('.scene-index')).toContainText('PREVIEW MODE');
  await expect(page.locator('.scene-fallback')).not.toHaveClass(/is-hidden/);
  await expect(
    page.getByText('3Dを読み込めませんでした。プレビュー画像でご覧ください。'),
  ).toBeVisible();
  await page.locator('.workspace-link').filter({ hasText: 'RESEARCH' }).click();
  await expect(
    page.getByRole('button', { name: 'Komorebi caféを表示' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Komorebi caféを表示' }).click();
  await expect(page.locator('.scene-index')).toContainText('LIVE 3D');
  await expect(page.locator('.model-name')).toHaveText('Komorebi café');
});
