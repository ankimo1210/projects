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

test('imported 3D cockpit loads and 3D picking round-trips (skipped without assets)', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  // wait for the cockpit; skip cleanly when assets were not built (fallback shell)
  const loaded = await page
    .waitForFunction(
      () =>
        Number(
          document
            .querySelector('[data-testid="sim-canvas"]')
            ?.getAttribute('data-cockpit-meshes') ?? 0,
        ) > 0,
      undefined,
      { timeout: 20_000 },
    )
    .then(() => true)
    .catch(() => false);
  test.skip(!loaded, 'converted cockpit assets not present (run pnpm assets:build)');

  const meshCount = Number(
    await page.getByTestId('sim-canvas').getAttribute('data-cockpit-meshes'),
  );
  expect(meshCount).toBeGreaterThan(500);

  // R-11: the FlightGear assembly rotations must actually reach the scene.
  const assembly = await page.evaluate(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scene = (window as never as { __simScene: any }).__simScene;
    const centerOf = (name: string): { x: number; y: number; z: number } | null => {
      const node = scene.getNodeByName(name);
      if (!node) return null;
      node.computeWorldMatrix(true);
      const hb = node.getHierarchyBoundingVectors(true);
      const c = hb.min.add(hb.max).scale(0.5);
      return { x: c.x, y: c.y, z: c.z };
    };
    const tilt = (name: string): number | null => {
      const node = scene.getTransformNodeByName(name);
      const q = node?.rotationQuaternion;
      if (!q) return null;
      return (2 * Math.acos(Math.min(1, Math.abs(q.w))) * 180) / Math.PI;
    };
    return {
      flightdeskTiltDeg: tilt('inst:cockpit/flightdesk_0:chain0'),
      overheadTiltDeg: tilt('inst:cockpit/Overhead_1:chain0'),
      overhead: centerOf('inst:cockpit/Overhead_1'),
      flightdesk: centerOf('inst:cockpit/flightdesk_0'),
    };
  });
  // the flightdesk is mounted at -15°, the overhead at 90/90
  expect(assembly.flightdeskTiltDeg).toBeCloseTo(15, 0);
  expect(assembly.overheadTiltDeg ?? 0).toBeGreaterThan(45);
  // and the assembled panels land where a 737 flight deck has them: the
  // overhead above the captain's eye datum (floor 2.55 m + 1.2 m), clearly
  // above the main panel
  expect(assembly.overhead!.y).toBeGreaterThan(3.8);
  expect(assembly.overhead!.y).toBeGreaterThan(assembly.flightdesk!.y + 0.4);

  // project the 3D gear lever to screen coords and click it — on the ground
  // the backend must REJECT the command (full 3D→bridge→backend round trip)
  const screenPos = await page.evaluate(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scene = (window as never as { __simScene: any }).__simScene;
    const node = scene.getNodeByName('lghandle');
    if (!node) return null;
    node.computeWorldMatrix(true);
    // click the visible geometry: hierarchy bounding-box center, not the node origin
    const hb = node.getHierarchyBoundingVectors(true);
    const p = hb.min.add(hb.max).scale(0.5);
    const V = p.constructor;
    const M = scene.getTransformMatrix().constructor;
    const engine = scene.getEngine();
    const projected = V.Project(
      p,
      M.Identity(),
      scene.getTransformMatrix(),
      scene.activeCamera.viewport.toGlobal(engine.getRenderWidth(), engine.getRenderHeight()),
    );
    // projection is in backing-store pixels; convert to CSS pixels for the click
    return {
      x: projected.x,
      y: projected.y,
      renderW: engine.getRenderWidth(),
      renderH: engine.getRenderHeight(),
    };
  });
  expect(screenPos).not.toBeNull();
  const canvas = await page.getByTestId('sim-canvas').boundingBox();
  await page.mouse.click(
    canvas!.x + (screenPos!.x * canvas!.width) / screenPos!.renderW,
    canvas!.y + (screenPos!.y * canvas!.height) / screenPos!.renderH,
  );
  await expect(page.getByTestId('cmd-rejection')).toContainText('gear lever locked', {
    timeout: 5_000,
  });

  // Every mesh the control registry claims must exist in the imported cockpit,
  // and must be pickable — otherwise a control is silently dead in 3D.
  const registry = await page.evaluate(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scene = (window as never as { __simScene: any }).__simScene;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const controls = (window as never as { __simControls: any[] }).__simControls;
    return controls
      .flatMap((c) => c.meshNames.map((name: string) => ({ control: c.id, name })))
      .map(({ control, name }) => {
        const node = scene.getNodeByName(name);
        const meshes = node
          ? [node, ...node.getChildMeshes(false)].filter(
              (n: { isPickable?: boolean }) => n.isPickable !== undefined,
            )
          : [];
        return {
          control,
          name,
          found: node !== null,
          pickable: meshes.some((m: { isPickable?: boolean }) => m.isPickable === true),
        };
      });
  });
  expect(registry.length).toBeGreaterThan(5);
  expect(registry.filter((r) => !r.found)).toEqual([]);
  expect(registry.filter((r) => !r.pickable)).toEqual([]);
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
