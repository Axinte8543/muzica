import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // cast plugin to any to satisfy type differences between Vite and plugin versions
  plugins: [react() as any],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setupTests.ts"],
    include: ["tests/unit/**/*.test.{js,jsx,ts,tsx}"],
  },
});
