import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    // Vitest owns `test/**` only. `e2e/**` is Playwright's: collecting a
    // Playwright spec here fails with "test() called here" (R-02).
    include: ['test/**/*.test.ts'],
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
  // Serves converted cockpit assets (assets/generated/webroot) — absent until
  // `pnpm assets:build` runs; the app falls back to temporary geometry.
  publicDir: fileURLToPath(new URL('../../assets/generated/webroot', import.meta.url)),
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    // The initial UI is small; the Babylon cockpit and glTF loader are lazy.
    chunkSizeWarningLimit: 1500,
  },
});
