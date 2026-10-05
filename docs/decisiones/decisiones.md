# Registro de decisiones

Decisiones de proyecto (infraestructura, CI/CD, herramientas, convenciones) que
no forman parte del diseño multiagente. La descripción del sistema que resulta
de ellas está en `docs/architecture/arquitectura-sistema.md`. Las decisiones de
arquitectura multiagente viven en `docs/arquitectura-multiagente-crewai.md`.

| ID | Decisión | Estado |
|---|---|---|
| D-001 | `ci.yml` incluido en los filtros de rutas | Aceptada |
| D-002 | El quality gate *Sonar way* es la única barrera de cobertura | Aceptada |
| D-003 | Informe HTML de cobertura automático en local | Pendiente |
| D-004 | Postgres y Redis publicados solo en `127.0.0.1` | Aceptada |
| D-005 | CD por SSH con build en la VM e interruptor `DEPLOY_ENABLED` | Pendiente |
| D-006 | Job `docker` del CI en runner ARM64 | Aceptada |
| D-007 | Dependabot solo para las versiones de las Actions | Aceptada |
| D-008 | Evals de LLM y pruebas de carga solo manuales | Pendiente |
| D-009 | CI sin claves reales de LLM ni MCP | Aceptada |
| D-010 | Extensiones de Postgres activadas por script de inicialización | Aceptada |
| D-011 | Backend en un único proceso (API + CrewAI Flow) | Aceptada |
| D-012 | Sin Redis: caché en memoria, cuotas en PostgreSQL y Redis como evolución futura | Aceptada |
| D-013 | Código nuevo de SonarQube: últimos 30 días | Aceptada |
| D-014 | Python 3.13 en el backend (sustituye a 3.12) | Aceptada |
| D-015 | PostgreSQL 16 se mantiene, con la imagen fijada a una versión concreta | Aceptada |
| D-016 | Versiones del backend y política de fijado | Aceptada |
| D-017 | AG-UI con `ag-ui-protocol`, sin `ag-ui-crewai` ni el SDK Python de CopilotKit | Pendiente |
| D-018 | Versiones del frontend: Node 24, pnpm 10, TypeScript 6 y ESLint 9 | Aceptada |
| D-019 | Vitest para los tests del frontend (como fija el plan de pruebas) | Aceptada |
| D-020 | Lugares y rutas con datos abiertos: Places MCP (Geoapify) y Routes MCP (Transitous), dos agentes | Pendiente |
| D-021 | Esqueleto mínimo de backend y frontend para que el CI pase de verdad | Aceptada |
| D-022 | Next.js compila con Webpack, no con Turbopack | Aceptada |
| D-023 | Lint y tipado estrictos en backend y frontend | Aceptada |
| D-024 | pnpm no ejecuta scripts de instalación de dependencias | Aceptada |
| D-025 | Entorno de desarrollo local en Windows: uv, Corepack y `.venv` | Aceptada |
| D-026 | Actions fijadas por SHA de commit y actualizadas a sus últimas versiones | Aceptada |

Formato de cada entrada: contexto, decisión, alternativas descartadas y
consecuencias. Estados: **Aceptada**, **Pendiente** (decidida pero aún sin
aplicar porque falta código), **Sustituida**.

---

## D-001 · El propio `ci.yml` forma parte de los filtros de rutas

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Contexto.** El CI (`.github/workflows/ci.yml`) usa `dorny/paths-filter` para
ejecutar solo los jobs cuya parte del monorepo ha cambiado. Un cambio en el
propio workflow (versión de una action, un paso) no toca código y, sin más, no
dispararía ningún job.

**Decisión.** `.github/workflows/ci.yml` se incluye en los filtros `backend`,
`frontend` y `docker`. Cualquier cambio en el workflow valida todo el pipeline.
El filtro `contracts` no lo incluye: comprueba la coherencia Pydantic ↔ TS, que
no depende del workflow.

**Alternativas descartadas.**
- Incluir `ci.yml` solo en los filtros afectados por cada cambio: no detecta
  fallos en partes compartidas (`needs`, `env` global).
- Separar en un workflow por parte (`ci-backend.yml`, `ci-frontend.yml`): más
  preciso, pero más ficheros que mantener para un proyecto de un solo
  desarrollador.

**Consecuencias.** Algunos minutos de Actions de más al editar el workflow.
Aceptable mientras los jobs sean cortos.

---

## D-002 · El quality gate *Sonar way* es la única barrera de cobertura

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Contexto.** Hay dos posibles barreras de cobertura: `--cov-fail-under` en
pytest (job `backend`) y el quality gate de SonarQube Cloud (job `sonar`, que
espera su resultado gracias a `sonar.qualitygate.wait=true` en
`sonar-project.properties`). En el plan gratuito de SonarQube Cloud **no se
pueden crear quality gates propios** (solo en los planes Team y Enterprise):
únicamente se puede elegir entre los predefinidos *Sonar way* y *Sonar way for
agentic AI*.

**Decisión.** Se usa *Sonar way* sin modificar y es la única barrera de
cobertura. pytest mide y muestra la cobertura (`--cov-report=term-missing`),
pero no falla por ella. *Sonar way* exige, **solo sobre el código nuevo** (en un
PR, las líneas que cambia el PR):
- cobertura ≥ 80 %;
- duplicación ≤ 3 %;
- notas A en fiabilidad, seguridad y mantenibilidad;
- todos los Security Hotspots nuevos revisados.

Las condiciones de cobertura y duplicación se ignoran si hay menos de 20
líneas nuevas.

Si no se supera el gate, falla el job `sonar` y, con él, `ci-ok`: no se puede
fusionar en `main` ni se despliega (D-005).

Lo que sea legítimamente difícil de probar (punto de entrada, configuración)
se excluye con `sonar.coverage.exclusions`, como ya se hace con las
migraciones. No se usa para ocultar código que debería tener tests.

**Alternativas descartadas.**
- **Umbral del 70 % en pytest además del gate.** Fue la configuración inicial.
  Con el gate bloqueando es redundante: si el código nuevo llega al 80 %, el
  total sube. Además, si saltaba, el job `sonar` no se ejecutaba y el análisis
  no llegaba a SonarQube justo cuando la cobertura era baja. Tampoco hacía el
  CI independiente de Sonar, porque el gate bloquea igualmente. Para ver la
  cobertura sin Sonar basta `term-missing` (log del CI y terminal local) y el
  informe HTML (D-003).
- **Sonar solo informativo** (sin `sonar.qualitygate.wait`) **y el 70 % en
  pytest como barrera.** Más cómodo, pero se pierde el control de duplicación,
  bugs, vulnerabilidades y hotspots.
- **Plan Team de SonarQube Cloud** para un gate propio: coste injustificado en
  un TFG.

**Consecuencias.**
- Los tests se escriben a la vez que el código; el 80 % se aplica a cada PR.
- El estándar no se rebaja: se usa tal cual el gate de referencia de Sonar, lo
  que es fácil de justificar en la memoria.
- El CI depende de SonarQube Cloud: si el servicio está caído, `sonar` falla y
  bloquea la fusión aunque el código sea correcto.
- En los PRs desde forks (sin acceso al token) no se aplica el gate. No afecta
  a un proyecto de un solo desarrollador.

---

## D-003 · Informe HTML de cobertura generado automáticamente en local

- **Fecha:** 2026-10-01
- **Estado:** Pendiente (falta `backend/pyproject.toml`)

**Contexto.** El informe de terminal (`term-missing`) lista las líneas sin
cubrir, pero el informe HTML de pytest-cov muestra el código coloreado (similar
a SonarQube) y es más cómodo de revisar.

**Decisión.** Configurar pytest para que lo genere en cada ejecución, sin
tener que recordar las opciones. Al crear `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-branch --cov-report=term-missing --cov-report=html"
```

`uv run pytest` genera entonces `backend/htmlcov/index.html`.

**Alternativas descartadas.**
- Lanzarlo a mano con las opciones cada vez: se olvida y no aporta nada.
- Subir `htmlcov/` como artefacto del CI: redundante con SonarQube.

