import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  // Serves converted cockpit assets (assets/generated/webroot) — absent until
  // `pnpm assets:build` runs; the app falls back to temporary geometry.
  publicDir: fileURLToPath(new URL('../../assets/generated/webroot', import.meta.url)),
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    chunkSizeWarningLimit: 4000, // Babylon.js is large; fine for a local app
  },
});
