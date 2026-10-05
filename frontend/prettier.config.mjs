// Formato del frontend con Prettier (D-029). Casi todo con los valores por
// defecto: la idea de Prettier es no discutir el estilo. Solo cambia el ancho
// de línea, a 100 como ruff en el backend (D-023).
/** @type {import("prettier").Config} */
const config = {
  printWidth: 100,
};

export default config;