**Consecuencias.**
- `addopts` también se aplica en CI: se genera el HTML (se descarta al acabar
  el job) y se mide cobertura de ramas (`--cov-branch`), que llega a SonarQube
  en `coverage.xml`. SonarQube combina líneas y ramas en su métrica de
  cobertura, así que el 80 % del gate (D-002) cuesta algo más de alcanzar.
- `.gitignore` ignora `.coverage`, `htmlcov/`, `coverage.xml` y `junit.xml`
  para no subir informes generados (ya aplicado).

---

## D-004 · Postgres y Redis publicados solo en `127.0.0.1`

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Contexto.** En local, el backend (y herramientas como `psql` o un cliente
gráfico) necesitan llegar a Postgres y Redis desde el host.

**Decisión.** En `infra/docker/docker-compose.yml` los puertos se publican como
`127.0.0.1:5432` y `127.0.0.1:6379`: accesibles desde la propia máquina, pero no
desde la red local. En producción (`docker-compose.prod.yml`) no se publican en
absoluto; solo existe la red interna de Docker.

**Alternativa descartada.** Publicar `5432:5432` sin IP: Docker escucha en
todas las interfaces y, además, se salta las reglas del cortafuegos del host,
de modo que la BD quedaría expuesta a la red (o a internet en la VM).

**Consecuencias.** Para conectarse a la BD de producción desde fuera hay que
usar un túnel SSH. Es intencionado.

**Nota.** Desde D-012 el proyecto ya no usa Redis: esta decisión aplica solo a
Postgres (`127.0.0.1:5432`).

---

## D-005 · CD por SSH con build en la VM e interruptor `DEPLOY_ENABLED`

- **Fecha:** 2026-10-01
- **Estado:** Pendiente (2026-10-05: el workflow existe en local, pero no se
  sube al repo hasta haber probado el CI y preparado la VM)

**Contexto.** El backend se despliega en una única VM ARM64. Hace falta un
mecanismo de despliegue sencillo, reproducible y que no despliegue código sin
validar.

**Decisión.** `deploy-backend.yml`:
- Se dispara solo cuando el CI de un **push** a `main` termina en verde (no con
  PRs), y despliega exactamente el commit que pasó el CI (`head_sha`).
- Entra por SSH verificando la huella del host, construye las imágenes **en la
  VM** con `docker compose up --build --wait` y aplica las migraciones.
- Smoke test contra `/health`.
- No hace nada mientras la variable `DEPLOY_ENABLED` no sea `true`, para poder
  tener el workflow en el repo antes de que exista la VM.
- `concurrency` impide dos despliegues simultáneos; los secretos están en el
  entorno `production`, que admite aprobación manual.

**Alternativas descartadas.**
- Construir las imágenes en CI y publicarlas en un registro (GHCR): más
  estándar, pero exige builds multiarquitectura o runner ARM y gestionar un
  registro. Para una VM y un desarrollador, construir en la VM es más simple.
- Kubernetes u otro orquestador: descartado para todo el proyecto (una sola VM).

**Consecuencias.** El build consume CPU de la VM durante el despliegue (breve
degradación). No hay rollback automático: se repite el despliegue con
`workflow_dispatch` sobre un commit anterior.

---

## D-006 · Job `docker` del CI en runner ARM64

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Contexto.** La VM de producción es ARM64 (Ampere A1). Una imagen que construye
en x86 puede fallar en ARM (dependencias sin binarios para ARM, por ejemplo).

**Decisión.** El job `docker` usa `ubuntu-24.04-arm`, gratuito en repositorios
públicos, para construir con la misma arquitectura que producción.

**Alternativa descartada.** Emular ARM con QEMU en un runner x86: funciona, pero
es mucho más lento.

**Consecuencias.** Si el repositorio pasa a privado, ese runner deja de ser
gratuito y habría que revisar esta decisión.

---

## D-007 · Dependabot solo para las versiones de las Actions

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Decisión.** `.github/dependabot.yml` solo actualiza las Actions, una vez al
mes y agrupadas en un único PR. Las dependencias de npm y uv no se actualizan
con PRs periódicos; sus parches de seguridad los cubren las *Dependabot
security updates* activadas en la configuración del repo.

**Motivo.** Menos ruido: un desarrollador no puede revisar un PR por cada
versión menor de cada paquete. Las actualizaciones de seguridad sí llegan.

**Consecuencias.** Las dependencias pueden quedarse atrás en versiones no
relacionadas con la seguridad; se actualizan a mano cuando haga falta.

---

## D-008 · Evals de LLM y pruebas de carga solo manuales

- **Fecha:** 2026-10-01
- **Estado:** Pendiente (2026-10-05: los dos workflows existen en local, pero
  no se suben al repo hasta que puedan funcionar: faltan el módulo de evals, el
  entorno `evals` con sus claves y un backend desplegado contra el que lanzar
  la carga)

**Decisión.** `llm-evals.yml` y `load-test.yml` solo se lanzan con
`workflow_dispatch`, con parámetros (dataset y repeticiones; host, usuarios,
ritmo y duración).

**Motivo.** Gastan tokens de las capas gratuitas de los LLM (con límites de
uso) y tardan. Ejecutarlos en cada PR agotaría la cuota sin aportar nada en
cambios que no tocan el comportamiento del LLM. La metodología estadística de
las evaluaciones está en `docs/plan-de-pruebas.md`.

**Consecuencias.** Hay que acordarse de lanzarlos tras cambios en agentes,
prompts o guardrails. Las evals usan un entorno de GitHub propio (`evals`) para
no mezclar sus claves con las de producción.

---

## D-009 · CI sin claves reales de LLM ni MCP

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Decisión.** El job `backend` del CI no recibe claves de LLM ni de servidores
MCP; los tests usan mocks (`APP_ENV: test`).

**Motivo.** Tests deterministas (un LLM no responde siempre igual), gratuitos y
que no fallan porque un proveedor externo esté caído o limite peticiones.
Además, los PRs no pueden filtrar claves.

**Consecuencias.** El CI no comprueba el comportamiento real del LLM: eso lo
cubren las evals (D-008).

---

## D-010 · Extensiones de Postgres activadas por script de inicialización

- **Fecha:** 2026-10-01
- **Estado:** Aceptada

**Contexto.** La memoria del usuario necesita `vector` (pgvector) y las claves
`uuid` usan `gen_random_uuid()`. La imagen `pgvector/pgvector:pg16` trae los
binarios, pero cada extensión hay que activarla en cada base de datos.

**Decisión.**
- Local y producción: `infra/postgres/init/001_extensions.sql` ejecuta
  `CREATE EXTENSION IF NOT EXISTS vector` y `pgcrypto`. La imagen lo ejecuta
  automáticamente la primera vez que el volumen de datos está vacío.
- CI: el job `backend` ejecuta `CREATE EXTENSION vector` con `psql` antes de
  las migraciones, porque el servicio del CI no monta ese script.

**Alternativa considerada.** Activar las extensiones en la primera migración de
Alembic (`op.execute(...)`). Tendría un único mecanismo en todos los entornos y
funcionaría también con volúmenes ya existentes. Se puede adoptar cuando se
escriba la primera migración; si se hace, sobra el paso de `psql` del CI.

**Consecuencias.**
- El script solo se ejecuta con el volumen vacío: si se añade una extensión
  nueva, una BD ya creada no la recibe (hay que crearla a mano o borrar el
  volumen).
- `pgcrypto` no se activa en CI. No afecta: `gen_random_uuid()` está en el
  núcleo de PostgreSQL desde la versión 13.

---

## D-011 · Backend en un único proceso (API + CrewAI Flow)

- **Fecha:** 2026-10-02
- **Estado:** Aceptada

**Contexto.** Un borrador de `infra/env/.env.example` daba por hecho un backend
partido en servicios de Compose: una `api` pública (JWT y cuota), un
`orchestrator` interno (`ORCHESTRATOR_URL=http://orchestrator:8001`, solo
`expose`) que ejecutaba el Flow y las crews, y un worker que consumía una cola
de Redis para la extracción de hechos del usuario. Ese diseño no estaba
recogido en la documentación.

