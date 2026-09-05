import { expect, test, type Page } from '@playwright/test';

const csv =
  'tenor_years,moneyness,iv\n0.25,0.9,0.22\n0.25,1.1,0.25\n2,0.9,0.31\n2,1.1,0.34\n';
const fixture = (name: string, text = csv) => ({
  name,
  mimeType: 'text/csv',
  buffer: Buffer.from(text),
});

// Keep real file contents and parsing; control only asynchronous read completion.
async function deferCsvReads(page: Page) {
  await page.addInitScript(() => {
    const original = Object.getOwnPropertyDescriptor(Blob.prototype, 'text')!
      .value as File['text'];
    File.prototype.text = function () {
      return new Promise<string>((resolve, reject) => {
        window.addEventListener(
          `release-csv:${this.name}`,
          () => {
            original
              .call(this)
              .then(resolve, reject)
              .finally(() => {
                requestAnimationFrame(() =>
                  requestAnimationFrame(() => {
                    window.dispatchEvent(
                      new Event(`finished-csv:${this.name}`),
                    );
                  }),
                );
              });
          },
          { once: true },
        );
      });
    };
  });
}

async function releaseCsv(page: Page, name: string) {
  await page.evaluate(
    (name) =>
      new Promise<void>((resolve) => {
        window.addEventListener(`finished-csv:${name}`, () => resolve(), {
          once: true,
        });
        window.dispatchEvent(new Event(`release-csv:${name}`));
      }),
    name,
  );
}

for (const [name, text] of [
  ['valid.csv', csv],
  ['invalid.csv', 'bad,headers\n1,2'],
]) {
  test(`a late ${name} read cannot replace a later preset choice`, async ({
    page,
  }) => {
    await deferCsvReads(page);
    await page.goto('/volatility');
    await page
      .getByLabel('サーフェスCSV', { exact: true })
      .setInputFiles(fixture(name, text));
    await expect(
      page.getByRole('button', { name: '読み込み中…' }),
    ).toBeDisabled();
    await page.getByRole('button', { name: 'Short-end stress' }).click();
    await releaseCsv(page, name);
    await expect(page.locator('.vol-badge')).toHaveText('模擬データ');
    await expect(page.getByTestId('selected-iv')).toHaveText('32.00');
    await expect(page.getByRole('alert')).toHaveCount(0);
    await expect(
      page.getByRole('button', { name: 'CSVを読み込む' }),
    ).toBeEnabled();
  });
}

test('a stale CSV completion cannot clear a newer pending import', async ({
  page,
}) => {
  await deferCsvReads(page);
  await page.goto('/volatility');
  const input = page.getByLabel('サーフェスCSV', { exact: true });
  await input.setInputFiles(fixture('first.csv'));
  await page.getByRole('button', { name: 'Short-end stress' }).click();
  // Choosing a preset cancels the earlier import and permits a new file.
  await expect(
    page.getByRole('button', { name: 'CSVを読み込む' }),
  ).toBeEnabled();
  await input.setInputFiles(fixture('second.csv', csv.replace('0.22', '0.27')));
  await releaseCsv(page, 'first.csv');
  await expect(
    page.getByRole('button', { name: '読み込み中…' }),
  ).toBeDisabled();
  await expect(page.locator('.vol-badge')).toHaveText('模擬データ');
  await releaseCsv(page, 'second.csv');
  await expect(page.locator('.vol-badge')).toHaveText('CSVデータ');
  await expect(page.getByTestId('selected-iv')).toHaveText('27.00');
  await expect(
    page.getByRole('button', { name: 'CSVを読み込む' }),
  ).toBeEnabled();
});

test('selection sliders expose financial coordinates instead of grid indices', async ({
  page,
}) => {
  await page.goto('/volatility');
  const tenor = page.getByRole('slider', { name: '満期', exact: true });
  const moneyness = page.getByRole('slider', {
    name: 'マネーネス K/F',
    exact: true,
  });
  await expect(tenor).toHaveAttribute('aria-valuetext', '12M');
  await expect(moneyness).toHaveAttribute('aria-valuetext', '100.0%');
  await tenor.press('Home');
  await expect(tenor).toHaveAttribute('aria-valuetext', '1M');
  await page
    .getByLabel('サーフェスCSV', { exact: true })
    .setInputFiles(fixture('quotes.csv'));
  await expect(tenor).toHaveAttribute('aria-valuetext', '3M');
  await expect(moneyness).toHaveAttribute('aria-valuetext', '90.0%');
  await moneyness.press('End');
  await expect(moneyness).toHaveAttribute('aria-valuetext', '110.0%');
});

test('zooming a surface keeps the surrounding page stationary', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto('/volatility');
  for (const [name, engine] of [
    ['Plotly', 'plotly'],
    ['Three.js', 'three'],
    ['Babylon.js', 'babylon'],
  ]) {
    await page.getByRole('tab', { name, exact: true }).click();
    const card = page.locator(
      `.vol-surface-card[data-engine="${engine}"][data-ready="true"]`,
    );
    await expect(card).toHaveCount(1);
    await card.locator('canvas').hover();
    const beforeScroll = await page.evaluate(() => window.scrollY);
    const beforeView = await card.getAttribute('data-view');
    await page.mouse.wheel(0, 200);
    await expect(card).not.toHaveAttribute('data-view', beforeView!);
    // Wait through the browser's scroll/paint, including smooth-scrolling frames.
    await page.waitForTimeout(300);
    expect(
      await page.evaluate(() => window.scrollY),
      `${name} wheel must only zoom`,
    ).toBe(beforeScroll);
  }
});
