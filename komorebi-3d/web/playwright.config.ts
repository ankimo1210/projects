import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  timeout: 45_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: 'http://localhost:3101',
    viewport: { width: 1440, height: 1000 },
    contextOptions: { reducedMotion: 'reduce' },
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
      args: [
        '--use-gl=angle',
        '--use-angle=swiftshader',
        '--enable-unsafe-swiftshader',
      ],
    },
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run build && npm run start -- --port 3101',
    url: 'http://localhost:3101',
    reuseExistingServer: !process.env.CI,
    timeout: 90_000,
  },
});
