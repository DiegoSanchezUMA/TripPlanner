import { fileURLToPath } from "node:url";

import { vanillaExtractPlugin } from "@vanilla-extract/vite-plugin";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), vanillaExtractPlugin()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    // Los tests viven solo en tests/, nunca junto al código (D-019, sonar-project.properties).
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      reportsDirectory: "coverage",
      include: ["src/**/*.{ts,tsx}"],
      // Estilos y el layout raíz (punto de entrada de Next) no tienen lógica que probar.
      exclude: ["src/**/*.css.ts", "src/app/layout.tsx", "src/**/*.d.ts"],
    },
  },
});
