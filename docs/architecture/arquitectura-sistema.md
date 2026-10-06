# Arquitectura del sistema

Visión de conjunto de TripPlanner: componentes, despliegue, entornos e
integración/entrega continua. El diseño interno del sistema multiagente (agentes,
tareas, guardrails, contratos, memoria) no está aquí: su fuente de verdad es
`docs/arquitectura-multiagente-crewai.md`.

El porqué de cada decisión de este documento está en
`docs/decisiones/decisiones.md` (referencias `D-NNN`).

---

## 1. Componentes

```
 Navegador
    │ HTTPS
    ▼
 Frontend · Next.js + React + TypeScript + CopilotKit        (Vercel)
    │ CopilotRuntime actúa como proxy hacia el backend
    │ HTTPS
    ▼
 Caddy · reverse proxy, HTTPS automático                      ┐
    │                                                         │
    ▼                                                         │
 Backend (BFF) · FastAPI + CrewAI, Python 3.13, uv            │ VM Oracle Cloud
    │            │                       │                    │ Always Free
    ▼            ▼                       ▼                    │ (Docker Engine)
 PostgreSQL 16              Servidores MCP                    │
 + pgvector                 (Flight, Hotel,                   │
                             Routes, Weather)                 ┘
    
 Servicios externos: LLMs (Groq, Google Gemini, Azure OpenAI) · Langfuse ·
 Places MCP (Geoapify, alojado por el proveedor) · API de Transitous (D-020)
```

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Frontend | Next.js, React, TypeScript, CopilotKit | Chat conversacional y visualización del itinerario mientras se construye. Componentes documentados en Storybook. |
| Backend (BFF) | FastAPI + CrewAI | API para el frontend y orquestación multiagente (CrewAI Flow) en un único proceso y contenedor (un solo worker de uvicorn), sin orquestador ni worker aparte (D-011). Las tareas en segundo plano (`extract_soft_facts`) y la caché de respuestas MCP viven en ese mismo proceso (D-012). El knowledge y la memoria de CrewAI van en Qdrant, con un almacén propio de cada ejecución (el knowledge en memoria; la memoria con Qdrant Edge en `/tmp`). Son librerías dentro del proceso, no un servicio (D-036). Stateless: el estado del Flow se persiste en PostgreSQL; la caché es desechable. |
| Base de datos | PostgreSQL 16 + pgvector | Datos relacionales y vectoriales en el mismo motor. Esquema en `docs/data-model/modelo-datos.md`. También guarda los contadores de cuota por usuario. Sin Redis: la caché de respuestas MCP va en memoria del backend; Redis queda como evolución futura (D-012). |
| Reverse proxy | Caddy | Solo en producción: termina HTTPS y expone el backend. |
| Observabilidad | Langfuse | Trazas de las llamadas a LLM y datasets de evaluación. |
| LLMs | Groq, Gemini, Azure OpenAI | Capas gratuitas. |

### Contratos de datos

Los schemas Pydantic de `backend/app/agents/models/` son la fuente de verdad.
Se exportan a JSON Schema (`shared/schemas/`) y de ahí se generan los tipos
TypeScript (`shared/types/`) que importa el frontend. Nunca se escriben tipos a
mano. El job `contracts` del CI comprueba que no divergen (§4.1).

### Capa de datos y migraciones

- El driver de Python para PostgreSQL es **psycopg 3**
  (`postgresql+psycopg://...`). SQLAlchemy trabaja por encima.
- El esquema lo crea **Alembic** a partir de los modelos; no se crean tablas a
  mano. Alembic lee la conexión de la variable `DATABASE_URL`.
- Las extensiones `vector` y `pgcrypto` se activan con
  `infra/postgres/init/001_extensions.sql`, que la imagen de Postgres ejecuta
  solo la primera vez que el volumen está vacío (D-010).

---

## 2. Despliegue

| Parte | Dónde | Cómo se despliega |
|---|---|---|
| Frontend | Vercel | Integración Git de Vercel (automática). |
| Backend, Postgres, Caddy | VM Oracle Cloud Always Free: Ampere A1 **ARM64**, 2 OCPU, 12 GB RAM | Docker Compose, mediante el workflow `deploy-backend.yml` (§4.2). |

