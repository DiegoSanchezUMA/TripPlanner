# TripPlanner — Planificador de Viajes Multiagente (TFG)

## Resumen
Aplicación web de planificación de viajes con IA: arquitectura RAG + sistema
multiagente (CrewAI) para generar itinerarios personalizados en tiempo real, con
chat conversacional y visualización dinámica del itinerario mientras se construye.
TFG de Diego Sánchez Contreras (Grado en Ingeniería Informática, UMA), tutor
Francisco López Valverde.

## Stack
- Frontend: React, Next.js, TypeScript, CopilotKit (CopilotRuntime como proxy)
- Estilos/UI: componentes modulares documentados en Storybook
- Backend: FastAPI (BFF) + CrewAI, Python 3.13, uv (versiones fijadas y sus
  motivos en `docs/decisiones/decisiones.md`, D-014 a D-019)
- Base de datos: PostgreSQL 16 + pgvector (relacional y vectorial en el mismo motor)
- Sin Redis: caché MCP en memoria del backend (un solo proceso), cuotas en
  PostgreSQL; Redis queda como evolución futura (ver
  `docs/decisiones/decisiones.md`, D-012)
- Observabilidad: Langfuse
- LLMs: Groq, Google Gemini, Azure OpenAI (capas gratuitas)
- Despliegue: frontend en Vercel; backend en una VM Oracle Cloud Always Free
  (Ampere A1 ARM64, 2 OCPU, 12 GB RAM) con Docker Engine — sin Kubernetes (una
  sola VM, volumen de usuarios bajo)

## Arquitectura multiagente (cerrada — ver `docs/arquitectura-multiagente-crewai.md`)
8 agentes, un especialista por servidor MCP (Flight, Hotel, Places, Routes,
Weather) más Travel Planner, Itinerary Composer e Itinerary Reviewer. Places usa
Geoapify MCP y Routes usa Transitous MCP (datos abiertos), no Google Maps, por los
términos de Google en el EEE (D-020, pendiente de desarrollar). Orquestación
con un CrewAI Flow (`@router classify_intent`, modelo de agencia por adhesión: la
mayoría de mensajes se resuelven sin instanciar ninguna crew) por encima de dos
crews: PlanningCrew (`Process.sequential`, async en T2–T4, 8 tareas) y
RefinementCrew (4–5 tareas, 3–4 agentes, sin Travel Planner). Guardrails deterministas
(anclaje, horario, presupuesto, dieta, accesibilidad, ritmo…) + probabilísticos
(rúbrica LLM-as-a-judge, 5 dimensiones). Contratos de datos: **Pydantic siempre**,
sin agente formateador. Memoria: pgvector solo con hechos del usuario (nunca datos
del mundo); memoria nativa de CrewAI solo *short-term* efímera en producción (no
aísla por usuario — ver documento de arquitectura §5 antes de tocar esto).

## Estructura del repo (real, verificar antes de asumir `apps/`)
- `frontend/` — Next.js, Vercel (incluye `.storybook/`, `stories/`, `tests/`)
- `backend/` — un paquete Python: `app/` (incluye `app/agents/` para
  flows/crews/guardrails/hooks/tools/models, ver estructura en el documento de
  arquitectura §11), `evals/`, `reports/`, `scripts/`, `tests/`
