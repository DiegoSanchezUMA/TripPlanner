# TripPlanner
Planificador de viajes con IA: arquitectura RAG y sistema multiagente (CrewAI) que genera itinerarios personalizados en tiempo real, con guardrail de anclaje contra alucinaciones. Frontend en Next.js + TypeScript con patrón BFF. Trabajo de Fin de Grado, Universidad de Málaga.

> **Estado:** fase de diseño con un esqueleto mínimo. Por ahora el backend solo
> tiene `GET /health` y el frontend una página de inicio. El diseño completo está
> en [`docs/`](#documentación).

## Requisitos

| Herramienta | Versión | Para qué | Cómo instalarla |
|---|---|---|---|
| Git | Reciente | Clonar y hacer commits (los hooks usan su `sh`) | [git-scm.com](https://git-scm.com/) |
| Node.js | **24** (lo fija [`frontend/.nvmrc`](frontend/.nvmrc)) | Frontend y hooks de Git | Con nvm: `nvm install 24` y `nvm use 24` (en Windows, [nvm-windows](https://github.com/coreybutler/nvm-windows)) |
| pnpm | **10.34.6** (lo fija `packageManager` en `package.json`) | Dependencias de JavaScript | `corepack enable pnpm` (Corepack viene con Node 24 y descarga la versión exacta) |
| uv | **0.12.x** (el proyecto exige `>=0.12,<0.13`) | Python y dependencias del backend | Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.12.23/install.ps1 \| iex"`<br>macOS/Linux: `curl -LsSf https://astral.sh/uv/0.12.23/install.sh \| sh` |
| Python | 3.13 | Backend | No hace falta instalarlo: uv lo descarga la primera vez |
| Docker | Docker Desktop (Windows/macOS) o Docker Engine con Compose v2 (Linux) | PostgreSQL + pgvector en local | [docs.docker.com](https://docs.docker.com/get-started/get-docker/) |

## Instalación

Se hace una sola vez, después de clonar. Todos los comandos parten de la raíz
del repositorio.

### 1. Clonar

```sh
git clone https://github.com/DiegoSanchezUMA/TripPlanner.git
cd TripPlanner
```

### 2. Hooks de Git (en la raíz)

```sh
corepack enable pnpm
pnpm install
```

Instala Husky, lint-staged y commitlint, y el script `prepare` activa los hooks
de Git. **Sin este paso no hay hooks**: Git no los activa solo al clonar. Para
comprobarlo, `git config core.hooksPath` debe responder `.husky/_`. Qué hace
cada hook: [Hooks de Git](#hooks-de-git).

### 3. Backend

```sh
cd backend
uv sync
```

Crea `backend/.venv` con Python 3.13 y las versiones exactas de `uv.lock`. En
VS Code, elige ese entorno como intérprete (*Python: Select Interpreter*). Si no,
el editor marcará las dependencias como no instaladas.

### 4. Frontend

```sh
cd frontend
pnpm install
```

### 5. Variables de entorno

Copia la plantilla y cambia la contraseña de Postgres. Va en **dos** líneas:
`POSTGRES_PASSWORD` y dentro de `DATABASE_URL`.

```sh
cp infra/env/.env.example infra/env/.env                 # Git Bash, macOS, Linux
Copy-Item infra/env/.env.example infra/env/.env          # PowerShell
```

`infra/env/.env` está en `.gitignore`: nunca se sube al repositorio. Para
arrancar el esqueleto no hacen falta las claves de LLM ni de MCP.

### 6. Base de datos

```sh
cd infra/docker
docker compose --env-file ../env/.env up -d
docker compose ps          # espera a que postgres aparezca como "healthy"
```

Postgres solo se publica en `127.0.0.1:5432`, no en la red local. La primera vez,
un script de inicialización crea las extensiones `vector` (pgvector) y
`pgcrypto`.

### 7. Migraciones

El backend lee la configuración **de las variables de entorno**, no del fichero
`.env`. Además, como se ejecuta en tu máquina y no dentro de Docker, el host de
la base de datos es `localhost`, no `postgres` (ese nombre solo existe dentro de
la red de Docker Compose).

```sh
# Git Bash, macOS, Linux (desde backend/)
export DATABASE_URL="postgresql+psycopg://tripplanner:TU_CONTRASEÑA@localhost:5432/tripplanner"
uv run alembic upgrade head
```

```powershell
# PowerShell (desde backend/)
$env:DATABASE_URL = "postgresql+psycopg://tripplanner:TU_CONTRASEÑA@localhost:5432/tripplanner"
uv run alembic upgrade head
```

Todavía no hay migraciones: de momento el comando solo comprueba que la conexión
funciona. La variable dura lo que dure la terminal.

## Uso diario

**Backend** (desde `backend/`):

| Comando | Qué hace |
|---|---|
| `uv run uvicorn app.main:app --reload` | API en http://127.0.0.1:8000 (prueba con `/health`; documentación interactiva en `/docs`) |
| `uv run pytest --ignore=tests/load` | Tests unitarios |
| `uv run ruff check .` y `uv run ruff format .` | Lint y formato |
| `uv run pyright` | Comprobación de tipos |

**Frontend** (desde `frontend/`):

| Comando | Qué hace |
|---|---|
| `pnpm dev` | Aplicación en http://localhost:3000 |
| `pnpm test` / `pnpm test:coverage` | Tests (Vitest), en modo vigilancia o con cobertura |
| `pnpm lint` y `pnpm typecheck` | ESLint y comprobación de tipos |
| `pnpm format` / `pnpm format:check` | Formatea con Prettier / solo comprueba el formato (lo que hace el CI) |
| `pnpm build` | Build de producción |
| `pnpm storybook` | Catálogo de componentes en http://localhost:6006 |

**Base de datos** (desde `infra/docker/`):

| Comando | Qué hace |
|---|---|
| `docker compose --env-file ../env/.env up -d` | Arranca Postgres |
| `docker compose --env-file ../env/.env down` | La para; los datos se conservan en el volumen |
| `docker compose --env-file ../env/.env down -v` | La para y **borra los datos** |

## Hooks de Git

Una versión rápida del CI que se ejecuta en local, separada por backend y
frontend ([D-028](docs/decisiones/decisiones.md)).

| Hook | Cuándo | Backend | Frontend |
|---|---|---|---|
| `pre-commit` | `git commit`, solo sobre los ficheros preparados | `ruff check --fix` y `ruff format`; `uv lock --check` si cambian las dependencias | `eslint --fix` y `prettier --write` |
| `commit-msg` | `git commit` | Formato del mensaje (abajo) | Igual |
| `pre-push` | `git push`, solo la parte que cambia | `pyright` y `pytest` | `next typegen` + `tsc` y Vitest |

Los arreglos automáticos (formato, imports…) se añaden solos al commit. Si queda
un error que no se puede arreglar solo, el commit o el push se cancelan y el
mensaje dice por qué.

**Formato de los mensajes de commit** ([Conventional Commits](https://www.conventionalcommits.org/es/)):
`tipo(ámbito opcional): resumen`. El resumen va en minúscula y empieza por un
verbo.

| Tipo | Para qué |
|---|---|
| `feat` / `fix` | Funcionalidad nueva / corrección de un error |
| `docs` | Solo documentación |
| `test` | Tests |
| `refactor` / `perf` / `style` | Reorganizar código / mejorar el rendimiento / solo formato |
| `build` / `ci` | Dependencias y herramientas / workflows de GitHub Actions |
| `chore` / `revert` | Mantenimiento / deshacer un commit |

```text
✔ feat(backend): añadir endpoint de itinerarios
✔ docs: actualizar el modelo de datos
✘ añadir endpoint                  (falta el tipo)
✘ Feat: Añadir endpoint            (tipo y resumen en mayúscula)
```

En un apuro, `git commit --no-verify` o `git push --no-verify` se saltan los
hooks. El CI sigue comprobándolo todo en el PR.

## Editor (VS Code)

Al abrir la carpeta del proyecto, VS Code sugiere instalar las extensiones de
[`.vscode/extensions.json`](.vscode/extensions.json): acepta *Install All*.
Después, elige `backend/.venv` como intérprete de Python (*Python: Select
Interpreter*). Con eso, al guardar un fichero pasa lo mismo que en el
`pre-commit` ([D-030](docs/decisiones/decisiones.md)):

| Al guardar… | Se aplica |
|---|---|
| `.ts`, `.tsx`, `.js` del frontend | ESLint arregla lo que puede y Prettier formatea |
| `.json`, `.css` del frontend | Prettier formatea |
| `.py` del backend | Ruff arregla, ordena los imports y formatea |

Pylance comprueba los tipos en modo estricto, igual que pyright en el CI.
SonarQube for IDE muestra en el editor las reglas del quality gate. Prettier
nunca toca nada fuera de `frontend/`.

## Problemas frecuentes en Windows

- **`uv` o `pnpm` no se encuentran justo después de instalarlos:** abre una
  terminal nueva o reinicia VS Code, que hereda el PATH al arrancar. Pasa
  también con los hooks si el editor estaba abierto durante la instalación.
- **Corepack pregunta antes de descargar pnpm:** define
  `COREPACK_ENABLE_DOWNLOAD_PROMPT=0` (en PowerShell:
  `$env:COREPACK_ENABLE_DOWNLOAD_PROMPT = "0"`).
- **pnpm avisa de `Unsupported engine`:** estás con una versión de Node distinta
  de la 24. Funciona, pero conviene cambiar con `nvm use 24`.
- **No se puede borrar `node_modules`:** `Remove-Item` falla por las rutas
  largas de pnpm. Usa `cmd /c rd /s /q node_modules`.

## Estructura del repositorio

```text
backend/    API FastAPI + sistema multiagente CrewAI (Python, uv)
frontend/   Next.js + CopilotKit, Storybook (TypeScript, pnpm)
shared/     Tipos y esquemas compartidos, generados desde los modelos Pydantic
infra/      Docker Compose, scripts de Postgres y plantilla de variables de entorno
docs/       Diseño, requisitos, decisiones y diagramas
.github/    CI (GitHub Actions) y Dependabot
.husky/     Hooks de Git
.vscode/    Extensiones recomendadas y configuración del editor
```

## Documentación

- [Arquitectura multiagente](docs/arquitectura-multiagente-crewai.md): agentes, tareas, guardrails y contratos de datos.
- [Requisitos](docs/requisitos.md): requisitos funcionales y no funcionales, y casos de uso.
- [Modelo de datos](docs/data-model/modelo-datos.md): esquema de la base de datos.
- [Plan de pruebas](docs/plan-de-pruebas.md): estrategia de pruebas y evaluación del LLM.
- [Arquitectura del sistema](docs/architecture/arquitectura-sistema.md): componentes, despliegue, entornos y CI/CD.
- [Registro de decisiones](docs/decisiones/decisiones.md): decisiones de infraestructura y herramientas, con su porqué.
- [Estado del arte](docs/estado-del-arte.md): contexto y justificación de las tecnologías.

## Integración continua

Cada PR ejecuta [`ci.yml`](.github/workflows/ci.yml): lint, formato, tipos,
tests y cobertura de backend y frontend, validación de Docker en ARM64, análisis de
SonarQube Cloud y Lighthouse para la accesibilidad. El check `ci-ok` resume el
resultado. Más detalle en la [arquitectura del sistema](docs/architecture/arquitectura-sistema.md#4-integración-y-entrega-continua).

## Licencia

[MIT](LICENSE).