Sin Kubernetes: una sola VM y pocos usuarios no justifican un orquestador
(decisión cerrada en `docs/arquitectura-multiagente-crewai.md` §2 y §14).

En producción se usa `docker-compose.yml` + `docker-compose.prod.yml` (este
último aún no existe). El fichero de producción añade Caddy y **no publica** los
puerto de Postgres al host: solo es accesible por la red interna de Docker.

---

## 3. Entornos

| Entorno | Base de datos | Claves de LLM | Uso |
|---|---|---|---|
| Local | `tripplanner` (Compose, persistente en volumen) | Las del desarrollador, en `infra/env/.env` (no versionado) | Desarrollo |
| CI | `tripplanner_test`, efímera (servicio del job) | **Ninguna**: tests con mocks (D-009) | Validar cada cambio |
| Evals | — | Entorno de GitHub `evals` | Hipótesis sobre el LLM (`plan-de-pruebas.md`) |
| Producción | `tripplanner` en la VM | Entorno de GitHub `production` | Usuarios reales |

En local, `infra/docker/docker-compose.yml` levanta Postgres y la API del
backend, publicados únicamente en `127.0.0.1` (D-004). La imagen de la API se
construye con un Dockerfile multietapa, *builder* y *runner*, que aprovecha la
caché de capas (D-034).

```
cd infra/docker
docker compose --env-file ../env/.env up -d --build
```

### Hooks de Git (local)

Husky ejecuta en local una versión rápida del CI, separada por backend y
frontend (D-028). Se activa una vez tras clonar, con `pnpm install` en la raíz
del repo.

| Hook | Backend | Frontend |
|---|---|---|
| `pre-commit` (ficheros preparados) | `ruff check --fix`, `ruff format`; `uv lock --check` si cambian las dependencias | `eslint --fix`, `prettier --write` (D-029) |
| `commit-msg` | Conventional Commits (`commitlint`) | Igual |
| `pre-push` (solo la parte que cambia) | `pyright`, `pytest` | `next typegen` + `tsc`, Vitest |

---

## 4. Integración y entrega continua

Todo en GitHub Actions (`.github/workflows/`). Todos los workflows dan al
`GITHUB_TOKEN` solo permiso de lectura (`contents: read`), y todas las Actions
se referencian por SHA de commit, con la versión en un comentario (D-026). Los
runners están fijados a `ubuntu-24.04` (y `ubuntu-24.04-arm`), no a
`ubuntu-latest` (D-027).

| Workflow | Disparador | Qué hace |
|---|---|---|
| `ci.yml` | PR, push a `main`, manual | Calidad y tests de cada parte (§4.1). |
| `deploy-backend.yml` | CI verde en `main`, manual | Despliegue del backend en la VM (§4.2). Aún no está en el repo (D-005). |
| `lighthouse.yml` | PR que toca `frontend/`, manual | Accesibilidad (WCAG AA) y rendimiento web. |
| `llm-evals.yml` | Solo manual | Evaluación de hipótesis contra datasets de Langfuse (D-008). Aún no está en el repo. |
| `load-test.yml` | Solo manual | Pruebas de carga con Locust (D-008). Aún no está en el repo. |
| `dependabot.yml` | Mensual | Actualiza las versiones de las Actions: SHA y comentario (D-007, D-026). |
| CodeQL (*default setup*, configurado en GitHub, sin fichero) | PR, push a `main` y semanal | Análisis de seguridad de Python, JS/TS y los workflows (D-032). |

### 4.1 CI (`ci.yml`)

El job `changes` detecta qué partes del monorepo han cambiado y solo se
ejecutan los jobs afectados (D-001).