**Decisión.** El backend es un único servicio FastAPI que ejecuta en el mismo
proceso la API y el CrewAI Flow. Las tareas fuera del camino crítico
(`schedule_background(extract_soft_facts, ...)`, ver
`docs/arquitectura-multiagente-crewai.md`) se lanzan como tareas en segundo
plano de ese proceso. No existe `ORCHESTRATOR_URL`.

**Alternativa descartada.** Separar `api` y `orchestrator` (y un worker). Aísla
la ejecución de crews detrás de la autenticación y evita que una ejecución
larga bloquee la API. Pero duplica imágenes, configuración y despliegue en una
VM de 12 GB compartida y con pocos usuarios. El JWT y la cuota se comprueban
igualmente en las dependencias de FastAPI antes de lanzar el Flow, y CrewAI se
ejecuta de forma asíncrona sin bloquear el bucle de eventos.

**Consecuencias.**
- Un solo `Dockerfile` y un solo servicio de backend en Compose.
- Si se reinicia el contenedor mientras corre una tarea en segundo plano, esa
  tarea se pierde. Para `extract_soft_facts` es aceptable: es una mejora
  oportunista de la memoria, no un dato crítico.
- Si en el futuro hiciera falta escalar la ejecución de crews, la separación
  descartada sigue siendo posible sin cambiar los contratos de datos.

---

## D-012 · Sin Redis: caché en memoria, cuotas en PostgreSQL y Redis como evolución futura

- **Fecha:** 2026-10-02
- **Estado:** Aceptada

**Contexto.** El diseño inicial incluía Redis 7 como "caché/cola", con un
contenedor en Compose, un servicio efímero en el job `backend` del CI y las
variables `REDIS_URL`/`REDIS_PORT`. Los usos previstos eran tres:

| Uso previsto | ¿Imprescindible? | Alternativa sin Redis |
|---|---|---|
| Caché de respuestas MCP con TTL | No | Caché en memoria del proceso (o tabla en Postgres) |
| Contadores de cuota por usuario | No | Tabla en Postgres |
| Cola de tareas de fondo (p. ej. `arq`) | No | Tarea `asyncio` en el propio proceso (D-011), o Postgres como cola con `SELECT … FOR UPDATE SKIP LOCKED` |

La cola es el uso que más complejidad añade (proceso consumidor, reintentos,
tareas atascadas) y ya se descartó en D-011. Redis solo como caché sería
barato, pero con un único proceso de backend no aporta nada que no dé una
caché en memoria.

**Decisión.** No se usa Redis en el TFG. Se elimina del Compose, del CI, de
`infra/env/.env.example` y de la documentación.

- **Caché de respuestas MCP:** en memoria del proceso (`cachetools.TTLCache`,
  con tamaño máximo), detrás de una interfaz en `backend/app/services/` para
  poder cambiar la implementación sin tocar a quien la usa. TTL orientativos:
  Weather 1–3 h, Places y Routes horas, Flight/Hotel 5–15 min (precios y
  disponibilidad cambian). Se complementa con la caché por crew de CrewAI
  (`cache=True`).
- **Cuotas por usuario:** contadores en una tabla de PostgreSQL, porque tienen
  que sobrevivir a reinicios. Se añadirá a `docs/data-model/modelo-datos.md`
  al implementarla.
- **Tareas de fondo** (`extract_soft_facts`): tarea `asyncio` en el proceso del
  backend (D-011), guardando la referencia a la tarea (si no, el recolector de
  basura puede cancelarla) y registrando sus excepciones en los logs.
- **Un único worker de uvicorn.** Es la condición que hace válido todo lo
  anterior: la caché en memoria y el `max_rpm` de CrewAI contra los LLM solo
  son globales si hay un solo proceso.

**Motivos.**
- **Complejidad sin necesidad real.** Otro contenedor, volumen, health check,
  variable de entorno y servicio en el CI, para un beneficio que con pocos
  usuarios no se nota.
- **El beneficio de la caché está dentro de cada conversación** (el Flow y el
  RefinementCrew repiten consultas a los MCP), no entre usuarios: con pocos
  usuarios, que dos pidan lo mismo es poco frecuente. Eso lo cubre la caché en
  memoria.
- **Latencia irrelevante.** El cuello de botella son los LLM y las APIs
  externas (segundos), no la caché (milisegundos).
- **Recursos de la VM.** 12 GB de RAM compartidos por backend, Postgres, Caddy
  y servidores MCP.

**Restricción independiente de la tecnología.** Los términos de Google Maps
Platform limitan qué contenido de Places se puede almacenar (el `place_id` sí;
las coordenadas, de forma temporal; el resto, en general, no). *Actualización:*
desde D-020 los lugares y las rutas no vienen de Google, sino de OpenStreetMap
(Geoapify) y Transitous, que sí permiten guardar los datos con atribución. La
restricción que queda es el uso moderado que pide la API pública de Transitous;
la caché ayuda a cumplirlo.

**Evolución futura: cuándo introducir Redis.** Se reconsidera si se da alguna
de estas condiciones:
1. **Más de un proceso de backend** (varios workers de uvicorn, varias
   réplicas o despliegue sin parada con dos versiones a la vez): la caché en
   memoria deja de ser compartida.
2. **Límites de peticiones globales contra los LLM** con varios procesos: el
   `max_rpm` de CrewAI cuenta por proceso y se superaría la cuota gratuita de
   Groq/Gemini. Un contador común en Redis lo resuelve.
3. **SSE entre varias instancias:** si un cliente se reconecta a otra
   instancia, haría falta pub/sub para reenviarle el stream.
4. **Caché cara de rellenar tras cada despliegue** (cuota diaria de Geoapify o
   uso de la API de Transitous) con despliegues frecuentes.

En ese caso, Redis entraría **solo como caché y contador**, sin persistencia
(`--save "" --appendonly no`), con `maxmemory` y `allkeys-lru`, y con patrón
*cache-aside*: si Redis no responde, se llama al MCP directamente. El cambio
queda acotado a la implementación de la interfaz de caché.

**Validación.** Es una decisión tomada a priori, sin código todavía. Se
comprueba en las pruebas de carga del plan de pruebas; si la caché en memoria
o el proceso único resultan insuficientes, aplican los criterios anteriores.

**Consecuencias.**
- Compose, CI y `.env` más pequeños; un servicio menos que desplegar.
- La caché se vacía en cada reinicio o despliegue. Es aceptable: no es una
  pieza crítica y los despliegues son poco frecuentes.
- Pendiente actualizar en Visual Paradigm `docs/uml/despliegue/Deployment
  Diagram.jpg`: quitar los artefactos **Redis** y **Worker ConversiónFacts**, y
  unir **FastAPI Server** y **Orquestador CrewAI** en un único artefacto
  (D-011). El diagrama de componentes no cambia: ahí el Orquestador CrewAI es
  un componente lógico, no un proceso aparte.

---

## D-013 · Código nuevo de SonarQube: últimos 30 días

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** El quality gate *Sonar way* (D-002) solo evalúa el **código
nuevo**, así que hay que definir qué cuenta como tal en la rama `main`
(*Administration → New Code* en SonarQube Cloud). En los PRs no influye: allí
el código nuevo es siempre el diff del PR. SonarQube Cloud ofrece tres
opciones: *Previous version*, *Number of days* y *Reference branch*.

El proyecto es un TFG con un único desarrollador y despliegue continuo: cada
push a `main` que pasa el CI se despliega (D-005). No hay versiones ni
releases, y `sonar.projectVersion` no se define.

**Decisión.** Se usa *Number of days* con **30 días**: el código nuevo de
`main` es el que ha cambiado en los últimos 30 días.

**Alternativas descartadas.**
- **Previous version.** Necesita que `sonar.projectVersion` cambie en cada
  release. Sin versiones, la "versión anterior" sería siempre el primer
  análisis y todo el código del proyecto contaría como nuevo para siempre.
  Versionar solo para Sonar sería trabajo artificial en un despliegue continuo.
- **Reference branch.** Compara con otra rama de larga duración, como
  `develop`. Solo existe `main`, así que no hay rama con la que comparar.
- **Ventanas más cortas o más largas.** Con una ventana corta (7 días), en
  semanas de poca actividad `main` apenas tiene código nuevo y el gate pierde
  sentido. Con una larga (90 días), la ventana arrastra código antiguo y la
  métrica deja de reflejar el trabajo reciente. 30 días cubre aproximadamente
  un sprint o hito del TFG.

