// Test config is kept separate from vite.config.ts on purpose: vitest 3.2
// bundles its own Rollup-based Vite, while this project builds on Vite 8
// (Rolldown). Sharing one config file makes the two `Plugin` types collide.
// This file is excluded from `tsc -b` for the same reason.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