| Job | Se ejecuta si cambia | Comprobaciones |
|---|---|---|
| `backend` | `backend/`, `ci.yml` | `ruff check`, `ruff format --check`, `pyright`, migraciones Alembic, `pytest` con informe de cobertura (sin umbral: la barrera es el gate de Sonar, D-002). Usa un servicio efímero de Postgres (`pgvector/pgvector:0.8.7-pg16-bookworm`, D-015) con health check y sin contraseña. uv instala con `--locked --no-build`: lockfile verificado y solo paquetes precompilados (D-031). |
| `frontend` | `frontend/`, `shared/`, `ci.yml` | Lint, formato con Prettier (D-029), `next typegen` + `tsc --noEmit` (D-023), tests con cobertura (Vitest, D-019), build de Next.js con Webpack (D-022) y de Storybook. |
| `contracts` | Modelos, API, `shared/` | Regenera JSON Schema y tipos TS y falla si difieren de lo commiteado. Se omite hasta que exista el generador. |
| `docker` | `backend/`, `frontend/`, `infra/`, `ci.yml` | Valida el Compose; construye la imagen del backend en **runner ARM** (como la VM, D-006) con la caché de capas de GitHub Actions; arranca la API con Postgres y comprueba `/health` y las migraciones (D-034), y que CrewAI y los almacenes Qdrant del knowledge y la memoria funcionan con el disco de solo lectura (D-035, D-036); analiza la configuración con Trivy (HIGH/CRITICAL). |
| `sonar` | Si `backend` o `frontend` pasan | SonarQube Cloud con el quality gate *Sonar way* (código nuevo: cobertura ≥ 80 %, duplicación ≤ 3 %, notas A, hotspots revisados). Si no se supera, el job falla (D-002). En `main`, el código nuevo es el de los últimos 30 días (D-013). |
| `ci-ok` | Siempre | Un único check que resume el resultado; es el único obligatorio para hacer merge en `main` (D-033). |

### 4.2 CD del backend (`deploy-backend.yml`)

> Pendiente (D-005): el workflow está escrito, pero no se sube al repo hasta
> haber probado el CI y preparado la VM.

1. Se dispara cuando el CI de un **push** a `main` termina en verde, o a mano.
2. Interruptor: no hace nada mientras la variable `DEPLOY_ENABLED` no sea
   `true` (D-005).
3. Entra por SSH en la VM (verificando la huella del host), hace checkout del
   commit exacto que pasó el CI, construye las imágenes **en la propia VM** y
   las levanta con `--wait`.
4. Aplica las migraciones (`alembic upgrade head`) y limpia imágenes viejas.
5. Smoke test: llama a `https://<host>/health` hasta 20 veces; si no responde,
   el despliegue falla.

Los despliegues nunca se solapan (`concurrency: deploy-production`) y los
secretos viven en el entorno `production`, que permite exigir aprobación manual.

---

## 5. Seguridad (resumen)

- Secretos fuera del repo: `.env` en `.gitignore`; en CI, en entornos de GitHub
  (`production`, `evals`).
- CI sin claves reales de LLM ni MCP (D-009).
- Postgres nunca expuesto fuera de la máquina (D-004).
- `GITHUB_TOKEN` de solo lectura; los PRs desde forks no reciben el token de
  SonarQube.
- Trivy analiza Dockerfiles y Compose en cada cambio de infraestructura.
- Actions fijadas por SHA de commit, que no se puede reescribir como una
  etiqueta (D-026).
- Dependencias de Python instaladas en el CI solo desde el lockfile verificado
  y sin compilar paquetes; la base de datos de pruebas, sin contraseña (D-031).
- CodeQL analiza la seguridad del código y de los workflows en cada PR y cada
  semana, como segunda opinión junto a SonarCloud (D-032).
- `main` solo cambia por PR con `ci-ok` en verde; no se puede borrar ni
  reescribir su historial (D-033).
- La API se ejecuta sin root y con el sistema de ficheros de solo lectura. Solo
  `/tmp` es escribible: está en memoria y se vacía en cada arranque, y ahí
  escribe CrewAI (D-034, D-035).
- El knowledge y la memoria de cada ejecución van en su propio almacén Qdrant:
  lo de un usuario nunca llega a la crew ni al Flow de otro (RNF-6.3, D-036).
- Las alertas de Dependabot sin arreglo compatible se analizan una a una. Si el
  código vulnerable no se usa, se descartan con justificación y con barreras que
  lo vigilan. Por ejemplo, ChromaDB (dependencia obligatoria de CrewAI) solo se
  usa como librería: Ruff prohíbe importarlo en nuestro código y un test
  comprueba que su servidor no se carga (D-036).
