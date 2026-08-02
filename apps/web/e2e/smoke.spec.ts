import { expect, test } from '@playwright/test';

/**
 * Vertical-slice smoke test (spec §21): boots the real bridge (mock backend)
 * and the real web app, verifies live state streaming, a full command
 * round-trip, and the ATC clearance workflow. No mocked screens.
 */

test('app boots, streams live state, and completes a command round-trip', async ({ page }) => {
  await page.goto('/');

  // 3D canvas + instruments render
  await expect(page.getByTestId('sim-canvas')).toBeVisible();
  await expect(page.getByTestId('pfd')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('nd')).toBeVisible();
  await expect(page.getByTestId('eicas')).toBeVisible();

  // connected to the mock backend
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });

  // state stream is LIVE: sim time advances
  const t1 = await page.getByTestId('sim-time').textContent();
  await page.waitForTimeout(2500);
  const t2 = await page.getByTestId('sim-time').textContent();
  expect(t1).not.toEqual(t2);

  // command round-trip: move the flap lever → backend state reflects it in EICAS
  await expect(page.getByTestId('eicas')).toContainText('handle 5');
  await page.getByTestId('flap-lever').getByRole('button', { name: '10', exact: true }).click();
  await expect(page.getByTestId('eicas')).toContainText('handle 10', { timeout: 5_000 });
  // restore takeoff flaps
  await page.getByTestId('flap-lever').getByRole('button', { name: '5', exact: true }).click();
  await expect(page.getByTestId('eicas')).toContainText('handle 5', { timeout: 5_000 });

  // physically invalid command is rejected by the backend (gear up on ground)
  await page.getByTestId('gear-lever').getByRole('button', { name: 'UP' }).click();
  await expect(page.getByTestId('cmd-rejection')).toContainText('gear lever locked', {
    timeout: 5_000,
  });

  // ATC workflow: request clearance → readback → transcript records it
  await page.getByTestId('request-takeoff').click();
  await expect(page.getByTestId('transcript-list')).toContainText('cleared for takeoff');
  await page
    .getByTestId('response-options')
    .getByRole('button', { name: /Cleared for takeoff runway 28R/ })
    .click();
  await expect(page.getByTestId('transcript-list')).toContainText('✓ readback');

  // checklist panel + guidance visible (guided mode default)
  await expect(page.getByTestId('checklist-panel')).toContainText('Flight controls');
  await expect(page.getByTestId('guidance')).toBeVisible();

  // diagnostics panel hidden by default, opens on demand
  await expect(page.getByTestId('diagnostics')).toHaveCount(0);
  await page.keyboard.press('Backquote');
  await expect(page.getByTestId('diagnostics')).toBeVisible();
  await expect(page.getByTestId('diagnostics')).toContainText('state rate');
});

test('debrief report opens with transparent categories', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await page.getByTestId('debrief-btn').click();
  await expect(page.getByTestId('debrief')).toBeVisible();
  await expect(page.getByTestId('debrief')).toContainText('Takeoff procedure');
  await expect(page.getByTestId('debrief')).toContainText('ATC compliance');
  await expect(page.getByTestId('debrief')).toContainText('NON_CERTIFIED_APPROXIMATION');
});
