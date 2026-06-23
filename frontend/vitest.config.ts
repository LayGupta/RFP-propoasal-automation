/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // jsdom provides a browser-like DOM for React component tests
    environment: 'jsdom',

    // Enable describe/it/expect as globals (no imports needed)
    globals: true,

    // Setup files run before every test file
    setupFiles: ['./src/__tests__/setup.ts'],

    // Skip CSS imports — components import index.css which jsdom can't parse
    css: false,

    // Test file patterns
    include: ['src/**/*.{test,spec}.{ts,tsx}'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/__tests__/**', 'src/vite-env.d.ts', 'src/main.tsx'],
    },
  },
});
