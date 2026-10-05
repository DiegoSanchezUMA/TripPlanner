// Mensajes de commit con Conventional Commits (D-028): "tipo(ámbito): resumen".
// Tipos: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
// Los merges que crea GitHub ("Merge pull request #…") se ignoran solos.
export default {
  extends: ["@commitlint/config-conventional"],
};
