import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Repo-root Vitest config for the Wave 0 web test harness.
// jsdom + @testing-library/react; later plans extend coverage.
//
// The React/Testing-Library deps live under apps/web (pnpm scopes them to the
// @veridoc/web package), so `root` is pinned to apps/web for correct module
// resolution. The config file itself lives at the repo root per the plan's
// layout; paths below are resolved relative to apps/web regardless of cwd.
const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "apps/web");

export default defineConfig({
  plugins: [react()],
  test: {
    root: webRoot,
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    setupFiles: [resolve(webRoot, "src/test-setup.ts")],
    css: false,
  },
});
