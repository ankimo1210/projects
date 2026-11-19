import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  server: { port: 5183, strictPort: false },
  preview: { port: 5184 },
  build: { target: "es2022", chunkSizeWarningLimit: 1200 },
  test: {
    include: ["tests/**/*.test.ts"],
    testTimeout: 60_000,
  },
});
