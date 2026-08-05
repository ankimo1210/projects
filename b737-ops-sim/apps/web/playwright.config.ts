import { defineConfig } from '@playwright/test';

// CI must start its own servers so a stale dev server cannot mask a failure.
const reuseExistingServer = !process.env.CI;
const webUrl = process.env.E2E_WEB_URL ?? 'http://127.0.0.1:5173';
const bridgeHealthUrl = process.env.E2E_BRIDGE_HEALTH_URL ?? 'http://127.0.0.1:8737/health';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: webUrl,
    viewport: { width: 1600, height: 1000 },
  },
  webServer: [
    {
      command: 'pnpm --filter @b737/bridge start',
      url: bridgeHealthUrl,
      reuseExistingServer,
      timeout: 30_000,
    },
    {
      command: 'pnpm --filter @b737/web dev',
      url: webUrl,
      reuseExistingServer,
      timeout: 30_000,
    },
  ],
});