- `shared/` — `contracts/`, `schemas/`, `types/` (tipos compartidos frontend↔backend)
- `infra/` — `docker/`, `postgres/`, `env/`, `ci/`
- `docs/` — diagramas y decisiones de arquitectura, incluye:
  - `arquitectura-multiagente-crewai.md` — **fuente de verdad** del diseño
    multiagente: agentes, tareas, guardrails, hooks, contratos, persistencia,
    esqueleto de código, checklist
  - `requisitos.md` — catálogo completo RF/RNF (183 requisitos) y 23 casos de uso
  - `data-model/modelo-datos.md` — esquema de base de datos (tablas de dominio +
    orquestación/autoguardado)
  - `plan-de-pruebas.md` — estrategia de pruebas, metodología estadística de las
    44 hipótesis sobre el LLM, escenarios de validación V01–V12
  - `estado-del-arte.md` — contexto y justificación de las decisiones (por qué
    CrewAI, por qué MCP, por qué pgvector, panorama competitivo)
  - `architecture/arquitectura-sistema.md` — arquitectura del sistema fuera del
    multiagente: componentes, despliegue, entornos, CI/CD (workflows y jobs),
    seguridad
  - `decisiones/decisiones.md` — registro de decisiones de infraestructura,
    CI/CD y herramientas (D-NNN: contexto, decisión, alternativas,
    consecuencias). Al tomar una decisión de este tipo, añadir aquí su entrada
    y actualizar `arquitectura-sistema.md` si cambia el sistema
  - `uml/` — diagramas fuente (Visual Paradigm, exportados a `.jpg`): casos de
    uso, secuencia, componentes, despliegue, clases, requisitos
  - `agents/`, `api/`, `mcp/`, `rag/` — carpetas reservadas para documentación
    futura más granular; de momento ese contenido vive consolidado en
    `arquitectura-multiagente-crewai.md`

## Reglas de trabajo
- Los schemas Pydantic de `backend/app/agents/models/` (contratos de datos, ver
  `docs/arquitectura-multiagente-crewai.md` §8) son la fuente de verdad del
  contrato de datos. Frontend y backend nunca deben divergir de ahí; los tipos
  TypeScript se generan desde el esquema, no se mantienen a mano.
- Un agente por servidor MCP: no fusionar responsabilidades. Exactamente 8 agentes.
- No introducir Kubernetes ni `Process.hierarchical` — decisiones cerradas y
  justificadas en `docs/arquitectura-multiagente-crewai.md` §2 y §14.
- No usar agente formateador (solo salidas Pydantic vía `output_pydantic`).
- No raspar precios ni disponibilidad (vuelos, alojamiento), ni como último
  recurso — el raspado acotado solo vale para datos informativos de lugares.
- Backend stateless; estado del Flow persistido vía `@persist` respaldado en
  PostgreSQL (no SQLite, que da bloqueos con ejecuciones concurrentes).
- No hay botón de guardar: toda mutación del itinerario se autoguarda con bloqueo
  optimista (versión) y deja una fila en `trip_revisions` (append-only).
- Sigue las convenciones de tipado estricto en TS y Pydantic en Python.
- Antes de cambiar algo en `docs/arquitectura-multiagente-crewai.md`, pregunta: es
  la fuente de verdad de la memoria del TFG.
- El proyecto está en fase de diseño/documentación: `backend/`, `frontend/` y
  `shared/` son scaffolding vacío. Antes de escribir código, consulta primero
  `docs/arquitectura-multiagente-crewai.md` (agentes/tareas/guardrails exactos),
  `docs/requisitos.md` (qué construir) y `docs/data-model/modelo-datos.md` (esquema).

## Comandos
Instalación completa y resto de comandos: `README.md`.
- `pnpm install` (en la raíz) — instala Husky y activa los hooks de Git (D-028)
- `docker compose --env-file ../env/.env up -d --build --wait` (desde `infra/docker/`) —
  Postgres + API local (imagen multietapa en `infra/docker/backend/Dockerfile`, D-034)
- `docker compose ps` / `docker stats --no-stream` — estado y consumo
- Backend (desde `backend/`): `uv sync`, `uv run pytest --ignore=tests/load`,
  `uv run ruff check .`, `uv run pyright`, `uv run uvicorn app.main:app --reload`
- Frontend (desde `frontend/`): `pnpm install`, `pnpm test:coverage`, `pnpm lint`,
  `pnpm format:check` (Prettier, solo frontend), `pnpm typecheck`, `pnpm dev`
- El backend lee la configuración solo de variables de entorno (no del `.env`);
  fuera de Docker, `DATABASE_URL` usa `localhost`, no `postgres`
