# Plan de pruebas — síntesis

> Síntesis de `Plan de Pruebas - TFG Planificador de Viajes_1.docx` (metodología) y
> `Conjuntos de datos y verificación de hipótesis - TFG Planificador de Viajes.docx`
> (entradas concretas por hipótesis, no reproducidas aquí). El registro de
> ejecución vivo está en `Plan de Pruebas - Matriz y trazabilidad_1.xlsx`
> (11 hojas: Introducción, Resumen, Trazabilidad Req×CP, Trazabilidad RNF×CP,
> Navegadores y Dispositivos, NyD×CP, Otras pruebas, Casos de prueba, Hipótesis LLM,
> Métricas RNF ISO 25023, Quality gate SonarQube, Matriz Req-CU-CP).
>
> **Resumen cuantitativo**: 183 requisitos (65 RF + 118 RNF) · **192 casos de
> prueba** · **44 hipótesis** no deterministas · 8 casos CPDN (multi-dispositivo) ·
> 0 requisitos sin cubrir. Plantilla inspirada en MADEJA (Junta de Andalucía),
> ampliada con ISO/IEC/IEEE 29119-3 y SQuaRE (ISO/IEC 25010, 25023, 25040).
>
> **Divergencia con los documentos fuente (2026-10-05):** H-25 y H-26 se han
> revisado aquí porque nombran tipos de memoria de CrewAI 0.x que ya no existen
> (ver [«Memoria: terminología desfasada y comparativa»](#memoria-terminología-desfasada-y-comparativa-h-26)).
> El Excel y los dos `.docx` conservan todavía la redacción original.

## Filosofía: dos tipos de prueba

| | Casos deterministas | Hipótesis no deterministas |
|---|---|---|
| Qué prueban | Reglas, contratos, seguridad, persistencia, interfaz | Comprensión del LLM, composición, respeto de restricciones, juicio del revisor |
| Repeticiones | 1 ejecución basta | n casos × **3 repeticiones**, n calculado de antemano |
| Oráculo | Resultado esperado exacto | Guardrail determinista siempre que se pueda; juez LLM solo para criterio |
| Coste en tokens | Cero (LLM simulado — RNF-7.10) | Presupuestado: ≈ 2,9 millones de tokens en total (≈ 3,05 millones con la H-26 redefinida) |
| Resultado | Superado / no superado | Tasa con IC 95%, pass³, comparación con umbral |

Las pruebas son **hipotéticas**: descritas en prosa (entrada, pasos, resultado
esperado, responsable) **antes de implementar el sistema**. La columna "Estado" de
la matriz se rellena al ejecutarlas — a fecha de la síntesis, las 192 están
`Pendiente`.

## Niveles de prueba

| Nivel | Qué busca | Cuándo |
|---|---|---|
| Unitaria/componente | Pieza aislada: guardrail, hook, validación, componente React sin backend. `pytest` + `Vitest`, CI en cada push | Mientras se programa |
| Integración | Piezas juntas + BD + MCP simulados | Al cerrar cada módulo |
| Sistema | Recorridos completos con LLM real, medición de tiempos | Con la crew funcionando |
| Seguridad | Control de acceso, tokens, inyección, PII, OWASP | Al cerrar módulo y antes de entregar |
| Aceptación | Recorrido manual con frontend+backend+crew reales; CPDN automatizable después con Playwright | Frontend conectado al backend |
| Evaluación del LLM | Hipótesis H-01 a H-44 | ~2 semanas, según cuota |
| Rendimiento/carga/estrés | Tiempos, 5 usuarios concurrentes, punto de ruptura | Antes de entregar |
| Usabilidad | 5–8 voluntarios + SUS | Con prototipo estable |

## Entornos

| Entorno | Descripción | Uso |
|---|---|---|
| Local de desarrollo | Docker Compose: backend, frontend, PostgreSQL+pgvector, Langfuse, MCP simulados | Unitarias, integración, seguridad |
| CI | Pipeline en cada push: deterministas + cobertura + SonarQube | Regresión, quality gate |
| Evaluación | Igual que local + LLM real (Groq/Gemini) + respuestas MCP grabadas | Hipótesis no deterministas |
| Demo | Despliegue académico (OCI) | Aceptación, dispositivos, usabilidad, disponibilidad |

## Herramientas

`pytest` (backend/crew), `Vitest`+Testing Library (componentes), `Playwright`
(aceptación multi-navegador, opcional), `SonarQube`/`SonarCloud` (análisis
estático), `crewai test` (puntuación 1–10 por tarea), `Langfuse` (trazas, datasets,
veredictos automáticos), `Locust` (carga/estrés), `Lighthouse` (accesibilidad y
rendimiento web), `OWASP ZAP` + `pip-audit`/`npm audit` (seguridad).

## Modelo de calidad y medición

Los RNF ya están agrupados por las 9 características de **ISO/IEC 25010:2023**
(ver `docs/requisitos.md`). La medición sigue **ISO/IEC 25023**: cada RNF tiene una
métrica (directa o indirecta `X=A/B`), un valor objetivo, un método de medición y
una herramienta — el detalle campo a campo está en la hoja "Métricas RNF (ISO
25023)" del Excel.

### Quality gate de SonarQube

| Condición | Umbral nuevo código | Umbral global |
|---|---|---|
| Cobertura de líneas | ≥ 80% | ≥ 70% |
| Líneas duplicadas | ≤ 3% | ≤ 3% |
| Calificación mantenibilidad (deuda ≤5%) | A | A |
| Calificación fiabilidad | A | A |
| Calificación seguridad | A | A |
| Security hotspots revisados | 100% | 100% |
| Complejidad cognitiva/función | ≤ 15 | ≤ 15 |
| Complejidad ciclomática/función | ≤ 10 | ≤ 10 |
| Secretos en el código | 0 | 0 |

## Método estadístico para las hipótesis no deterministas

- **3 repeticiones por caso**: se informa la tasa global, `pass³` (pasa las 3) y el
  voto mayoritario. `pass³` se usa (no `pass@k`) porque el usuario solo recibe una
  respuesta real.
- **Respuestas MCP grabadas**: la única variable del experimento es el LLM.
- **Oráculos deterministas primero** (guardrails); el juez LLM solo puntúa criterio
  (pertinencia, tono) por los sesgos conocidos de los jueces LLM.
- **Regla del tres**: si en *n* ejecuciones independientes no hay fallos, la tasa
  real de fallo es ≤ 3/n con 95% de confianza (3 ≈ −ln(0,05)). Ejemplos: n=60 → <5%;
  n=144 → <2,1%; n=300 → <1%.
- **Intervalo de Wilson (95%)** cuando sí hay fallos observados.
- **Dos cotas por independencia**: cota por ejecución (3/ejecuciones totales) vs.
  cota prudente (3/casos distintos, para generalizar a mensajes nuevos) — la
  segunda es más conservadora y es la que se usa para conclusiones.
- **Pruebas por componente**: evaluar el Composer (T7) solo cuesta ~7 000
  tokens/muestra frente a ~25 000 del flujo completo; la potencia estadística se
  consigue por componente, el flujo completo (H-35) es solo confirmación.
- **Etiquetado humano previo**: el autor etiqueta los datasets antes de ejecutar
  ningún modelo (evita ajustar el criterio a lo que salga).

### Veredicto de cada ejecución

| Forma | Cómo | Hipótesis |
|---|---|---|
| Automática por código | Guardrail/comparación con etiqueta/canario | La mayoría (H-01–18, H-20–31, H-35, H-36, H-40–44) |
| Automática con juez LLM | Evaluador con rúbrica fija | H-19, H-32, H-33, H-34 |
| Manual | Revisión en cola de anotación de Langfuse | 10% de lo que puntúa el juez, 100% de emergencias (H-29), etiquetas de H-33 |

## Catálogo de hipótesis (H-01 a H-44) — resumen

Detalle completo (variable, muestra, oráculo, criterio, requisitos) en la hoja
"Hipótesis LLM" del Excel; datasets concretos en el documento complementario
`Conjuntos de datos y verificación de hipótesis.docx`. Agrupación temática:

- **Router e intención** — H-01 (exactitud ≥95%), H-02 (no relanza crew completa
  por ediciones pequeñas), H-03 (pregunta ante ambigüedad, 0 mutaciones).
- **Extracción del briefing (T1)** — H-04 (exactitud por campo ≥90%), H-05 (no
  inventa parámetros obligatorios que faltan).
- **Esquema y anclaje del Composer (T7)** — H-06 (validez Pydantic ≥90%
  primer intento), H-07..H-11 (anclaje de vuelos/hoteles/lugares/traslados/clima —
  todas exigen **0 no anclados en lo entregado**), H-12 (huecos declarados, no
  inventados, 36/36).
- **Restricciones duras** — H-13 (dieta, 0 violaciones), H-14 (movilidad, 0
  violaciones), H-15 (presupuesto, 0 superaciones sin explicar), H-16 (clima como
  filtro de exteriores), H-17 (ritmo dentro de rango), H-18 (horarios coherentes,
  0 conflictos).
- **Calidad del itinerario** — H-19 (interés del usuario, juez ≥8/10), H-20
  (variedad sin repeticiones), H-42 (desviaciones explicadas).
- **Refinamiento conversacional** — H-21 (cambio de hotel sin efectos colaterales,
  60/60), H-22 (cambio de vuelo con impacto en cascada, 0 conflictos), H-23 (CRUD
  por chat ≥95% exactas), H-24 (contexto visual/deíctico, 60/60).
- **Memoria** — H-25 (referencias a turnos anteriores de la misma sesión ≥90%; su
  componente original, la *short-term memory* de CrewAI, está **desfasado**), H-26
  (**redefinida**: la original, «memoria de entidad ≥85%», está **desfasada por
  cambio de tecnología**; ahora compara ReMAP + pgvector con la memoria unificada de
  CrewAI, ver más abajo), H-27 (extracción de preferencias implícitas,
  P≥0,85/R≥0,75), H-28 (clasificación de criticidad hard/soft, 0 críticas mal
  clasificadas).
- **Seguridad** — H-29 (emergencias médicas: redirige, no diagnostica, 75/75), H-30
  (resistencia a prompt injection: 0/30 ataques conocidos, ≤5% evasivos), H-31 (0
  PII sin redactar llega al LLM).
- **Calidad del juez (T8)** — H-32 (idioma/tono ≥98% español), H-33 (el juez
  detecta defectos sembrados, recall≥0,90, κ≥0,6), H-34 (el juez es estable entre
  repeticiones, ≥90% veredicto unánime).
- **Consistencia y rendimiento** — H-35 (flujo completo pass³ en 11 escenarios
  V01–V11), H-36 (tokens dentro de cuota: ≤30 000 base, ≤6 000 edición), H-43
  (p95 generación ≤120 s), H-44 (p95 TTFT chat <3 s).
- **Comparativas A/B** — H-37 (reflexión mejora calidad), H-38 (planning previo
  mejora aprobación en 1ª ronda), H-39 (temperatura baja reduce variabilidad), H-40
  (cambio de proveedor LLM mantiene ≥10/11 escenarios). H-26 también es una
  comparativa (memoria propia frente a la de CrewAI).
- **Procedencia** — H-41 (datos scraped/estimados bien etiquetados, 0 mal
  etiquetados).

## Memoria: terminología desfasada y comparativa (H-26)

### Desfasado por cambio de tecnología

Los documentos fuente se escribieron sobre CrewAI 0.x, que tenía tres memorias: a
corto plazo (`short_term`), a largo plazo (`long_term`) y de entidad (`entity`),
además de una externa. **CrewAI 1.x las sustituyó por una memoria unificada**
(`Memory`, sobre LanceDB). En la versión fijada (1.15.23, D-016) esos tipos y sus
parámetros ya no existen (D-035; `arquitectura-multiagente-crewai.md` §5). Por eso
queda desfasado todo lo que se apoya en ellos:

| Dónde | Qué dice | Situación |
|---|---|---|
| RNF-1.08, RNF-2.17 | Memoria a corto plazo | **Desfasado el componente.** El contexto de la sesión lo dan la ventana de `chat_messages` (RNF-2.06) y el estado del Flow (§10 de la arquitectura) |
| RNF-1.09 | Memoria a largo plazo | **Desfasado.** Lo que se recuerda del usuario entre viajes va en pgvector (ReMAP). La memoria persistente de CrewAI queda solo para evaluación (§5) |
| RNF-1.10 | Memoria de entidad | **Desfasado.** Las personas, cadenas o aerolíneas del usuario son hechos de ReMAP en pgvector |
| H-25 | Componente *Short-term memory* | **Desfasado el componente**; la hipótesis se mantiene (ver abajo) |
| H-26 | «Memoria de entidad ≥ 85 %», componente *Entity memory* | **Desfasada**; se redefine como comparativa (ver abajo) |
| CP-05.01-03 | «Memoria de entidad» | **Desfasado el nombre**; prueba lo mismo que H-26 |

También están desfasados los RF de la numeración antigua de `Requisitos.docx` que
nombran esas memorias (RF-02.25 a RF-02.27, y la memoria a corto plazo, de entidad
y a largo plazo del módulo 5). "Largo plazo" como idea general **no** lo está: la
consolidación de ReMAP (CU-05.02) o la memoria a largo plazo del estado del arte
siguen valiendo, porque no se refieren a los tipos de CrewAI.

**H-25 se mantiene.** Cada mensaje del chat es una ejecución distinta del Flow, y la
memoria de CrewAI de una ejecución no sobrevive a la siguiente (§5). Las referencias
a turnos anteriores ("el segundo", "ese hotel") las resuelven la ventana de
`chat_messages` y el estado del Flow. Solo cambia la etiqueta del componente.

### H-26 redefinida: ¿qué recuerda mejor al usuario?

**Pregunta:** con los mismos datos, ¿es más eficaz la capa propia (ReMAP + pgvector)
o la memoria de CrewAI activada? Se mide la eficacia, pero también el aislamiento,
el coste y la latencia: una memoria que recuerda algo más pero mezcla usuarios o
agota la cuota gratuita no sirve.

| | A — ReMAP + pgvector | B — Memoria de CrewAI activada |
|---|---|---|
| Al guardar | ReMAP extrae los hechos, los clasifica (*hard*/*soft*) y los guarda en `hard_facts`/`soft_facts` con su `user_id` | La crew extrae recuerdos de cada tarea y los guarda sola. Un LLM infiere ámbito, categorías e importancia, y consolida con lo que ya hay |
| Al recuperar | Top-K por similitud, filtrado por `user_id` en SQL, inyectado como contexto | `recall` automático antes de cada tarea, con `root_scope=/user/{id}`, `source=user:{id}` y `private=True` |
| Aislamiento | Físico: la consulta SQL solo ve las filas del usuario | Lógico: ámbito y `source` dentro del mismo almacén |
| Almacén | PostgreSQL + pgvector | Qdrant Edge persistente, pasado como instancia: `QdrantEdgeStorage(path=…)` (entorno de evaluación; D-036) |
| Crews | `memory=False` | `memory=Memory(...)` con el ámbito del usuario |

**Lo que no cambia entre A y B:**
- El modelo y su versión, la temperatura, los prompts y las respuestas MCP grabadas.
- El mismo modelo de *embeddings* y el mismo historial de relleno.
- **Solo cambia la memoria.**

**Dos detalles técnicos** para que la comparación sea limpia:
- **En A se desactiva la memoria automática del Flow** (`_skip_auto_memory = True`).
  Si no, todo `Flow` crea su propia `Memory` (comprobado en 1.15.23; con D-036, en un
  Qdrant Edge propio de la ejecución), y A dejaría de ser "sin memoria de CrewAI".
- **En B, la memoria usa el LLM del proyecto**, no el que trae por defecto
  (`gpt-5.4-mini`).

**Datos:** las 20 conversaciones EN01–EN20 de la Tabla 20 del documento de conjuntos
de datos, en dos variantes:
1. **Misma sesión, fuera de la ventana.** Entre la mención y la referencia se
   intercalan al menos 10 intercambios de relleno, ya escritos. Si la referencia cae
   dentro de la ventana de 5–10 intercambios (RNF-2.06), la resuelve el historial y
   no se estaría midiendo la memoria.
2. **Otra sesión.** La mención se hace en un viaje y la referencia en otro nuevo.
   Solo con los casos que el autor etiquete como **duraderos** antes de ejecutar. Por
   ejemplo, EN03 (Iberia) o EN09 (alergia) sí lo son; EN04 («nos alojamos en el
   Alfama Suites») no.

**Control de aislamiento:** un segundo usuario, sin esos hechos, envía el mismo
mensaje de referencia. Cualquier uso de los hechos del primero cuenta como fuga.

**Muestra:**
- Variante 1: 20 casos × 2 configuraciones × 3 = 120 ejecuciones.
- Variante 2: d casos duraderos × 2 × 3 = 6d.
- Control de aislamiento: 20 × 2 × 3 = 120.

| Variable | Cómo se mide | Criterio |
|---|---|---|
| Eficacia | Asociaciones correctas / total, por configuración y variante. Oráculo: la asociación esperada de la Tabla 20, anotada antes de ejecutar | A ≥ 0,85 (el umbral original de H-26) |
| Diferencia de eficacia | McNemar sobre los pares discordantes (mismo caso en A y en B), como en H-38 | B solo se adopta si mejora ≥ 10 pp con p < 0,05 |
| Restricciones críticas | Olvidos en los casos de salud o movilidad (EN02, EN05, EN09, EN11) | 0 en la configuración elegida |
| Aislamiento | Fugas en el control | 0 (60 ejecuciones por configuración sin fugas → ≤ 5 %, regla del tres) |
| Coste | Tokens y llamadas de LLM por conversación, **incluidas las de la propia memoria** (mediana y p95), con Wilcoxon pareado | Dentro de H-36 |
| Latencia | p95 del turno de referencia y tiempo de recuperación de la memoria | Recuperación < 500 ms (RNF-2.03) |

**Sobre la estadística:**
- Como en el resto del plan, la conclusión se saca con el **voto mayoritario por
  caso** (pares independientes). La cuenta por ejecución se informa aparte.
- Con 20 casos, McNemar solo detecta diferencias grandes. Un resultado no
  significativo no demuestra que A y B sean iguales. Aun así basta para la regla de
  decisión, porque es B quien tiene que demostrar su mejora.

**Regla de decisión** (fijada antes de ejecutar):
- **B se adopta solo si cumple todo** lo siguiente:
  - mejora la eficacia ≥ 10 pp con p < 0,05;
  - 0 fugas;
  - 0 olvidos críticos;
  - se mantiene dentro de H-36 y H-43.

  Es la misma regla que H-38: una pieza que gasta tokens tiene que ganarse su sitio.
- **Si no, se queda A**, y las crews van con `memory=False`. La tabla de §5 de la
  arquitectura describe hoy una memoria por ejecución, así que en ese caso habría
  que actualizarla.
- **Si A no llega a 0,85**, es un defecto de ReMAP, gane quien gane, y se registra
  como incidencia.
- **Si cada una gana en una variante**, se documenta y se estudia un híbrido. Por
  ejemplo, usar `extract_memories()` de CrewAI dentro de la extracción de ReMAP.

**Ficha:**
- **Requisitos:** RNF-1.10 (desfasado), RF-05.01 a RF-05.05, RNF-6.3, RNF-2.03,
  RNF-2.04 y RNF-2.06.
- **Casos de uso:** CU-05.01 y CU-05.03.
- **Coste:** ≈ 200 000 tokens. Es una estimación (dos configuraciones, la variante
  entre sesiones y el control) que se revisará tras un piloto de 2–3 casos. Añade
  ≈ 150 000 al presupuesto total.
- **Prioridad:** Media. La original era Baja; sube porque decide la memoria de
  producción.
- **Responsable:** Autor (probador).

## Escenarios de validación V01–V12 (usados en H-35, H-40, H-43)

| ID | Escenario | Qué comprueba |
|---|---|---|
| V01 | Fin de semana en Lisboa, pareja, 1.500€ | Camino feliz |
| V02 | Valencia, familia con bebé y silla de ruedas | Accesibilidad como filtro duro |
| V03 | Roma, viajero celíaco, 5 días | Dieta estricta |
| V04 | París, 350€ / 3 días | Presupuesto muy ajustado |
| V05 | Oporto con lluvia el día 2 | Clima como regla de decisión |
| V06 | Londres, ritmo intensivo | Ritmo y traslados reales |
| V07 | Atenas fuera del horizonte de previsión | Degradación honesta (confidence=low) |
| V08 | MCP de vuelos caído | Resiliencia: hueco declarado, resto entregado |
| V09 | Refinamiento ambiguo sobre V01 | Pregunta aclaratoria, ningún cambio |
| V10 | Inyección de prompt sobre V01 | Rechazo antes de la crew, registrado |
| V11 | Sevilla, MCP de mapas sin horarios | Lector web de respaldo, source=scraped |
| V12 | Dos ediciones concurrentes del mismo elemento | Bloqueo optimista (determinista, CP-03.01-11) |

## Dispositivos y navegadores (matriz CPDN)

5 dispositivos × 5 navegadores, 8 flujos críticos probados en todas las combinaciones:

- **Dispositivos**: PC Windows 11 (1920×1080), portátil macOS (1440×900), tablet
  Android 10" (800×1280), móvil Android Pixel 7 (412×915), iPhone 13 (390×844).
- **Navegadores**: Chrome, Firefox, Edge, Safari, Chrome Android.
- **Flujos CPDN-01..08**: registro/login, onboarding completo, generación con
  espera interactiva, chat con streaming, línea de tiempo + drag&drop, mapa
  sincronizado, deshacer/rehacer, cierre de sesión.

## Criterios de entrada / salida / suspensión

| Criterio | Condición |
|---|---|
| Entrada | Requisitos estables; Docker funcionando; simuladores y grabaciones listos; datasets etiquetados |
| Superación de un caso determinista | Resultado observado coincide en todos sus puntos |
| Superación de una hipótesis | Se cumple el criterio de aceptación de su ficha, con la muestra completa |
| **Salida** | 100% prioridad Alta superados · ≥90% Media · 0 defectos críticos/graves abiertos · quality gate en verde · hipótesis Alta aceptadas · SUS ≥68 |
| Suspensión | Defecto bloqueante en un módulo; cuota diaria de tokens agotada; cambia un contrato de datos |
| Reanudación | Defecto corregido + regresión superada; cuota renovada al día siguiente; contratos regenerados |

## Gestión de incidencias

Severidades: **Crítica** (riesgo/fuga de datos, p. ej. restaurante con alérgeno del
usuario) · **Grave** (funcionalidad principal rota) · **Media** (funciona con
rodeo) · **Leve** (estético). Plantilla: ID (`INC-NNN`), caso/hipótesis, entorno,
requisitos afectados, pasos, esperado/observado, causa, severidad/prioridad, traza
o captura, estado.

## Registro de evidencias

| Tipo de prueba | Evidencia |
|---|---|
| Unitarias/integración | Informe pytest/Vitest de CI |
| Calidad de código | Captura del quality gate de SonarQube |
| Aceptación/CPDN | Captura o GIF, nombrado con el ID del caso |
| Con intervención de la crew | + ID de traza de Langfuse |
| Hipótesis del LLM | Enlace al dataset en Langfuse + CSV exportado + 2–3 trazas de ejemplo |
| Carga/rendimiento | Informe HTML de Locust/Lighthouse |
| Seguridad | Captura de respuesta denegada (403/401/429) o informe OWASP ZAP |
| Usabilidad | Hoja de observación anónima + cuestionario SUS |

## Riesgos principales

Agotar la cuota gratuita de LLM (mitigación: orden por prioridad, pruebas por
componente, respuestas MCP grabadas, repartir entre Groq/Gemini) · cambio/retirada
de modelo por el proveedor · pocos voluntarios de usabilidad (mínimo 5) · sesgo del
juez LLM (mitigación: defectos sembrados + revisión manual del 10%) · sobreajuste
de prompts al conjunto de prueba (mitigación: 20% del dataset del router reservado,
no se mira al ajustar) · falta de tiempo.

## Prueba de usabilidad (Anexo D)

6 tareas cronometradas (registro+login ≤2min, planificar viaje ≤4min, cambiar hotel
por chat ≤2min, mover actividad por drag&drop ≤1min, deshacer ≤30s, encontrar coste
y procedencia del precio ≤1min) + cuestionario **SUS** (10 ítems, objetivo media
≥68, referencia de Sauro). 5–8 voluntarios ajenos al proyecto, pensando en voz alta.

## Referencias
- `Plan de Pruebas - TFG Planificador de Viajes_1.docx` — documento fuente completo
  (16 capítulos + 4 anexos).
- `Plan de Pruebas - Matriz y trazabilidad_1.xlsx` — registro de ejecución vivo,
  trazabilidad completa RF/RNF × CP y matriz Req-CU-CP.
- `Conjuntos de datos y verificación de hipótesis - TFG Planificador de Viajes.docx`
  — entradas concretas, etiquetadas a mano, para cada una de las 44 hipótesis.
- `docs/arquitectura-multiagente-crewai.md` §12 — evaluación con `crewai
  test`/`train` y Langfuse, en el contexto de la arquitectura.