**Consecuencias.**
- El estado del gate en `main` refleja siempre el último mes de trabajo, sin
  tener que mantener versiones.
- La barrera real sigue estando en los PRs (diff del PR, D-002); la ventana de
  30 días afecta a lo que se ve en el panel de `main`.
- Si un incumplimiento entra en `main` (por ejemplo, con un push directo), el
  gate de `main` sigue en rojo hasta corregirlo o hasta que salga de la
  ventana de 30 días.
- Si el proyecto empezara a publicar versiones, se reconsideraría pasar a
  *Previous version*.

---

## D-014 · Python 3.13 en el backend (sustituye a 3.12)

- **Fecha:** 2026-10-04
- **Estado:** Aceptada (aplicada el 2026-10-04 en `backend/pyproject.toml`)

**Contexto.** El stack fijaba Python 3.12. CrewAI 1.15 solo admite
`>=3.10,<3.14`, igual que `crewai-tools` y la instrumentación de OpenInference
para CrewAI, así que 3.14 queda descartado. Situación de cada versión
(octubre de 2026, según endoflife.date):

| Versión | Correcciones de errores | Solo seguridad hasta |
|---|---|---|
| 3.12 | Terminaron en abril de 2025 | Octubre de 2028 |
| 3.13 | Hasta octubre de 2026 (3.13.16) | Octubre de 2029 |
| 3.14 | Activas | Octubre de 2030 (CrewAI no la admite) |

**Decisión.** Python **3.13**, la versión más reciente que admite CrewAI:
`requires-python = ">=3.13,<3.14"` y `.python-version` con `3.13`.

**Comprobaciones hechas.** Todas las dependencias compiladas publican ruedas
para Linux ARM64 (la VM de Oracle) con Python 3.13: `pydantic-core`,
`psycopg-binary`, `tiktoken`, `regex` y `numpy` con ruedas `cp313`, y
`chromadb`, `lancedb`, `tokenizers` y `pymupdf` (dependencias de CrewAI) con
ruedas `abi3`. La imagen `python:3.13-slim` existe para `arm64`.

**Alternativas descartadas.**
- **Mantener 3.12.** Funciona, pero lleva año y medio sin correcciones de
  errores. Las de 3.13 son las últimas que ha recibido una versión compatible
  con CrewAI.
- **3.14.** CrewAI, `crewai-tools` y `ag-ui-crewai` la excluyen.

**Consecuencias.**
- Actualizados `CLAUDE.md` y `docs/architecture/arquitectura-sistema.md`. Si
  la memoria del TFG menciona Python 3.12, hay que cambiarlo también allí.
- La imagen Docker del backend será `python:3.13-slim-bookworm`: misma base
  Debian que la de Postgres (D-015).
- Cuando CrewAI admita 3.14, se reconsidera.

---

## D-015 · PostgreSQL 16 se mantiene, con la imagen fijada a una versión concreta

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** PostgreSQL 18 (septiembre de 2025, ya en 18.6) es la versión más
reciente. Aporta `uuidv7()` nativo y E/S asíncrona. El compose y el CI usaban
la etiqueta flotante `pgvector/pgvector:pg16`, que cambia sola cada vez que
sale una versión nueva de pgvector o de Postgres.

**Decisión.**
- Se mantiene **PostgreSQL 16**.
- La imagen se fija a **`pgvector/pgvector:0.8.7-pg16-bookworm`** en el
  compose y en el servicio del job `backend`. Es exactamente la misma imagen
  que servía `pg16` hoy (mismo *digest* en `amd64` y `arm64`), así que no
  cambia nada para un volumen local ya creado.

**Motivos.**
- PostgreSQL da **correcciones completas a todas sus versiones durante 5
  años**. A diferencia de Python, la 16 sigue recibiendo arreglos hasta
  noviembre de 2028, más allá del final del TFG.
- Ninguna función de PostgreSQL 17 o 18 es necesaria para el diseño. Los UUID
  aleatorios de `gen_random_uuid()` bastan con los volúmenes del proyecto.
- **pgvector 0.8** (incluido en la imagen) sí aporta algo clave: los
  *iterative index scans* (`hnsw.iterative_scan`). Sin ellos, una búsqueda
  HNSW filtrada por `user_id` (RNF-6.3) puede devolver menos de los *k*
  resultados pedidos, porque el filtro se aplica después del índice. Con ellos,
  el índice sigue buscando hasta completar el Top-K (RNF-8.4).

**Alternativas descartadas.**
- **PostgreSQL 18.** Cambia la ruta de datos de la imagen Docker (el volumen
  se monta en `/var/lib/postgresql`, no en `.../data`) y obliga a revisar
  documentación y memoria, sin aportar nada que el diseño necesite.
- **Variante `trixie` de la imagen.** Cambia la glibc (2.36 → 2.41). Un
  cambio de glibc puede alterar el orden de las *collations* y obliga a
  reindexar los índices de texto de una base ya creada.
- **Seguir con la etiqueta flotante `pg16`.** Un `docker compose pull` podía
  cambiar de versión de pgvector sin que nadie lo decidiera, y el CI y la VM
  podían acabar con versiones distintas.

**Consecuencias.**
- Actualizar pgvector o Postgres es un cambio explícito de la etiqueta en el
  compose y en `ci.yml`. Dependabot no lo cubre (D-007).
- Si en el futuro se migra a 18, hay que hacer volcado y restauración
  (`pg_dump`/`pg_restore`) o `pg_upgrade`, y cambiar el punto de montaje del
  volumen.

---

## D-016 · Versiones del backend y política de fijado

- **Fecha:** 2026-10-04
- **Estado:** Aceptada (aplicada el 2026-10-04 en `backend/pyproject.toml`)

**Contexto.** `backend/pyproject.toml` declara las dependencias del backend
con sus rangos de versiones, la versión de Python y la configuración de las
herramientas (ruff, pyright, pytest). `uv.lock` guarda la versión exacta que se
instala, con *hashes*. El CI instala con `uv sync --frozen`, así que sin
`uv.lock` el job falla.

**Política.**
- **`pyproject.toml` con rangos y `uv.lock` con versiones exactas**
  (determinismo, RNF-8.6). Los rangos admiten parches y versiones menores
  compatibles; el lockfile congela lo que se instala de verdad.
- **Versión exacta (`==`) solo donde un cambio de versión altera el resultado
  sin tocar código:** CrewAI (su API cambia entre versiones menores, como avisa
  `docs/arquitectura-multiagente-crewai.md`), ruff (`ruff format --check`
  fallaría por un cambio de estilo) y pyright (cada versión añade
  comprobaciones).
- **Los límites que imponen las dependencias mandan sobre "la última
  versión".** CrewAI fija varias dependencias por debajo de su última versión;
  se documentan aquí para no intentar subirlas a mano.

**Versiones (comprobadas en PyPI el 2026-10-04).**

