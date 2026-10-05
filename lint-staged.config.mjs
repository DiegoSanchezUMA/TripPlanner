// Comprobaciones rápidas del hook pre-commit, solo sobre los ficheros que se
// van a commitear y separadas por parte del monorepo (D-028). lint-staged
// añade al final de cada comando la lista de ficheros (rutas absolutas).
// Los arreglos automáticos (--fix, format) se vuelven a añadir al commit.
export default {
  // Backend: las mismas herramientas y versiones que el CI (D-016, D-023).
  // --frozen: usa uv.lock tal cual, sin tocarlo. --force-exclude: respeta las
  // exclusiones de ruff aunque se le pasen ficheros sueltos.
  "backend/**/*.py": [
    "uv run --directory backend --frozen ruff check --fix --force-exclude",
    "uv run --directory backend --frozen ruff format --force-exclude",
  ],

  // Si cambian las dependencias, uv.lock tiene que estar al día: el CI
  // instala con --frozen y no detectaría un lockfile desfasado. Es una
  // función para que no reciba la lista de ficheros.
  "backend/{pyproject.toml,uv.lock}": () => "uv lock --directory backend --check",

  // Frontend: ESLint con la configuración de frontend/ (D-023).
  "frontend/**/*.{ts,tsx,js,mjs,cjs}": "pnpm --dir frontend exec eslint --fix --no-warn-ignored",
};
