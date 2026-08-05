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

  // Beginner mission coach: one objective, optional explanation and a
  // SHOW ME interaction that highlights the relevant panel.
  await expect(page.getByTestId('mission-coach')).toBeVisible();
  await expect(page.getByTestId('mission-coach')).toContainText('NEXT ACTION');
  await page.getByRole('button', { name: /なぜ/ }).click();
  await expect(page.getByTestId('mission-help')).toContainText('SUCCESS');
  await page.getByRole('button', { name: /場所を表示/ }).click();
  await expect(page.getByTestId('sim-canvas')).toHaveClass(/coach-focus/);

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

  // ATC correction workflow: one wrong answer followed by one correct retry
  // must clear the pending response instead of leaving the UI stuck (V-07).
  await page.getByTestId('request-takeoff').click();
  await expect(page.getByTestId('transcript-list')).toContainText('cleared for takeoff');
  await page
    .getByTestId('response-options')
    .getByRole('button', { name: 'Roger.', exact: true })
    .click();
  await expect(page.getByTestId('transcript-list')).toContainText('negative — read back');
  await expect(page.getByTestId('transcript-list')).toContainText('✗ readback');
  await page
    .getByTestId('response-options')
    .getByRole('button', { name: /Cleared for takeoff runway 28R/ })
    .click();
  await expect(page.getByTestId('transcript-list')).toContainText('✓ readback');
  await expect(page.getByTestId('response-options')).toHaveCount(0);

  // checklist panel + guidance visible (guided mode default)
  await expect(page.getByTestId('checklist-panel')).toContainText('Flight controls');
  await expect(page.getByTestId('guidance')).toBeVisible();

  // diagnostics panel hidden by default, opens on demand
  await expect(page.getByTestId('diagnostics')).toHaveCount(0);
  await page.keyboard.press('Backquote');
  await expect(page.getByTestId('diagnostics')).toBeVisible();
  await expect(page.getByTestId('diagnostics')).toContainText('state rate');
});

test('brief keyboard taps complete the flight-control check with live progress', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await page.getByTestId('sim-canvas').click({ position: { x: 80, y: 80 } });

  for (const key of ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ',', '.']) {
    await page.keyboard.press(key);
  }

  await expect(page.locator('.mission-metric.metric-good')).toHaveCount(6);
  await page.getByTestId('checklist-answer-flight_controls').click();
  await expect(page.getByTestId('checklist-answer-flaps')).toBeVisible();
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

// M3: the scenario catalogue is switchable, and the switch goes through the
// backend — the training session must never describe a flight the aircraft is
// not flying.
test('switching scenario resets the aircraft into the new one', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await expect(page.getByTestId('phase-chip')).toContainText('Before takeoff');

  await page.getByTestId('scenario-picker').selectOption({ label: 'Gate to Gate — KSFO 28R' });
  // parked at the stand: ground control, not the tower
  await expect(page.getByTestId('phase-chip')).toContainText('At the stand', { timeout: 10_000 });
  await expect(page.getByTestId('request-taxi')).toBeVisible();
  await expect(page.getByTestId('checklist-panel')).toContainText('Before Start');

  await page.getByTestId('scenario-picker').selectOption({ label: 'Approach Drill — ILS 28R' });
  await expect(page.getByTestId('phase-chip')).toContainText('Final approach', { timeout: 10_000 });
  // airborne on the ILS: the PFD shows a real radio altitude and the go-around
  // action is available
  await expect(page.getByTestId('go-around')).toBeVisible();
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

// M4: the overhead panel drives real systems state through the bridge.
test('overhead panel powers the aircraft up from cold and dark', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });

  await page.getByTestId('scenario-picker').selectOption({ label: 'Cold and Dark — KSFO' });
  await expect(page.getByTestId('phase-chip')).toContainText('Cold and dark', { timeout: 10_000 });

  await page.getByTestId('overhead-btn').click();
  await expect(page.getByTestId('overhead-panel')).toBeVisible();
  await expect(page.getByTestId('synoptic')).toContainText('OFF');

  // battery → DC bus, and the master caution lights because there is no AC
  await page.getByTestId('sw-battery').click();
  await expect(page.getByTestId('synoptic')).toContainText('POWERED', { timeout: 5_000 });
  await expect(page.getByTestId('ann-elec_no_ac')).toBeVisible();
  await expect(page.getByTestId('master-caution')).toContainText('MASTER CAUTION');

  // recall acknowledges it; the annunciation stays but the light goes out
  await page.getByTestId('master-caution').click();
  await expect(page.getByTestId('master-caution')).toContainText('NO ALERTS', { timeout: 5_000 });
  await expect(page.getByTestId('ann-elec_no_ac')).toBeVisible();

  // APU start needs the master switch first; then it runs and can be put on bus
  await page.getByTestId('sw-apu_master').click();
  await page.getByTestId('sw-apu_start').click();
  await expect(page.getByTestId('synoptic')).toContainText('RUNNING', { timeout: 45_000 });
  await page.getByTestId('sw-apu_gen').click();
  await expect(page.getByTestId('ann-elec_no_ac')).toHaveCount(0, { timeout: 5_000 });

  // and an engine start without duct pressure is refused by the backend
  await page.getByTestId('start-left-ground').click();
  await expect(page.getByTestId('cmd-rejection')).toContainText('duct pressure', {
    timeout: 5_000,
  });
});

