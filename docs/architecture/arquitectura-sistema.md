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
| Backend (BFF) | FastAPI + CrewAI | API para el frontend y orquestación multiagente (CrewAI Flow) en un único proceso y contenedor (un solo worker de uvicorn), sin orquestador ni worker aparte (D-011). Las tareas en segundo plano (`extract_soft_facts`) y la caché de respuestas MCP viven en ese mismo proceso (D-012). Stateless: el estado del Flow se persiste en PostgreSQL; la caché es desechable. |
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

En local, `infra/docker/docker-compose.yml` levanta solo Postgres,
publicado únicamente en `127.0.0.1` (D-004). El backend se añadirá al Compose
cuando tenga código.

```
cd infra/docker
docker compose --env-file ../env/.env up -d
```

---

## 4. Integración y entrega continua

Todo en GitHub Actions (`.github/workflows/`). Todos los workflows dan al
`GITHUB_TOKEN` solo permiso de lectura (`contents: read`).

| Workflow | Disparador | Qué hace |
|---|---|---|
| `ci.yml` | PR, push a `main`, manual | Calidad y tests de cada parte (§4.1). |
| `deploy-backend.yml` | CI verde en `main`, manual | Despliegue del backend en la VM (§4.2). |
| `lighthouse.yml` | PR que toca `frontend/`, manual | Accesibilidad (WCAG AA) y rendimiento web. |
| `llm-evals.yml` | Solo manual | Evaluación de hipótesis contra datasets de Langfuse (D-008). |
| `load-test.yml` | Solo manual | Pruebas de carga con Locust (D-008). |
| `dependabot.yml` | Mensual | Actualiza las versiones de las Actions (D-007). |

### 4.1 CI (`ci.yml`)

El job `changes` detecta qué partes del monorepo han cambiado y solo se
ejecutan los jobs afectados (D-001).

| Job | Se ejecuta si cambia | Comprobaciones |
|---|---|---|
| `backend` | `backend/`, `ci.yml` | `ruff check`, `ruff format --check`, `pyright`, migraciones Alembic, `pytest` con informe de cobertura (sin umbral: la barrera es el gate de Sonar, D-002). Usa un servicio efímero de Postgres (`pgvector/pgvector:0.8.7-pg16-bookworm`, D-015) con health check. |
| `frontend` | `frontend/`, `shared/`, `ci.yml` | Lint, `next typegen` + `tsc --noEmit` (D-023), tests con cobertura (Vitest, D-019), build de Next.js con Webpack (D-022) y de Storybook. |
| `contracts` | Modelos, API, `shared/` | Regenera JSON Schema y tipos TS y falla si difieren de lo commiteado. Se omite hasta que exista el generador. |
| `docker` | `backend/`, `frontend/`, `infra/`, `ci.yml` | Valida el Compose, construye las imágenes en **runner ARM** (como la VM, D-006) y analiza la configuración con Trivy (HIGH/CRITICAL). |
| `sonar` | Si `backend` o `frontend` pasan | SonarQube Cloud con el quality gate *Sonar way* (código nuevo: cobertura ≥ 80 %, duplicación ≤ 3 %, notas A, hotspots revisados). Si no se supera, el job falla (D-002). En `main`, el código nuevo es el de los últimos 30 días (D-013). |
| `ci-ok` | Siempre | Un único check que resume el resultado; es el que se marca como obligatorio en `main`. |

### 4.2 CD del backend (`deploy-backend.yml`)

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
