/**
 * setup.ts — Vitest Global Setup
 *
 * Runs before every test file. Configures:
 *   - @testing-library/jest-dom matchers (toBeInTheDocument, etc.)
 *   - Global fetch mock
 *   - ResizeObserver polyfill (needed by Recharts)
 */

import '@testing-library/jest-dom';

// ── Mock ResizeObserver (Recharts uses it, jsdom doesn't provide it) ──
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// ── Mock matchMedia (jsdom doesn't support it) ──
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
