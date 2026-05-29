import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    viewport: { width: 1280, height: 720 },
  },
  webServer: {
    command: "node scripts/e2e-server.mjs",
    port: 5173,
    timeout: 180_000,
    reuseExistingServer: false,
  },
});