| Paquete | Rango en `pyproject.toml` | Motivo |
|---|---|---|
| `crewai[litellm]` | `==1.15.23` | Última estable. El extra `litellm` da acceso uniforme a Groq, Gemini y Azure OpenAI (cambiar de proveedor = variable de entorno, RNF-8.1). |
| `crewai-tools[mcp]` | `==1.15.23` | Exige la misma versión exacta de `crewai`. El extra `mcp` trae `mcpadapt` para conectar los servidores MCP. |
| `pydantic` | `>=2.12.5,<2.13` | **CrewAI exige `<2.13`**: la última (2.13.5) no es instalable. |
| `mcp` | *(no se declara)* | Lo fija CrewAI (`~=1.28.1`) aunque ya exista la 2.x. Los servidores MCP propios, en su propio contenedor, no están atados a este límite. |
| `httpx` | *(no se declara)* | Lo fija CrewAI (`~=0.28.1`). |
| `fastapi` | `>=0.142.2,<0.143` | FastAPI sigue en 0.x y puede romper compatibilidad entre versiones menores. |
| `uvicorn[standard]` | `>=0.54,<0.55` | Un solo worker (D-011). |
| `pydantic-settings` | `>=2.15,<3` | Configuración desde `.env`. Compatible con el rango de CrewAI. |
| `sqlalchemy` | `>=2.0.54,<2.1` | La 2.1.0 salió el 2026-09-24. Se espera a que acumule correcciones y a que Alembic y `pgvector` confirmen soporte. |
| `alembic` | `>=1.20,<2` | Migraciones. |
| `psycopg[binary,pool]` | `>=3.3.6,<3.4` | Driver de PostgreSQL (`postgresql+psycopg://`). |
| `pgvector` | `>=0.5,<0.6` | Tipo `Vector` para SQLAlchemy. |
| `ag-ui-protocol` | `>=1.0,<2` | Eventos AG-UI hacia CopilotKit (D-017). |
| `langfuse` | `>=4.16,<5` | SDK v4 sobre OpenTelemetry, compatible con el OpenTelemetry que exige CrewAI. |
| `openinference-instrumentation-crewai` | `>=1.1.20,<2` | Envía a Langfuse las trazas de agentes, tareas y herramientas. |
| `pyjwt` | `>=2.15,<3` | JWT (RF-01.02). CrewAI exige `>=2.13`. |
| `pwdlib[argon2]` | `>=0.3.1,<0.4` | Hash de contraseñas con Argon2 (RNF-6.1). Es la librería que recomienda la documentación de FastAPI. |

Desarrollo (`[dependency-groups] dev`):

| Paquete | Rango | Motivo |
|---|---|---|
| `pytest` | `>=9.1,<10` | Compatible con `pytest-asyncio` (`<10`). |
| `pytest-asyncio` | `>=1.4,<2` | Tests de los hooks y del Flow, que son asíncronos. |
| `pytest-cov` | `>=7.1,<8` | Genera `coverage.xml` para SonarQube. |
| `ruff` | `==0.16.10` | Exacta: lint y formato reproducibles. |
| `pyright` | `==1.1.414` | Exacta: comprobación de tipos reproducible. |
| `httpx2` | `>=2.13,<3` | Cliente HTTP que usa el `TestClient` de Starlette 1.x (con `httpx` avisa de que está obsoleto y pyright no conoce los tipos). Es otro paquete, así que no choca con el `httpx` que fija CrewAI. |

Herramientas fuera de `pyproject.toml`:
- **uv 0.12.x**, con `[tool.uv] required-version = ">=0.12,<0.13"`, y la misma
  versión fijada en `astral-sh/setup-uv`.
- **Locust** se ejecuta con `uvx` en `load-test.yml`, sin formar parte del
  entorno del backend. Se fija con `uvx locust==2.46.6`.
- **pip-audit** también va con `uvx`, por la misma razón y por necesidad: la
  2.10 exige `tomli-w>=1.2` y CrewAI fija `tomli-w~=1.1.0`, así que no caben en
  el mismo entorno. Se audita el lockfile exportado:
  `uv export --format requirements-txt | uvx pip-audit -r /dev/stdin`.

**Consecuencias.**
- CrewAI publica versiones casi a diario. Se actualiza a mano, leyendo el
  changelog, y nunca durante una campaña de evaluación de hipótesis (los
  resultados dejarían de ser comparables).
- Al subir CrewAI, se revisan los límites de Pydantic, `mcp` y `httpx` de esta
  tabla.
- CrewAI arrastra `chromadb` y `lancedb` aunque el diseño no los use (la
  memoria vectorial es pgvector). Aumentan el tamaño de la imagen, pero no se
  pueden quitar sin dejar de usar CrewAI.

---

## D-017 · AG-UI con `ag-ui-protocol`, sin `ag-ui-crewai` ni el SDK Python de CopilotKit

- **Fecha:** 2026-10-04
- **Estado:** Pendiente (se aplica al implementar el hook `emit_agui_events`)

**Contexto.** El frontend (CopilotKit) recibe el progreso del Flow como
eventos AG-UI por SSE (RNF-3.4, hook `emit_agui_events`). Hay tres paquetes de
Python para producirlos:

| Paquete | Qué impone |
|---|---|
| `ag-ui-crewai` 0.3.1 | `fastapi<0.116` y `uvicorn<0.35`: fija FastAPI a una versión de 2025 |
| `copilotkit` (Python) 0.1.96 | Instala `langchain` y `langgraph`, que el proyecto no usa |
| `ag-ui-protocol` 1.0.0 | Solo Pydantic. Tipos de los eventos y codificador SSE |

**Decisión.** Se usa **`ag-ui-protocol`** directamente. El hook
`emit_agui_events` construye los eventos y FastAPI los emite con una
`StreamingResponse`.

**Motivos.**
- Encaja con el diseño: el Flow, sus hooks y su estado son propios (§7.5 de la
  arquitectura multiagente). `ag-ui-crewai` está pensado para exponer un Flow
  tal cual, sin hooks propios.
- Evita congelar FastAPI y Uvicorn en versiones antiguas, y no añade LangChain.
- Es la misma versión del protocolo que usa el frontend: `@copilotkit/runtime`
  1.77 depende de `@ag-ui/client` y `@ag-ui/core` 1.0.1.

**Consecuencias.** Hay que escribir a mano la correspondencia entre el estado
del Flow y los eventos AG-UI (inicio y fin de cada tarea, deltas de estado,
mensajes). Es poco código y queda bajo control del proyecto.

---

## D-018 · Versiones del frontend: Node 24, pnpm 10, TypeScript 6 y ESLint 9

- **Fecha:** 2026-10-04
- **Estado:** Aceptada (aplicada el 2026-10-04 en `frontend/package.json`)

**Contexto.** `frontend/package.json` declara las dependencias, los scripts que
llama el CI (`lint`, `typecheck`, `test:coverage`, `build`,
`build-storybook`), la versión de Node (`engines`) y la de pnpm
(`packageManager`). Como en el backend, la última versión publicada no siempre
es compatible con el resto: hay cuatro casos.

**Decisión: los cuatro casos en los que no se usa la última versión.**

| Tecnología | Última | Elegida | Motivo |
|---|---|---|---|
| Node.js | 26 (LTS el 2026-10-28) | **24 LTS** | Vercel solo ofrece 20, 22 y 24. La 24 tiene soporte hasta abril de 2028. |
| pnpm | 12 | **10** | Vercel solo admite pnpm 6–10 de forma nativa; 11 y 12 necesitan Corepack experimental. |
| TypeScript | 7.0 (compilador nativo) | **6.0** | `typescript-eslint` (incluido en `eslint-config-next`) solo admite `typescript <6.1`. |
| ESLint | 10 | **9** | `eslint-plugin-react`, `jsx-a11y` e `import` (dentro de `eslint-config-next`) solo admiten ESLint ≤ 9. |

**Resto de versiones (comprobadas en npm el 2026-10-04).**

| Paquete | Rango | Motivo |
|---|---|---|
| `next` / `eslint-config-next` | `^16.3.8` | Next 15 deja de tener soporte el 2026-10-21. |
| `react`, `react-dom` | `^19.3.0` | Compatible con Next 16, CopilotKit y Testing Library. |
| `@copilotkit/react-core`, `react-ui`, `runtime` | `1.77.0` (exacta, la misma en los tres) | CopilotKit publica con mucha frecuencia y las tres piezas deben ir a la par. Usa AG-UI 1.0 (D-017). Nota: `@copilotkit/runtime` instala LangChain de forma transitiva (a través de `@ag-ui/langgraph`). Solo se ejecuta en el servidor de Next, no llega al navegador ni lo usa el proyecto, y no se puede quitar sin renunciar a CopilotRuntime. Un paquete interno (`@copilotkit/channels-core`) declara Vitest 4 como *peer*; es un aviso sin efecto en ejecución. |
| `@vanilla-extract/css` | `^1.21` | Estilos (RF-03.01). |
| `@vanilla-extract/next-plugin` | `^2.5.2` | Su soporte de Turbopack (el compilador por defecto de Next 16) es **experimental** y viene desactivado. Se compila con **Webpack**, que Next 16 sigue soportando: `next dev --webpack` y `next build --webpack`. Se revisa cuando el soporte de Turbopack sea estable. |
| `@vanilla-extract/vite-plugin` | `^5.2` | Para Storybook y Vitest, que usan Vite. |
| `storybook`, `@storybook/nextjs-vite`, `@storybook/addon-vitest` | `^10.6` | Constructor Vite: más rápido y reutiliza el plugin de Vanilla Extract. |
| `vitest`, `@vitest/coverage-v8` | `^5.0` | D-019. Exige Node 22.12+ o 24. |
| `@testing-library/react` | `^16.3` | Tests de componentes. |
| `@playwright/test` | `^1.63` | Aceptación multinavegador (opcional en el plan de pruebas). |
| `typescript` | `~6.0.3` | Ver tabla anterior. |
| `eslint` | `^9.39` | Ver tabla anterior. Next 16 ya no incluye `next lint`, así que el script `lint` llama a `eslint` directamente. |
| `json-schema-to-typescript` | `^16` | Genera `shared/types` desde el JSON Schema de Pydantic. |

