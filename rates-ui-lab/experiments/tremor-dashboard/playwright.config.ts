import { defineConfig } from "@playwright/test"

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  workers: 1,
  use: {
    baseURL: process.env.RATES_BASE_URL || "http://127.0.0.1:3100",
    viewport: { width: 1440, height: 1000 },
    browserName: "chromium",
    launchOptions: process.env.RATES_CHROMIUM_PATH
      ? { executablePath: process.env.RATES_CHROMIUM_PATH }
      : {},
  },
  reporter: [["list"]],
})
