import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Next 16 ya no incluye "next lint": el script lint llama a eslint directamente (D-018).
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "coverage/**",
    "storybook-static/**",
    "next-env.d.ts",
    ".claude/**",
  ]),
]);