**Consecuencias.**
- `engines.node: "24.x"` y `.nvmrc` con `24`. En los workflows,
  `node-version: 24` sustituye a `lts/*`: el 2026-10-28 `lts/*` pasará a
  significar Node 26 y el CI dejaría de usar la misma versión que Vercel.
- `packageManager: "pnpm@10.34.6"`. pnpm 10 deja de tener soporte en abril de
  2027; si Vercel admite ya pnpm 11 o superior, se sube entonces.
- Se revisan TypeScript 7 y ESLint 10 cuando `typescript-eslint` y los
  plugins de `eslint-config-next` los admitan.
- El esqueleto inicial (2026-10-04) aún no instala tres paquetes de la tabla:
  `@storybook/addon-vitest` (necesita Vitest en modo navegador con
  Playwright), `@playwright/test` (llega con los tests e2e) y
  `json-schema-to-typescript` (va en `shared/`, con el job `contracts`).

---

## D-019 · Vitest para los tests del frontend

- **Fecha:** 2026-10-04
- **Estado:** Aceptada (aplicada el 2026-10-04 en `frontend/package.json`)

**Contexto.** `docs/plan-de-pruebas.md` fija desde el principio **Vitest con
Testing Library** para los tests de componentes. Una línea de los comandos de
`CLAUDE.md` mencionaba Jest por error. Esta entrada no cambia la herramienta:
deja escrito por qué es Vitest y no Jest, para justificarlo en la memoria.

**Decisión.** Se mantiene **Vitest** con Testing Library, como dice el plan de
pruebas. Se corrige la errata de `CLAUDE.md`.

**Motivos.**
- **Un solo pipeline de compilación.** Storybook usa Vite, y Vitest también.
  Los estilos de Vanilla Extract (`*.css.ts`) se procesan en los tests con el
  mismo plugin.
- **Las *stories* sirven como tests.** `@storybook/addon-vitest` ejecuta cada
  *story* como un test de componente. Cada componente documentado en
  Storybook (RNF-7.4) queda probado sin escribir el test dos veces.
- TypeScript y ESM sin configuración adicional, y la documentación oficial de
  Next.js describe cómo configurarlo.

**Alternativa descartada: Jest.** Las pruebas se escriben casi igual
(`describe`, `it`, `expect`), pero Jest necesitaría un transformador propio para
Vanilla Extract (`@vanilla-extract/jest-transform`), Babel o SWC para TypeScript
y ESM, y una configuración aparte de la de Storybook. No tiene integración con
`@storybook/addon-vitest`.

**Consecuencias.**
- El script `test:coverage` es `vitest run --coverage`, con el informe `lcov`
  en `frontend/coverage/lcov.info`, la ruta que espera SonarQube.
- Los tests van en `frontend/tests/` (`unit`, `integration`, `e2e`), nunca
  junto al código en `src/`. Así lo exige `sonar-project.properties`, y Vitest
  se configura para buscar solo ahí (`include: ['tests/**/*.test.{ts,tsx}']`).

---

## D-020 · Lugares y rutas con datos abiertos: Places MCP (Geoapify) y Routes MCP (Transitous), dos agentes

- **Fecha:** 2026-10-04
- **Estado:** Pendiente (de desarrollar; cambia `docs/arquitectura-multiagente-crewai.md`)

**Contexto.** El diseño usaba un único *Places & Routes Specialist* con Google
Maps Platform MCP. Con una cuenta de facturación en el EEE (España), desde el 8
de julio de 2025 se aplican términos específicos. Leídos el 2026-10-04:

