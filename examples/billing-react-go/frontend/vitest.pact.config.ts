// Separate vitest config for Pact consumer tests:
// - runs in Node (no jsdom) so Pact's mock server works
// - excludes the MSW setup
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    include: ['src/**/*.consumer.test.ts'],
    testTimeout: 30_000,
  },
});
