import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: { allowedHosts: ['frontend', 'localhost'] },
  build: {
    // Vite inlines small files as data: URLs; the runtime CSP allows fonts only from
    // this origin, so fonts (including KaTeX's smallest) stay as separate files.
    assetsInlineLimit: (file) =>
      /\.(woff2?|ttf|otf)$/.test(file) ? false : undefined,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    restoreMocks: true,
  },
});
