import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";

// Next 16 ya no incluye "next lint": el script lint llama a eslint directamente (D-018).
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  // El formato es cosa de Prettier: apaga las reglas de estilo de ESLint que
  // chocarían con él. Va después de las demás configuraciones (D-029).
  prettier,
  globalIgnores([
    ".next/**",
    "out/**",
    "coverage/**",
    "storybook-static/**",
    "next-env.d.ts",
    ".claude/**",
  ]),
]);