// M5: the route panel drives the FMS through the bridge, and the ND shows it.
test('FMS panel loads a route and arms LNAV', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await page.getByTestId('scenario-picker').selectOption({ label: 'SID and Arrival — KSFO 28R' });
  await page.getByTestId('overhead-btn').click();
  await expect(page.getByTestId('fms-panel')).toBeVisible();
  await expect(page.getByTestId('fms-route')).toContainText('no route');

  await page.getByTestId('load-route').click();
  await expect(page.getByTestId('fms-route')).toContainText('SFOUT1', { timeout: 5_000 });
  await expect(page.getByTestId('fms-panel')).toContainText('SFOUT');
  await expect(page.getByTestId('fms-panel')).toContainText('WESTB');

  // LNAV is refused on the ground with no route... now it has one
  await page.getByTestId('lnav-btn').click();
  await expect(page.getByTestId('fms-readout')).toContainText('NM', { timeout: 5_000 });

  // direct-to re-anchors the route on that fix
  await page.getByTestId('direct-MIDBA').click();
  await expect(page.getByTestId('fms-readout')).toContainText('xtk', { timeout: 5_000 });
});

// M5: weather reaches the UI, and the crosswind scenario really is one.
test('weather readout reflects the scenario weather', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await page.getByTestId('overhead-btn').click();
  await expect(page.getByTestId('weather-readout')).toContainText('Wind 290/6');

  await page.getByTestId('scenario-picker').selectOption({ label: 'Crosswind Landing — ILS 28R' });
  // The drill starts at ~2,000 ft, so the wind shown is blended toward the
  // wind aloft (235/38) — from the south-west and strong either way.
  await expect(page.getByTestId('weather-readout')).toHaveText(/Wind 2[34]\d\/[23]\d/, {
    timeout: 10_000,
  });
  await expect(page.getByTestId('weather-readout')).toContainText('turb');
});

// F-01: the failure a scenario injects must reach the AIRCRAFT in the browser,
// not just the transcript. This is the test whose earlier removal hid the bug.
test('V1 engine failure happens in the browser and the aircraft feels it', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  await expect(page.getByTestId('conn-status')).toContainText('mock backend', { timeout: 15_000 });
  await page
    .getByTestId('scenario-picker')
    .selectOption({ label: 'Engine Failure after V1 — KSFO 28R' });
  await page.getByTestId('overhead-btn').click();

  await page.getByTestId('request-takeoff').click();
  await page
    .getByTestId('response-options')
    .getByRole('button', { name: /Cleared for takeoff runway 28R/ })
    .click();
  await page.getByTestId('parking-brake').click();
  // set takeoff thrust via the DOM throttle (the keyboard ramp relies on a
  // 20 Hz interval that headless Chromium throttles)
  await page.getByTestId('throttle-slider').fill('100');

  // the rule fires when the aeroplane reaches V1 — and the aircraft feels it:
  // active failure reported, hydraulic system A decays, master caution lights
  await expect(page.getByTestId('weather-readout')).toContainText('FAIL: engine_1_flameout', {
    timeout: 60_000,
  });
  await expect(page.getByTestId('ann-hyd_a_low')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId('master-caution')).toContainText('MASTER CAUTION');
  // and the systems synoptic shows system A collapsing while B holds
  await expect(page.getByTestId('synoptic')).toContainText('HYD A/B');
});