- [EEA Service Specific Terms](https://cloud.google.com/terms/maps-platform/eea/maps-service-terms),
  §15 Places API: salvo latitud, longitud y `place_id`, el contenido no se
  puede usar "con ningún mapa", **incluido uno de Google**. Además, solo se
  puede usar para los *Permitted Uses*.
- [Places API EEA Permitted Uses](https://cloud.google.com/terms/maps-platform/eea-places-api-permitted-uses):
  es una lista cerrada de 9 usos (autocompletar direcciones, tiendas propias,
  CRM, notas, inmobiliaria, transacciones, juegos, redes sociales, domótica).
  **Planificar viajes no está entre ellos**: TripPlanner no puede usar nombres,
  horarios ni accesibilidad de Places API, ni siquiera sin mapa.
- §20 Routes API: los pasos de una ruta no se pueden mostrar con un mapa.
- §11 Maps Grounding Lite, la vía de Google para LLMs: prohíbe separar el
  contenido de Google de la respuesta generada y solo deja cachearlo 30 días
  para evaluación. Choca con extraer horarios a Pydantic para los guardrails y
  con guardar el itinerario. Además, no da horarios estructurados ni transporte
  público.
- [Políticas de Places API](https://developers.google.com/maps/documentation/places/web-service/policies),
  también fuera del EEE: no se puede guardar contenido salvo el `place_id`.
  Afectaría a `itinerary_items`, `trip_revisions`, `flow_states`, el
  `tool_ledger` y las trazas de Langfuse.

**Decisión.** Lugares y rutas pasan a **datos abiertos**, con **dos servidores
MCP y, por la regla de un agente por servidor, dos agentes**: 8 en total.

| Agente | Servidor MCP | Datos | Requisitos |
|---|---|---|---|
| **Places Specialist** (T5, R2) | [Geoapify MCP](https://apidocs.geoapify.com/docs/mcp/), oficial, alojado por Geoapify, Streamable HTTP | OpenStreetMap: lugares por categoría, `opening_hours`, accesibilidad (`wheelchair`), coordenadas | RF-04.07–04.09 |
| **Routes Specialist** (T6, R2b) | [transitous-mcp](https://github.com/Movm/transitous-mcp) en un contenedor propio (`mcp-routes`), Streamable HTTP | [Transitous](https://transitous.org/api/) (MOTIS): rutas a pie y en transporte público con línea, transbordos, horarios y accesibilidad | RF-04.10–04.11 |

- **Aislamiento de herramientas:** el Geoapify MCP también expone herramientas de
  rutas, pero al Places Specialist solo se le inyectan las de lugares y
  geocodificación. Las rutas son siempre del Routes Specialist.
- **RefinementCrew:** se añade la tarea R2b `requery_transfers` (Routes
  Specialist) cuando un cambio altera la ubicación o el orden de algún ítem.
  La crew pasa a 3–4 agentes y 4–5 tareas.

**Alternativas descartadas.**
- **Google Places API + Places UI Kit.** UI Kit solo sirve para mostrar fichas
  en el navegador; los agentes no podrían razonar con horarios ni
  accesibilidad (no es un *Permitted Use*).
- **Maps Grounding Lite.** No se pueden separar ni guardar los datos, y no hay
  horarios estructurados ni transporte público.
- **Foursquare Places.** [Solo deja guardar los identificadores](https://openplacesapi.com/blog/can-you-store-places-api-results),
  igual que Google.
- **Servidores MCP de OSM de la comunidad**
  ([cyanheads](https://github.com/cyanheads/openstreetmap-mcp-server),
  [ni-c](https://github.com/ni-c/osm-mcp)). Usan los servidores públicos de
  Nominatim y OSRM, con límites de uso estrictos (1 petición por segundo, o no
  aptos para producción), y son proyectos pequeños. Geoapify es un proveedor con
  servicio mantenido y la misma fuente de datos.
- **Un servidor MCP propio que combine Geoapify y Transitous** (un solo agente).
  Mantenía los 7 agentes, pero obligaba a escribir y mantener un servidor más.
  Se prefiere separar los agentes.

**Consecuencias.**
- **8 agentes.** Actualizados `CLAUDE.md`, la arquitectura multiagente (§1, §3,
  §4, §6, §7, §11, §13–15), `requisitos.md`, `estado-del-arte.md`,
  `arquitectura-sistema.md` y `infra/env/.env.example`. D-012 queda sin la
  restricción de Google.
- **Los datos se pueden guardar** (OpenStreetMap, licencia ODbL) en
  `itinerary_items` y en `trip_revisions`, y se pueden mostrar con cualquier
  mapa. La interfaz debe mostrar la atribución "© OpenStreetMap contributors",
  la de Geoapify (obligatoria en su plan gratuito) y un enlace a las fuentes de
  Transitous.
- **Cuotas:** Geoapify gratis hasta 3.000 créditos/día y 5 peticiones/segundo,
  con uso en producción permitido ([precios](https://www.geoapify.com/pricing/)).
  La API de Transitous es gratuita, de voluntarios y sin garantías. Exige uso
  no comercial, código abierto (el repo es público) y uso moderado; el
  servidor MCP ya cachea y limita a 20 llamadas por minuto.
- **Riesgos y cómo se cubren:**
  - Horarios incompletos en OSM fuera de los lugares grandes → `gap` y lector
    web acotado (§7.4). El escenario V11 del plan de pruebas lo cubre.
  - Caída de Transitous → estimación geométrica con `source=assumed` (§7.4).
  - `transitous-mcp` es un proyecto pequeño → si se abandona, se sustituye o se
    hace un *fork*; el cambio queda dentro del servidor MCP.
  - Cobertura de transporte público de cada destino → comprobarla para los
    destinos de los escenarios V01–V12.
- **Pendiente de desarrollar:**
  - servicio `mcp-routes` en el Compose cuando se añada el backend;
  - clientes MCP con el filtro de herramientas de Geoapify;
  - elegir la librería del mapa del frontend (ya no está condicionada por
    Google);
  - actualizar en Visual Paradigm el diagrama de casos de uso del módulo 4 y
    el de despliegue. El diagrama original ya mostraba "Places MCP" y "Bus MCP"
    como dos cajas;
  - actualizar la memoria del TFG (§15 de la arquitectura).

---

## D-021 · Esqueleto mínimo de backend y frontend para que el CI pase de verdad

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** Con `backend/` y `frontend/` vacíos, los jobs `backend` y
`frontend` del CI fallaban: sin manifiestos no se instala nada, `alembic`
necesita su configuración, `pytest` sin tests devuelve el código 5, Vitest
falla si no encuentra tests y Next y Storybook necesitan al menos una página y
una *story*. Con `ci-ok` como check obligatorio en `main`, no se podía fusionar
nada.

**Decisión.** Crear el esqueleto mínimo que ejercita todo el pipeline, en vez
de saltar los jobs hasta que haya código.

| Parte | Qué se crea | Para qué |
|---|---|---|
| Backend | `pyproject.toml`, `uv.lock`, `.python-version` | Dependencias de D-016 y Python 3.13 (D-014) |
| Backend | `app/main.py` + `app/api/health.py` (`GET /health`) | Lo necesita el *smoke test* de `deploy-backend.yml` |
| Backend | `app/core/config` (`pydantic-settings`) | Configuración desde el entorno. `DATABASE_URL` es obligatoria y sin valor por defecto: no hay credenciales en el código (evita un *hotspot* de SonarQube) |
| Backend | `alembic.ini` + `app/db/migrations/` (sin migraciones) + `app/db/base.py` | `alembic upgrade head` funciona ya. La primera migración llegará con el esquema de `modelo-datos.md` |
| Backend | `tests/unit/{api,core,db}/` | 4 tests, 100 % de cobertura |
| Frontend | `package.json`, `pnpm-lock.yaml`, `.nvmrc` | Dependencias de D-018 y Node 24 |
| Frontend | `src/app/layout.tsx`, `src/app/(marketing)/page.tsx`, `src/features/landing/` | Una página de inicio con estilos de Vanilla Extract. Usa la estructura de carpetas que ya existía (grupos de rutas, `features/`) |
| Frontend | `vitest.config.ts`, `tests/setup.ts`, `tests/unit/features/landing/` | 2 tests, 100 % de cobertura |
| Frontend | `.storybook/` + `stories/Landing.stories.tsx` | `build-storybook` necesita al menos una *story* |

Detalles que conviene conocer:
- **Tests del backend con `--import-mode=importlib`**: las carpetas de tests no
  llevan `__init__.py` y pueden repetir nombres de fichero sin chocar.
- **Exclusiones de cobertura** (aplicación de D-002): los ficheros de estilos
  (`*.css.ts`) y el layout raíz de Next no tienen lógica que probar. Se
  excluyen igual en `vitest.config.ts` y en `sonar.coverage.exclusions`, para
  que la cobertura local y la de SonarQube coincidan.
- `sonar.python.version` pasa a 3.13 (seguía en 3.12).
- Sobran los `.gitkeep` de `backend/app`, `frontend/src` y `frontend/tests`:
  ya tienen ficheros reales.

**Alternativa descartada.** Saltar los jobs `backend` y `frontend` mientras
no existan los manifiestos, como hace `contracts`. Era más rápido, pero el CI
no comprobaba nada y SonarQube no recibía ningún análisis con cobertura.

**Consecuencias.**
- Todos los pasos de los jobs `backend` y `frontend` se han ejecutado en local
  con éxito. El único que no se ha probado contra una base de datos real es
  `alembic upgrade head` (Docker no estaba arrancado); se ha validado en modo
  `--sql`.
- El primer push activará también `contracts` (cambia `backend/app/api/`),
  que se salta solo porque aún no hay generador.

---

## D-022 · Next.js compila con Webpack, no con Turbopack

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** Next 16 usa Turbopack por defecto. El plugin de Vanilla Extract
(RF-03.01) añade configuración de Webpack, y su soporte de Turbopack es
**experimental y viene desactivado** (`unstable_turbopack`): "su API es
inestable y puede no cubrir todas las funciones de Next.js", según su
documentación. El primer `next build` falló por esa razón.

**Decisión.** Compilar con **Webpack**, que Next 16 sigue soportando:
`next dev --webpack` y `next build --webpack` en los scripts de
`package.json`.

**Alternativa descartada.** Activar `unstable_turbopack: { mode: 'auto' }`.
Compila más rápido, pero es una integración experimental en el camino del
build de producción y del CI.

**Consecuencias.** Las compilaciones son algo más lentas que con Turbopack. Se
revisa cuando el soporte de Turbopack del plugin sea estable. Storybook y
Vitest no se ven afectados: usan Vite.

---

## D-023 · Lint y tipado estrictos en backend y frontend

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** `CLAUDE.md` pide tipado estricto en TypeScript y en Python, y
SonarQube exige nota A en mantenibilidad (D-002).

**Decisión.**

| Herramienta | Configuración | Motivo |
|---|---|---|
| ruff | Reglas `E`, `W`, `F`, `I`, `B`, `UP`, `N`, `S`, `SIM`, `ASYNC`, `RUF`; líneas de 100; `assert` permitido solo en `tests/` | Además de estilo, detecta errores probables (`B`), seguridad (`S`, las reglas de Bandit) y fallos con `async` |
| pyright | `typeCheckingMode = "strict"`; excluye `tests/load` | Locust se ejecuta con `uvx` y no está en el entorno, así que pyright no puede resolverlo |
| TypeScript | `strict` + `noUncheckedIndexedAccess`; `types: ["node"]` | Acceder a un array o un objeto por índice devuelve `T \| undefined`, que es lo que pasa en realidad |
| ESLint | `eslint-config-next` (`core-web-vitals` + `typescript`), configuración plana | La configuración que mantiene Next |
| `typecheck` | `next typegen && tsc --noEmit` | `next typegen` genera los tipos de las rutas de Next antes de comprobar; sin él, `tsc` falla en un checkout limpio como el del CI |

Dos excepciones, documentadas en el código:
- `Settings()` lleva `# pyright: ignore[reportCallIssue]`: `pydantic-settings`
  rellena los campos desde el entorno y pyright no lo sabe.
- Next añade `allowJs: true` a `tsconfig.json` en cada ejecución si no está; se
  deja para que no reescriba el fichero.

**Consecuencias.** El código nuevo tiene que pasar estas reglas desde el
principio. Relajar una regla es una decisión que se anota aquí.

---

## D-024 · pnpm no ejecuta scripts de instalación de dependencias

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Contexto.** pnpm 10 bloquea por defecto los scripts de instalación de las
dependencias (`postinstall` y similares), que son una vía habitual de ataques
a la cadena de suministro. En este proyecto los piden cuatro paquetes:
`esbuild`, `@swc/core`, `unrs-resolver` y `@scarf/scarf`.

**Decisión.** No aprobar ninguno. Se declaran en
`frontend/pnpm-workspace.yaml` como `ignoredBuiltDependencies`.

**Motivos.** Los tres primeros reciben su binario nativo ya compilado como
dependencia opcional; su script solo lo comprueba. `@scarf/scarf` solo envía
telemetría de instalación. Con todos bloqueados, lint, tipos, tests, el build
de Next y el de Storybook funcionan.

**Consecuencias.** Si una dependencia futura necesita de verdad su script, se
añade a `onlyBuiltDependencies` en el mismo fichero y se anota aquí.

---

## D-025 · Entorno de desarrollo local en Windows: uv, Corepack y `.venv`

- **Fecha:** 2026-10-04
- **Estado:** Aceptada

**Decisión.**
- **uv 0.12.23**, instalado con `winget install astral-sh.uv`: la misma versión
  que fija el CI (D-016). uv descarga solo Python 3.13 cuando hace falta; no se
  instala Python aparte.
- **Entorno virtual en `backend/.venv`**, creado con `uv sync` (ya está en
  `.gitignore`). VS Code debe usarlo como intérprete (*Python: Select
  Interpreter*), o marcará las dependencias como no instaladas.
- **pnpm con Corepack** (`corepack enable pnpm`): usa la versión del campo
  `packageManager` de `package.json` (10.34.6), así que local y CI coinciden.
  Para que no pregunte antes de descargarla: `COREPACK_ENABLE_DOWNLOAD_PROMPT=0`.

**Pendiente.**
- **Node 24 en local.** El equipo tiene Node 22.23 (con nvm-windows). Funciona,
  porque todas las dependencias admiten Node 22, pero pnpm avisa de que
  `engines` pide 24. Basta con `nvm install 24` y `nvm use 24`.
- **Docker Desktop arrancado** para probar `alembic upgrade head` contra
  Postgres y levantar el compose.

**Consecuencias.** En Windows, borrar `node_modules` con `Remove-Item` falla
por las rutas largas de pnpm. Hay que usar `cmd /c rd /s /q node_modules`.

---

## D-026 · Actions fijadas por SHA de commit y actualizadas a sus últimas versiones

- **Fecha:** 2026-10-05
- **Estado:** Aceptada

**Contexto.** Los workflows referenciaban las Actions por etiquetas mayores
antiguas (`actions/checkout@v4`, `astral-sh/setup-uv@v6`,
`SonarSource/sonarqube-scan-action@v5`…), que además corren en Node 20. Antes
del primer push había que actualizarlas, y dos hechos obligan a cambiar también
la forma de referenciarlas:
- **Una etiqueta es un puntero que se puede mover.** El 19 de marzo de 2026,
  con credenciales robadas, un atacante reescribió 76 de las 77 etiquetas de
  `aquasecurity/trivy-action` (la que usa el job `docker`) para que apuntaran a
  código que robaba credenciales (aviso GHSA-69fq-xp46-6x23). Solo se libraron
  la release inmutable 0.35.0 y quien la tenía fijada por SHA. En 2025 pasó lo
  mismo con `tj-actions/changed-files`.
- **`astral-sh/setup-uv` ya no publica etiquetas mayores** desde la v8,
  precisamente por eso: `@v10` no existe y hay que fijar una versión exacta.

**Decisión.** Toda Action se referencia por el SHA completo del commit, con la
versión en un comentario al final de la línea:

```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
```

Un SHA no se puede reescribir: apunta siempre al mismo código. Dependabot (D-007)
entiende este formato y en sus PRs mensuales actualiza a la vez el SHA y el
comentario.

Versiones aplicadas, tras leer las notas de cada salto mayor:

| Action | Antes | Ahora | Cambio incompatible que podría afectar | ¿Afecta? |
|---|---|---|---|---|
| `actions/checkout` | v4 | v7.0.1 | v6 guarda las credenciales en un fichero aparte; v7 bloquea hacer checkout de PRs de forks en `pull_request_target` y `workflow_run` | No: no se usan esos eventos con checkout |
| `actions/setup-node` | v4 | v7.0.0 | v5 activa la caché sola si hay `packageManager`; v6 la limita a npm | No: la caché de pnpm ya se pide con `cache: pnpm` |
| `actions/upload-artifact` | v4 | v7.0.1 | Solo Node 24 y ESM | No |
| `actions/download-artifact` | v4 | v8.0.1 | v5 cambia la ruta al descargar **por ID**; v8 falla si el hash no coincide | No: se descarga por nombre |
| `astral-sh/setup-uv` | v6 | v10.2.0 | v7 quita `server-url`; v9 deja de podar la caché; v10 desactiva la caché automática en `pull_request_target`, `workflow_run` y `release` | No: se usa `enable-cache: true` explícito y ninguno de esos eventos |
| `pnpm/action-setup` | v4 | v6.1.0 | v5 pasa a Node 24; v6 y v6.1 añaden soporte de pnpm 11 y 12 | No: sigue instalando la versión de `packageManager`, pnpm 10.34.6 (D-018) |
| `dorny/paths-filter` | v3 | v4.0.3 | Solo Node 24 | No |
| `SonarSource/sonarqube-scan-action` | v5 | v8.3.0 | v6 cambia cómo se parsea `args`; v8 verifica la firma del escáner | No: no se usa `args` |
| `aquasecurity/trivy-action` | v0.36.0 | v0.36.0 | Ya era la última; release inmutable posterior al ataque | — |
| `treosh/lighthouse-ci-action` | v12 | v12 | Ya era la última | — |
| `appleboy/ssh-action` | v1 | v1.2.5 | Ninguno (misma versión mayor) | — |

De paso, `load-test.yml` cumple ya lo que decía D-016 y no hacía: `setup-uv`
con `version: "0.12.23"` y `uvx locust==2.46.6`.

**Alternativas descartadas.**
- **Etiquetas mayores (`@v7`):** más legibles y reciben parches solas, pero son
  justo lo que se reescribió en el ataque a Trivy. Además, `setup-uv` ya no las
  publica.
- **Etiquetas exactas (`@v7.0.1`):** también se pueden mover, salvo en las
  releases inmutables, y no todas las Actions las usan.
- **`pnpm/setup` en lugar de `pnpm/action-setup`:** es el sucesor que recomienda
  pnpm e instala también Node, pero exige pnpm 11 o superior y el proyecto usa
  pnpm 10 (D-018). Se puede revisar si se sube de versión.

**Consecuencias.**
- Los SHA no se leen a simple vista; el comentario con la versión lo compensa y
  Dependabot lo mantiene al día.
- El fijado protege la Action que se referencia, no lo que esa Action descarga
  por su cuenta. `trivy-action` y `appleboy/ssh-action` son *composite* y usan
  otras Actions o binarios: en el ataque a Trivy, quien había fijado un commit de
  `trivy-action` anterior a abril de 2025 recibió igualmente un `setup-trivy`
  malicioso. Por eso conviene fijar también versiones recientes, que fijan sus
  propias dependencias.
- Todas las Actions corren ya en Node 24 (salvo las *composite*, que no usan
  Node).
- No se puede probar en local: `actionlint` valida la sintaxis y las
  expresiones de los workflows, pero los parámetros de cada Action se han
  comprobado leyendo su `action.yml`. La prueba real es el primer PR.
