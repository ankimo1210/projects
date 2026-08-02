import { defineConfig } from '@playwright/test';

// CI must start its own servers so a stale dev server cannot mask a failure.
const reuseExistingServer = !process.env.CI;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    viewport: { width: 1600, height: 1000 },
  },
  webServer: [
    {
      command: 'pnpm --filter @b737/bridge start',
      url: 'http://127.0.0.1:8737/health',
      reuseExistingServer,
      timeout: 30_000,
    },
    {
      command: 'pnpm --filter @b737/web dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer,
      timeout: 30_000,
    },
  ],
});
