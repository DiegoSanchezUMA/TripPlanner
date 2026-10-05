# Arquitectura del sistema multiagente (CrewAI) — fuente de verdad

> Síntesis de `Diseno sistema multiagente CrewAI - TFG v2.docx` (2025-09-23, fuente
> primaria con detalle de implementación) y `Diseno sistema multiagente - Sintesis
> para tutor.docx` (versión corta para el tutor). Generado automáticamente a partir
> de los documentos de la memoria para que quede disponible como contexto de trabajo
> en el repositorio. **Antes de cambiar este documento, pregunta**: es la fuente de
> verdad de la memoria del TFG (ver `CLAUDE.md`).
>
> Diagramas UML relacionados: `docs/uml/componentes/Component Diagram.jpg`,
> `docs/uml/despliegue/Deployment Diagram.jpg`,
> `docs/uml/secuencia/Creación de Itinerario de Viaje.jpg`,
> `docs/uml/secuencia/Modificación de itinerario de viaje.jpg`,
> `docs/uml/casos-de-uso/Motor de IA y Herramientas (Integración MCP) Use Case Diagram.jpg`.
> (`...- mal.jpg` es un borrador incorrecto, ignorar.)

## 0. Idea central

El sistema **no es una crew permanente**. El punto de entrada es un **Flow de CrewAI**
que resuelve la mayoría de interacciones **sin instanciar ningún agente** (modelo de
*agencia por adhesión* / *opt-in agency*): se sube un peldaño de autonomía —una
llamada al modelo, un agente, una crew completa— solo cuando el peldaño anterior se
queda corto.

- «¿El hotel del día 2 tiene desayuno?» → una lectura de estado, ~600 tokens, ~1 s.
- «Cámbiame el vuelo de vuelta» → `RefinementCrew` con 3 agentes, ~5 000 tokens, 8–20 s.
- Generar el itinerario completo → `PlanningCrew` con 8 agentes y 8 tareas, ~25 000
  tokens, 60–110 s.

Tres capas por encima de un catálogo de agentes:

| Capa | Responsabilidad | Naturaleza |
|---|---|---|
| 0 · Catálogo | Definición única de los 8 agentes | Configuración (YAML) |
| 1 · Decisión | El Flow (`@router classify_intent`) clasifica la intención y elige la rama. Aquí y solo aquí se decide | Código + 1 llamada LLM barata |
| 2 · Composición | Selecciona agentes y tareas del catálogo para montar la crew adecuada | Código puro |
| 3 · Ejecución | La crew recorre su grafo de tareas de forma secuencial. No elige nada | Agentes LLM |

## 1. Los ocho agentes

Un agente por servidor MCP (correspondencia 1:1 con los actores del diagrama de
casos de uso del módulo 4), más planificador, compositor y revisor. **No siete, no
nueve: exactamente ocho.**

> **Cambio pendiente de desarrollar (D-020, 2026-10-04).** El antiguo *Places &
> Routes Specialist* (Google Maps Platform MCP) se divide en **Places Specialist**
> (Geoapify MCP) y **Routes Specialist** (Transitous MCP). Motivo: con facturación
> en el EEE, los términos de Google Maps Platform no permiten usar el contenido de
> Places API (nombres, horarios, accesibilidad) en un planificador de viajes, ni
> guardarlo. Al ser dos servidores MCP distintos, la regla "un agente por servidor
> MCP" obliga a dos agentes. Detalle en `docs/decisiones/decisiones.md` (D-020).

| Agente | Rol (`Role`) | Responsabilidad | Herramientas | Modelo / temp | Requisitos |
|---|---|---|---|---|---|
| **Travel Planner** | Senior Trip Scoping Analyst | Convierte el briefing + hard facts en un esqueleto día a día (T1). **No elige lugares, vuelos ni precios.** No ensambla el itinerario final. | Ninguna | Medio, reasoning activo (máx. 3 intentos) · temp 0.2 | RNF-5.10, RF-02.x |
| **Flight Specialist** | Air Travel Logistics Specialist | Vuelos ida/vuelta reales, precios, horarios, escalas | Flight MCP (`@mcp/octotrip`) — sin lector web | Medio · temp 0.1 | RF-04.01–04.03 |
| **Hotel Specialist** | Accommodation Availability Specialist | Alojamiento con disponibilidad confirmada y coordenadas | Hotel MCP (`@mcp/winwin-travel`) — sin lector web | Medio · temp 0.1 | RF-04.04–04.06 |
| **Places Specialist** | Destination Curator | Puntos de interés, horarios de apertura, accesibilidad y coordenadas (datos de OpenStreetMap). Único agente con lector web (acotado) | Places MCP (Geoapify, solo herramientas de lugares y geocodificación) + `bounded_web_reader` | Medio · temp 0.1 | RF-04.07–04.09 |
| **Routes Specialist** | Urban Mobility Analyst | Tiempos de desplazamiento a pie y en transporte público entre puntos consecutivos, con la línea concreta | Routes MCP (Transitous) — sin lector web | Pequeño/medio · temp 0.0 | RF-04.10–04.11 |
| **Weather Specialist** | Destination Weather Analyst | Clasifica cada día como interior/exterior con confianza | Weather MCP | Pequeño/medio · temp 0.0 | RF-04.12–04.13 |
| **Itinerary Composer** | Itinerary Composer | Ensambla el itinerario final (T7); aplica los parches del refinamiento (R1, R3) | Ninguna | Grande, contexto largo · temp 0.3 | RNF-2.04 |
| **Itinerary Reviewer** | Itinerary Feasibility Auditor | Audita viabilidad con rúbrica LLM-as-a-Judge (T8). **Nunca reescribe.** | `schedule_validator` + `tool_call_ledger_reader` (solo lectura) | Grande, **familia de modelo distinta** a la del Composer · temp 0.0, reasoning (máx. 2) | RNF-6.18, RNF-7.12 |

**Por qué esta granularidad:**
1. Especialistas > generalistas: prompt más corto, menos superficie de alucinación.
2. Aislamiento de herramientas *por construcción* (RNF-1.07, RNF-6.16): el agente de
   vuelos físicamente no tiene el cliente MCP de clima inyectado.
3. Correspondencia 1:1 con el UML: el diseño es la traducción literal del análisis.

**Por qué el planificador no ensambla el itinerario** (decisión más defendible del
diseño): T1 es trabajo divergente (estructurar sin datos), T7 es convergente
(seleccionar, encajar horarios, cuadrar presupuesto). Separarlos permite: asignar
modelo barato a T1 y modelo caro solo a T7 (ahorro real); y evitar el **sesgo de
anclaje** (quien escribe el plan tiende a defenderlo en vez de replantear cuando los
datos no encajan) — mismo motivo por el que el revisor usa una familia de modelo
distinta al compositor. Precedente del curso DeepLearning.AI/CrewAI: Deep Research
Crew separa *Research Planner* y *Report Writer*.

Regla general: **no es "una tarea, un agente" sino "un agente por competencia"**, y la
competencia la marca el servidor MCP. T5 (seleccionar actividades) y T6 (calcular
traslados) eran del mismo agente mientras compartían servidor (Google Maps); desde
D-020 usan servidores distintos (Geoapify y Transitous), así que son de agentes
distintos. Lo que no cambia: la atomicidad vive en la capa de tareas, y un agente
nunca tiene dos servidores MCP.

`allow_delegation = false` en los 8. Ningún agente delega en otro; la coordinación
pasa por el `context` de las tareas, nunca por delegación libre (fuente habitual de
bucles infinitos).

## 2. Proceso: secuencial + async, no jerárquico

La memoria describe la topología como "jerárquica con un único planificador" — es
correcto **conceptualmente**, pero **no se implementa con `Process.hierarchical`**:
ese modo crea un agente gestor implícito cuyo prompt no se controla, añade una
llamada LLM por delegación y hace la ejecución no determinista (choca con RNF-7.11,
que exige validar cambios de prompt con puntuaciones repetibles).

Implementación real: **`Process.sequential`** con `async_execution=True` en T2, T3 y
T4 (las tres búsquedas independientes: vuelos, hoteles, clima), y el resto de
dependencias expresadas con `context`. La jerarquía existe, pero está codificada en
un grafo auditable, no en la improvisación de un gestor.

## 3. Las ocho tareas de la `PlanningCrew`

| Tarea | Agente | Produce | Depende de | Async |
|---|---|---|---|---|
| **T1** `decompose_brief` | Travel Planner | `TripSkeleton`: días, slots según ritmo (relajado=2, moderado=3, intensivo=4+noche), % presupuesto por día, restricciones duras, *rationale* por día, *deviation_policy* | — | no |
| **T2** `search_flights` | Flight Specialist | `FlightOptions`: 3–5 opciones reales o `gap` | T1 | **sí** |
| **T3** `search_hotels` | Hotel Specialist | `HotelOptions`: 3–5 propiedades con coordenadas | T1 | **sí** |
| **T4** `forecast_weather` | Weather Specialist | `WeatherWindow`: 1 entrada/día, recomendación + confianza | T1 | **sí** |
| **T5** `curate_activities` | Places Specialist | `ActivityPool`: 2–3 candidatos por slot, anclados al hotel | T1, T3, T4 | no |
| **T6** `compute_transfers` | Routes Specialist | `TransferMatrix`: tiempo, medio de transporte y línea entre pares consecutivos | T5 | no |
| **T7** `assemble_itinerary` | Itinerary Composer | `Itinerary` completo: horarios, traslados, desglose de coste, `gaps[]`, `deviations[]` | T1–T6 | no |
| **T8** `audit_itinerary` | Itinerary Reviewer | `ReviewVerdict`: aprobado/rechazado + 5 puntuaciones + defectos concretos | T7 | no |

Detalles de diseño que importan:
- **Orden de relajación de filtros fijado en la tarea, no al criterio del agente**:
  en vuelos, aerolínea preferida → directo → clase de cabina (nunca las fechas: "un
  vuelo en otras fechas no es una alternativa, es otro viaje").
- **T5 filtra en orden numerado, no puntúa globalmente**: (1) descarta lo que viola
  una restricción dura (dieta/accesibilidad) → (2) solo interior si el día es
  `indoor_only` → (3) empareja con intereses → (4) horarios que cubren el slot. Si se
  deja al criterio del modelo, un restaurante bien valorado "compensa" no ser apto
  para celíacos.
- **T7 enumera sus propias verificaciones** aunque las repita un guardrail: el
  guardrail es la red, la instrucción en la descripción ahorra el reintento.
- Campo `assumptions[]` en el itinerario (RNF-1.04, RNF-4.14): toda estimación se
  declara, nunca se presenta como dato verificado.

### RefinementCrew (refinamiento conversacional — la rama frecuente)

Un usuario refina un itinerario muchas más veces de las que lo genera: aquí se
decide si el sistema es económicamente viable. Se ensambla en tiempo de ejecución
con 3 o 4 agentes: **Composer + especialista según intención + Routes Specialist
(solo si el cambio mueve ubicaciones) + Reviewer**. El Travel Planner **no
participa** (el esqueleto ya existe).

| Intención | Especialista de R2 | ¿R2b (Routes)? |
|---|---|---|
| `modify_transport` | Flight Specialist | No |
| `modify_lodging` | Hotel Specialist | Sí: cambian los traslados desde y hacia el hotel |
| `modify_activities` | Places Specialist | Sí |
| `reschedule` | Places Specialist (horarios para la nueva franja) | Sí, si cambia el orden de las visitas |

| Tarea | Agente | Qué hace | Salida |
|---|---|---|---|
| **R1** `interpret_change` | Composer | Identifica qué ítems afecta el mensaje y qué se pide; si es ambiguo devuelve `needs_clarification` con la pregunta. No cambia nada. | `ChangeRequest` |
| **R2** `requery_<dominio>` | Especialista seleccionado | Alternativas solo para los ítems afectados, respetando restricciones originales + nuevas | `OptionSet` |
| **R2b** `requery_transfers` | Routes Specialist | Solo cuando el cambio altera la ubicación o el orden de algún ítem: traslados de los pares afectados | `TransferMatrix` |
| **R3** `patch_itinerary` | Composer | Aplica el parche elegido; integra los traslados de R2b y recalcula el coste solo del día afectado y vecinos | `ItineraryPatch` |
| **R4** `audit_patch` | Reviewer | Misma rúbrica que T8, pero solo sobre los días tocados | `ReviewVerdict` |

La salida es un **parche, no un itinerario completo**: regenerar todo costaría igual
que la generación inicial, alteraría partes ya aceptadas por el usuario y rompería
`RNF-5.2` (estabilidad del estado compartido). El parche es también la unidad que se
persiste en el historial de revisiones (§7).

## 4. Reparto de modelos por agente

| Componente | Perfil | Temp | Motivo |
|---|---|---|---|
| `@router classify_intent` | pequeño/rápido (Groq 8B) | 0.0 | Camino crítico de toda interacción; clasificar, no razonar |
| Especialistas (vuelos, hotel, lugares, clima, rutas) | medio (Gemini Flash / GPT-mini) | 0.1 | Invocan herramientas y estructuran; creatividad = defecto aquí |
| Travel Planner | medio, reasoning | 0.2 | Entrada pequeña; no necesita contexto largo |
| Itinerary Composer | grande, contexto largo (Gemini Pro / GPT-4) | 0.3 | Único que ve las 6 salidas heterogéneas a la vez |
| Itinerary Reviewer | grande, **otra familia** que el Composer | 0.0 | Un juez del mismo modelo comparte los puntos ciegos del autor |
| `extract_soft_facts` | pequeño | 0.0 | Fuera del camino crítico, en segundo plano |

Cambiar de proveedor es cambiar una variable de entorno (RNF-8.1, RNF-7.8).
Proveedores previstos: **Groq** (inferencia rápida), **Google AI/Gemini**
(razonamiento, contexto largo), **Azure OpenAI** (funciones de CrewAI que solo
soportan API de OpenAI).

## 5. Memoria y conocimiento — el punto más delicado del diseño

**Hecho documentado, no una suposición**: la memoria nativa de CrewAI **no aísla por
usuario**. En las versiones 0.x (memorias `short_term`, `long_term` y `entity`), el
foro oficial del proyecto lo confirmaba explícitamente ("there is no isolation per
user for the CrewAI memory types"), y la memoria a largo plazo usaba SQLite, que da
errores de bloqueo con ejecuciones concurrentes, alcanzables con los 5 usuarios
simultáneos del RNF-2.07.

**En CrewAI 1.15.23, la versión fijada (D-016), la memoria cambió.** Comprobado en
su código fuente y en el contenedor el 2026-10-05 (D-035):

- **Ya no hay tres memorias, sino una memoria unificada**, `Memory`, sobre LanceDB.
  `Crew(memory=...)` acepta `True` o una instancia de `Memory`, `MemoryScope` o
  `MemorySlice`. Los parámetros `short_term_memory`, `long_term_memory` y
  `entity_memory` ya no existen.
- **`MemoryScope` es una vista restringida a una ruta** (`root_scope`, p. ej.
  `/user/42`). Aísla de forma **lógica**, dentro del mismo almacén y con la ruta
  que elija la aplicación. Es un particionado por convención, no un aislamiento
  multiinquilino garantizado. La conclusión de arriba se mantiene.
- **Cada recuerdo guardado pasa por un LLM**, que infiere su ámbito, categorías e
  importancia. Por defecto es `gpt-5.4-mini`, y los *embeddings* también son de
  OpenAI por defecto. Hay que configurar `llm` y `embedder` con los proveedores del
  proyecto (§4), o fallaría por falta de clave. Además, cada tarea gasta llamadas
  de LLM extra a cargo de la cuota gratuita.
- **`CREWAI_STORAGE_DIR` es una variable de entorno de todo el proceso.** El
  backend atiende a varios usuarios a la vez en un único proceso (D-011), así que
  cambiarla en cada ejecución sería una condición de carrera. La ruta de cada
  ejecución se pasa de forma explícita: `Memory(storage="<ruta>")`.
- **Cada `Crew` escribe sus salidas en un SQLite común**
  (`latest_kickoff_task_outputs.db`, para `crewai replay`), con independencia de
  la memoria. Se vacía en cada `kickoff` y se escribe después de cada tarea, y no
  hay opción para desactivarlo. Con dos generaciones a la vez, una borraría las
  salidas de la otra y competirían por el bloqueo de SQLite. Hay que neutralizarlo
  en cada crew; queda pendiente de implementar y de verificar.
- **En el contenedor, el único sitio escribible es `/tmp`**, en memoria, y
  `CREWAI_STORAGE_DIR=/tmp/crewai` (D-035).

| Función | Solución adoptada (CrewAI 1.15.23) | Justificación |
|---|---|---|
| Memoria de la crew durante una generación (la antigua `short_term`) | `memory=Memory(storage=<directorio temporal propio de la ejecución>, llm=…, embedder=…)`. El directorio va en `/tmp`, en memoria, y se borra al terminar | Contexto compartido entre las tareas de una generación, que nunca sobrevive para mezclarse con otro usuario (RNF-2.17, RNF-1.08). La ruta se pasa de forma explícita, no con `CREWAI_STORAGE_DIR` |
| Memoria persistente entre ejecuciones (la antigua `long_term`) | **Solo en el entorno de evaluación** (`crewai train` / `crewai test`), con un almacén persistente. **Nunca en producción** | El único usuario es el autor, así que no hay problema de aislamiento |
| Entidades (la antigua `entity`) | **No se usa** | La sustituye pgvector: las entidades recurrentes son hechos del usuario y ya tienen sitio en `hard_facts` |
| `knowledge` | pgvector con los *hard facts* del usuario, filtrados por `user_id` en SQL | Es el aislamiento que exige RNF-6.3 y que el framework no ofrece |
| Salidas de tareas para `crewai replay` | **No se usan en producción**: hay que neutralizar el SQLite común en cada crew (pendiente de verificar al implementar) | Lo comparten todas las ejecuciones del proceso |

**Regla de alcance de la capa vectorial** (la más importante de este apartado):
**pgvector almacena quién es el usuario, no qué hay en el mundo.** Precios,
horarios, disponibilidad y clima se consultan siempre en vivo por MCP. Un corpus
turístico estático tendría el mismo defecto de obsolescencia que se le reprocha al
conocimiento paramétrico del LLM. Con esta regla, **ReMAP** (extracción/consolidación
de hard/soft facts, capítulo 2 de la memoria) pasa a ser la única razón de existir de
la capa vectorial.

Cómo defenderlo ante tribunal: *"La memoria a largo plazo la implementa el sistema en
PostgreSQL con pgvector y aislamiento multiinquilino por SQL, porque el almacén
nativo del framework no ofrece aislamiento por usuario: como mucho, vistas por ámbito
dentro de un mismo almacén, que dependen de que la aplicación pase la ruta
correcta"* es una decisión de arquitectura argumentada; *"activamos la memoria
porque el framework la tiene"* no lo es.

## 6. Raspado web acotado por dominio

El raspado (`bounded_web_reader`) **no es una excepción al control**: es una
herramienta más, con dominios permitidos y tope de peticiones, que registra sus
llamadas en el `tool_ledger` como cualquier cliente MCP. Solo la tiene el **Places
Specialist**.

| Dominio | ¿Raspado? | Razón |
|---|---|---|
| Horarios y datos de lugares | **Sí** | Verificable in situ, cambia poco; un error cuesta una visita mal planificada, no dinero |
| Información general de lugares/eventos | **Sí** | Es contexto, no compromiso |
| Vuelos | **No** | Precio volátil, transaccional, prohibido por ToS de aerolíneas |
| Alojamiento | **No** | Mismo argumento que vuelos |
| Clima | **No** | Fuera de horizonte → `confidence: low` declarado; raspar no da nada más fiable |

Todo lo recuperado por raspado sale marcado `source: scraped`, `confidence: low`, y
la interfaz lo señala con un distintivo. Nunca se usa para precios ni disponibilidad.

## 7. Mecanismos de control

### 7.1 Guardrails deterministas (código) — capítulo 6 de v2

| Guardrail | Qué comprueba | Se aplica en | Requisito |
|---|---|---|---|
| `grounding_guardrail` | Todo `place_id`/`flight_number`/`hotel_id`/línea de transporte existe en el `tool_ledger` de esta ejecución, con `source` correcto | T2, T3, T5, T6, T7 | RNF-1.04 |
| `schedule_guardrail` | Sin solapes; dentro de horario de apertura; día 1 tras llegada+traslado; último día antes de check-in de vuelta | T7 | RF-04.08, 04.10 |
| `budget_guardrail` | Desglose suma el total (±1 €) y no supera el techo | T7 | RF-02.17 |
| `diet_guardrail` | Toda comida cumple la restricción dietética declarada | T5, T7 | RF-02.06 |
| `accessibility_guardrail` | Si hay movilidad reducida, todo lugar/alojamiento tiene `accessible=true` | T3, T5, T7 | RF-02.03 |
| `pace_guardrail` | Bloques/día según ritmo (±1); ningún día > 12 h | T7 | RF-02.05 |
| `opening_hours_guardrail` | Horarios para la fecha concreta, no genéricos | T5 | RF-04.08 |
| `coverage_guardrail` | Un registro por día (clima) o por par consecutivo (traslados), sin huecos | T4, T6 | RF-04.10, 04.12 |
| `min_options_guardrail` | Entre 3 y 5 opciones | T2, T3 | RNF-2.04 |
| `schema_guardrail` | Validación Pydantic estricta | todas | RNF-1.03, 3.7 |
| `source_guardrail` | Todo valor factual lleva `source`+`confidence`; nada `scraped` en precio/disponibilidad | T2, T3, T5, T6, T7 | RNF-1.04, 4.15 |
| `gap_guardrail` | Una laguna declarada se arrastra, nunca se rellena con un valor | T7 | RNF-5.7 |
| `verdict_guardrail` | Coherencia veredicto ↔ puntuaciones del revisor | T8 | RNF-6.18 |

El **guardrail de anclaje es el más importante**: convierte "prohibido inventar" (una
instrucción del prompt, ignorable) en una comprobación de conjuntos entre lo que
afirma la salida y lo que el `tool_ledger` registró de verdad. Es lo que permite
afirmar ante el tribunal que el sistema no alucina datos turísticos como invariante,
no como promesa.

```python
def make_grounding_guardrail(ledger: ToolCallLedger):
    def guardrail(output: TaskOutput) -> Tuple[bool, Any]:
        data = output.pydantic
        claimed = extract_identifiers(data)
        retrieved = ledger.identifiers()
        invented = claimed - retrieved
        mislabelled = ledger.source_mismatches(data)
        if mislabelled:
            return (False, f"Wrong source declared for: {sorted(mislabelled)}.")
        if invented:
            return (False, f"These identifiers were never returned by any tool "
                            f"in this run: {sorted(invented)}. Do not substitute "
                            f"plausible-looking values.")
        return (True, output)
    return guardrail
```

### 7.2 Guardrails probabilísticos (LLM-as-a-Judge) — solo en T8/R4

5 dimensiones, puntuación 1–10, rechaza si alguna < 7 (**< 8 en `grounding`**, porque
un dato falso presentado como cierto es el único fallo realmente inaceptable):
`temporal_feasibility`, `budget_compliance`, `hard_constraint_respect`, `grounding`,
`interest_fit`. El juez usa herramientas deterministas de solo lectura
(`schedule_validator`, `tool_call_ledger_reader`) en vez de hacer aritmética él
mismo, y **tiene prohibido reescribir** el plan.

### 7.3 Política anti-bucle

1. **Tope de 2 rondas de revisión** (`state.revision_round`).
2. **Degradación controlada**: al agotar rondas, el itinerario se entrega marcado
   `needs_attention = true` con los defectos visibles — nunca un error.
3. **Criterios cerrados**: el revisor aplica umbrales fijos, no "criterio abierto"
   (que nunca converge).

### 7.4 Qué pasa cuando un servicio falla — escalera de degradación por dominio

| Dominio | Escalera | Si todo falla |
|---|---|---|
| Vuelos | Reintento (backoff exp., 3) → relajar filtros (aerolínea→directo→clase) → ampliar aeropuertos. **Nunca raspado ni conocimiento previo** | `gap{domain: flights}`; resto del itinerario entregado, botón de reintentar |
| Alojamiento | Igual, relajando tipo→valoración→radio. **Nunca por debajo de accesibilidad** | `gap` declarado; actividades ancladas al centro del destino |
| Lugares/horarios | Reintento → consulta alternativa al mismo MCP → lector web acotado | Horario no verificado + aviso visible |
| Rutas | Reintento → modo alternativo → estimación geométrica `source=assumed` | Duración estimada con aviso explícito |
| Clima | Reintento → `confidence=low` si excede horizonte | Esos días no condicionan interior/exterior |

**Jerarquía de valores en una frase**: *un itinerario al que le falta el vuelo es
aceptable; un precio de vuelo inventado no lo es.* Una laguna declarada no penaliza
en la rúbrica del revisor; un valor inventado para taparla recibe la penalización
máxima.

### 7.5 Hooks de ejecución

**Pre-hooks** (orden deliberado: seguridad → normalización → enriquecimiento, para no
gastar tokens ni inyectar contexto en una petición que se va a rechazar):

| Hook | Función | Requisito |
|---|---|---|
| `sanitize_input` | Limpia caracteres/delimitadores interpretables como estructura | RNF-6.5 |
| `detect_prompt_injection` | Si hay patrón conocido, no ejecuta la crew y registra el intento | RNF-6.12 |
| `redact_pii` | Enmascara email/teléfono/tarjeta antes del proveedor LLM | RNF-6.15 |
| `normalize_dates` | "El próximo puente" → ISO-8601 en tz del usuario | RF-02.13, RNF-4.7 |
| `inject_hard_facts` | Top-K 3–5 hechos de pgvector filtrados por `user_id`, `min_similarity=0.78` | RF-02.10, RNF-6.3 |
| `check_quota` | Degrada de modelo o avisa en vez de fallar a mitad | RNF-1.05 |

**Post-hooks**:

| Hook | Función | Requisito |
|---|---|---|
| `validate_output` | Segunda red de guardrails sobre el resultado final | RNF-1.03, 5.1 |
| `unredact` | Restituye PII real antes de persistir/mostrar | RNF-6.15 |
| `persist_itinerary` | Escritura en una única transacción, rollback si error | RNF-5.8, 5.9 |
| `emit_agui_events` | Publica progreso/estado por SSE (AG-UI/CopilotKit) | RNF-3.4 |
| `trace_run` | Cierra el span de Langfuse: tokens, latencias, I/O | RNF-6.8, 7.16 |
| `extract_soft_facts` | En segundo plano, detecta preferencias implícitas | RF-05.01 |
| `sample_for_quality` | % configurable de ejecuciones a juez fuera de línea | RNF-5.12 |

**Hooks a nivel de herramienta** (cliente MCP): registro en `tool_ledger` + reintento
con backoff (3 intentos) + degradación elegante (resultado vacío `unavailable`, nunca
excepción propagada). El lector web usa el mismo cliente y las mismas reglas.

## 8. Contratos de datos (Pydantic)

Todas las salidas de tareas son objetos Pydantic (`output_pydantic`), **nunca prosa**.
Se descarta deliberadamente el "agente formateador" que CrewAI ofrece como
alternativa: añadiría una llamada LLM y un punto de fallo para un formato que es fijo
y está versionado con el esquema de la base de datos. Los tipos TypeScript del
frontend se generan a partir de este esquema (no se mantienen a mano) — RNF-3.6,
RNF-7.9.

```python
class Intent(BaseModel):
    kind: Literal['create_itinerary', 'modify_transport', 'modify_lodging',
                  'modify_activities', 'reschedule', 'chitchat_faq', 'ambiguous']
    target_item_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    clarifying_question: Optional[str] = None

class ItineraryItem(BaseModel):
    item_id: str
    type: Literal['activity', 'meal', 'transfer', 'checkin', 'flight']
    start_time: time
    end_time: time
    place_id: Optional[str] = None
    title: str            # es-ES
    description: str      # es-ES
    lat: Optional[float] = None
    lon: Optional[float] = None
    cost: float = 0.0
    source: Literal['mcp', 'scraped', 'assumed', 'user'] = 'mcp'
    confidence: Literal['high', 'medium', 'low'] = 'high'
    accessible: Optional[bool] = None
    dietary_tags: list[str] = Field(default_factory=list)

class Itinerary(BaseModel):
    trip_id: str
    destination: str
    days: list['ItineraryDay']
    selected_flight: FlightOption
    selected_hotel: HotelOption
    cost_breakdown: CostBreakdown
    assumptions: list[str] = Field(default_factory=list)          # RNF-1.04
    gaps: list['Gap'] = Field(default_factory=list)
    deviations: list['Deviation'] = Field(default_factory=list)
    needs_attention: bool = False
    version: int = 1                                              # bloqueo optimista

class Gap(BaseModel):
    domain: Literal['flights', 'lodging', 'places', 'routes', 'weather']
    reason: str            # es-ES
    retryable: bool
    attempted: list[str] = Field(default_factory=list)

class ReviewVerdict(BaseModel):
    verdict: Literal['approved', 'rejected']
    scores: dict[str, int]     # 5 dimensiones, 1-10
    defects: list['Defect'] = Field(default_factory=list)
    reviewer_notes: str = ''   # es-ES
```

**Idioma**: definiciones de agentes/tareas en **inglés** (fidelidad del modelo, menos
tokens, encaja con el formato de CrewAI). Todo *string* orientado al usuario dentro de
los objetos estructurados, en **español (es-ES)**, forzado por instrucción explícita
en cada tarea.

## 9. Estado del Flow (`TravelPlannerState`)

| Campo | Tipo | Papel |
|---|---|---|
| `user_id, trip_id, session_id` | UUID | Claves de aislamiento; filtran toda consulta a pgvector (RNF-6.3) |
| `briefing` | `TripBriefing` | Salida del formulario inicial (RF-02.01–09) |
| `hard_facts` | `list[Fact]` | Top-K 3–5 hechos consolidados por RAG (RF-02.10, RNF-2.04) |
| `soft_facts` | `list[Fact]` | Preferencias detectadas en la conversación actual |
| `itinerary` | `Itinerary \| None` | Estado actual del plan; reflejado en frontend vía *shared state* |
| `intent` | `Intent` | Salida del router |
| `revision_round` | `int` | Contador anti-bucle, corta en 2 |
| `pending_question` | `str \| None` | Pregunta de desambiguación en espera de respuesta humana |
| `tool_ledger` | `list[ToolCall]` | Registro de toda llamada a herramienta: procedencia + confianza. Base del guardrail de anclaje y de la traza |
| `trace_id` | `str` | Correlación con Langfuse |
| `token_budget` | `TokenBudget` | Consumidos/restantes; alimenta degradación por cuota |
| `gaps` | `list[Gap]` | Lagunas declaradas por especialistas |

## 10. Persistencia del estado y autoguardado

**No hay botón de guardar**: toda mutación (del usuario o de un agente) se persiste
sola y deja rastro. Dos estados que **no se mezclan**:

| | Estado del Flow | Estado del dominio |
|---|---|---|
| Qué es | Conversación y orquestación (rama, intención, pregunta pendiente, llamadas) | El itinerario: días, actividades, reservas, presupuesto |
| Quién escribe | El propio Flow (`@persist`) | El backend, en cada mutación |
| Dónde vive | `flow_states` (jsonb) | Tablas relacionales |
| Duración | Sesión de planificación | Mientras exista el viaje |

`@persist` de CrewAI usa SQLite por defecto → **se respalda en PostgreSQL desde el
principio** (mismo problema de concurrencia que la memoria del framework).

**Ciclo de autoguardado**: actualización optimista en la interfaz → PATCH con
debounce (~600 ms al escribir, inmediato al soltar una tarjeta) → **bloqueo
optimista** (la petición lleva `version`; si no coincide, 409 y el cliente
resincroniza — nunca se sobrescribe en silencio un cambio del usuario) → todo en
**una única transacción** (elemento + versión + fila de revisión + marca de
guardado) → difusión por SSE a todas las vistas abiertas. Indicador permanente en la
interfaz: "Guardando…" / "Guardado hace un momento" / "Sin conexión, se guardará al
reconectar".

**Dos historiales distintos, no intercambiables**:
- `chat_messages` — "qué se dijo" (alimenta la ventana deslizante de 5–10 intercambios
  al LLM, RNF-2.06).
- `trip_revisions` — "qué cambió y quién", registro **append-only**. Un mensaje puede
  producir 0–5 revisiones; arrastrar una tarjeta es una revisión sin mensaje. Se
  enlazan por `source_message_id` (NULL si el cambio fue directo del usuario).

**Deshacer no borra filas**: aplica el parche inverso como una revisión nueva (como
un libro contable: no se tachan asientos, se corrigen con uno nuevo).

### Cambios en el modelo de datos (SQL)

```sql
-- Estado de la orquestación
CREATE TABLE flow_states (
    flow_uuid    uuid PRIMARY KEY,
    trip_id      uuid REFERENCES trips(trip_id) ON DELETE CASCADE,
    user_id      uuid REFERENCES users(user_id) ON DELETE CASCADE,
    state        jsonb NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);

-- Autoguardado y bloqueo optimista
ALTER TABLE trips
    ADD COLUMN status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','generating','ready','archived')),
    ADD COLUMN version integer NOT NULL DEFAULT 1,
    ADD COLUMN autosaved_at timestamptz;

ALTER TABLE itinerary_items
    ADD COLUMN version integer NOT NULL DEFAULT 1,
    ADD COLUMN source text NOT NULL DEFAULT 'mcp'
        CHECK (source IN ('mcp','scraped','assumed','user')),
    ADD COLUMN confidence text NOT NULL DEFAULT 'high'
        CHECK (confidence IN ('high','medium','low'));

-- Historial de revisiones (append-only)
CREATE TABLE trip_revisions (
    revision_id        uuid PRIMARY KEY,
    trip_id            uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    author             text NOT NULL CHECK (author IN ('user','agent')),
    agent_role         text,             -- NULL cuando author = 'user'
    source_message_id  uuid REFERENCES chat_messages(message_id) ON DELETE SET NULL,
    patch              jsonb NOT NULL,
    inverse_patch      jsonb NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now()
);

-- Conversación
CREATE TABLE chat_messages (
    message_id   uuid PRIMARY KEY,
    trip_id      uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    role         text NOT NULL CHECK (role IN ('user','assistant','tool')),
    content      text,
    tool_calls   jsonb,
    created_at   timestamptz NOT NULL DEFAULT now()
);
```

Borrado en cascada: las 4 tablas cuelgan del viaje/usuario con `ON DELETE CASCADE`
(derecho al olvido, RF-01.11) salvo `source_message_id` (`SET NULL`: borrar una
conversación no debe destruir el historial del itinerario).

Requisitos que introduce esta capa: **RF-02.19** (autoguardado), **RF-02.20**
(reanudación de sesión), **RF-03.14** (historial de revisiones), **RF-03.15**
(deshacer/rehacer), **RF-03.16** (indicador de procedencia), **RNF-5.13** (bloqueo
optimista), **RNF-5.14** (persistencia del estado de orquestación en motor
relacional, no embebido local).

## 11. Esqueleto de código

```
backend/app/agents/
├── flows/
│   └── travel_planner_flow.py     # @start, @router, @listen  ← no lo genera Studio
├── crews/
│   ├── planning_crew/
│   │   ├── planning_crew.py
│   │   └── config/{agents,tasks}.yaml
│   └── refinement_crew/
│       ├── refinement_crew.py     # ensamblado dinámico según intención
│       └── config/{agents,tasks}.yaml
├── persistence/
│   ├── flow_state_store.py        # @persist respaldado en PostgreSQL
│   └── revisions.py                # trip_revisions + parche inverso
├── guardrails/
│   ├── deterministic.py
│   └── judges.py
├── hooks/
│   ├── pre.py
│   └── post.py
├── tools/
│   ├── mcp_clients.py              # un cliente por servidor, con ledger y reintentos
│   ├── web_reader.py               # lector acotado: solo POIs, marca source=scraped
│   ├── schedule_validator.py
│   └── ledger.py
├── models/                         # contratos Pydantic (§8)
└── state.py                        # TravelPlannerState
```

```python
# travel_planner_flow.py — la pieza que NO genera Studio
@persist()
class TravelPlannerFlow(Flow[TravelPlannerState]):

    @start()
    def receive_request(self):
        self.state.briefing = normalize_dates(self.state.briefing, self.state.tz)
        return 'received'

    @listen(receive_request)
    def load_context(self, _):
        self.state.hard_facts = retrieve_hard_facts(
            user_id=self.state.user_id,
            query=self.state.query_seed(), top_k=5, min_similarity=0.78)
        return 'context_loaded'

    @router(load_context)
    def classify_intent(self, _):
        if self.state.trip_id and trip_is_fresh(self.state.trip_id):
            return 'cached_trip'                    # RNF-2.13: ni una crew
        intent = cheap_llm.classify(message=self.state.user_message,
                                     itinerary=self.state.itinerary,
                                     output_pydantic=Intent)
        self.state.intent = intent
        if intent.confidence < 0.6 or intent.kind == 'ambiguous':
            return 'ambiguous'
        return intent.kind

    @listen('cached_trip')
    def return_cached(self): return load_itinerary(self.state.trip_id)

    @listen('chitchat_faq')
    def answer_directly(self): return cheap_llm.answer(self.state)

    @listen('ambiguous')                            # CU-03.02 · RF-03.03
    def ask_clarification(self):
        self.state.pending_question = self.state.intent.clarifying_question
        return HumanInputRequired(self.state.pending_question)  # el Flow pausa

    @listen('create_itinerary')
    def run_planning_crew(self):
        result = PlanningCrew(self.state.user_id, self.state.ledger).crew().kickoff(
            inputs=self.state.as_inputs())
        return self._apply_review_loop(result)

    @listen(or_('modify_transport', 'modify_lodging',
                'modify_activities', 'reschedule'))
    def run_refinement_crew(self):
        specialist = SPECIALIST_BY_INTENT[self.state.intent.kind]
        with_routes = moves_locations(self.state.intent)   # R2b (§3, D-020)
        crew = RefinementCrew(self.state.user_id, specialist, with_routes,
                              self.state.ledger).crew()
        return self._apply_review_loop(crew.kickoff(inputs=self.state.as_inputs()))

    def _apply_review_loop(self, result):
        while result.verdict == 'rejected' and self.state.revision_round < 2:
            self.state.revision_round += 1
            result = retry_with_defects(result)
        if result.verdict == 'rejected':
            result.itinerary.needs_attention = True
        return result

    @listen(or_(return_cached, answer_directly, ask_clarification,
                run_planning_crew, run_refinement_crew))
    def validate_and_persist(self, result):
        validate_output(result)
        persist_in_transaction(result)              # RNF-5.8 + trip_revisions
        emit_agui_events(result)                     # RNF-3.4
        trace_run(self.state)                        # RNF-7.16
        schedule_background(extract_soft_facts, self.state)
        return result
```

```python
# planning_crew.py
@CrewBase
class PlanningCrew:
    agents_config = 'config/agents.yaml'
    tasks_config  = 'config/tasks.yaml'

    def __init__(self, user_id: str, ledger: ToolCallLedger):
        self.user_id = user_id
        self.ledger = ledger

    @before_kickoff
    def prepare(self, inputs): return before_kickoff_pipeline(inputs)

    @after_kickoff
    def finalize(self, result): return after_kickoff_pipeline(result, self.ledger)

    @agent
    def travel_planner(self) -> Agent:
        return Agent(config=self.agents_config['travel_planner'], tools=[])

    @agent
    def flight_specialist(self) -> Agent:
        return Agent(config=self.agents_config['flight_specialist'],
                     tools=flight_mcp_tools(self.ledger))

    @task
    def search_flights(self) -> Task:
        return Task(config=self.tasks_config['search_flights'],
                    agent=self.flight_specialist(),
                    context=[self.decompose_brief()],
                    async_execution=True,
                    output_pydantic=FlightOptions,
                    guardrails=[make_grounding_guardrail(self.ledger),
                                min_options_guardrail])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents, tasks=self.tasks,
            process=Process.sequential,              # NO hierarchical (§2)
            # Memoria unificada de CrewAI 1.15 (§5): almacén propio de esta
            # ejecución en /tmp (se destruye al terminar) y LLM/embedder del
            # proyecto (§4). En evaluación, un almacén persistente. Ruta
            # explícita: CREWAI_STORAGE_DIR es global al proceso (D-011, D-035).
            memory=Memory(storage=self.run_storage_dir if IS_PROD else eval_storage_dir(),
                          llm=memory_llm(), embedder=project_embedder()),
            knowledge_sources=[hard_facts_source(self.user_id)],
            cache=True, max_rpm=20, tracing=True, verbose=True)
```

## 12. Evaluación y observabilidad

- **`crewai test`**: ejecuta n veces con juez LLM, tabla de puntuaciones por
  tarea/iteración (RNF-7.11, RNF-5.11). Uso previsto: 10 casos de validación con 2
  modelos distintos para comparar.
- **`crewai train`**: única vía donde la memoria persistente entre ejecuciones
  tiene sentido — el único usuario es el autor (§5). 5 iteraciones sobre el caso V01 para ajustar el nivel
  de detalle de actividades (RNF-1.09, RNF-4.17).
- **Langfuse**: trazado por ejecución (agente, prompt, herramienta, argumentos,
  tokens, latencia — RNF-6.8, 7.6, 7.16), métricas agregadas (aprobación en primera
  ronda, p50/p95 por rama, coste por itinerario/refinamiento, fallo por MCP), y
  muestreo de calidad en producción (% configurable evaluado por juez fuera de
  línea — RNF-5.12, para detectar degradación silenciosa al cambiar de modelo).
- Ver `docs/plan-de-pruebas.md` para los 12 escenarios de validación V01–V12 y el
  catálogo completo de 44 hipótesis (H-01 a H-44).
- Versionado: prompts (roles, goals, backstories) en **YAML**; lógica (herramientas,
  hooks, guardrails) en **código**. Permite cambiar un prompt y re-evaluar sin tocar
  código (condición para que RNF-7.11 sea útil en la práctica).

## 13. Lista de verificación al construir la automatización

Recorrer tras generar en CrewAI Studio y antes de dar el diseño por implementado:

- [ ] Exactamente **8 agentes**; borrar cualquier agente genérico añadido por el generador.
- [ ] Travel Planner e Itinerary Composer con lista de herramientas **vacía**; Reviewer solo con las dos deterministas de lectura.
- [ ] Solo Places Specialist tiene el lector web acotado; **ningún** agente tiene buscador genérico.
- [ ] T1 la ejecuta Travel Planner, T7 el Composer (si Studio los fusionó, separar).
- [ ] Cada especialista con **un único** servidor MCP conectado. Places Specialist recibe solo las herramientas de lugares y geocodificación de Geoapify, no las de rutas.
- [ ] `allow_delegation = false` en los 8.
- [ ] Solo T2, T3, T4 con `async_execution = true`.
- [ ] Dependencias exactas: T5 ← T1,T3,T4 · T7 ← T1–T6 · T8 ← T7.
- [ ] Ninguna `expected output` dice "un informe" o "una lista": todas enumeran campos con tipo, con `output_pydantic` asignado.
- [ ] Proceso `sequential`; memoria de la crew con un almacén propio y efímero por ejecución (`Memory(storage=…)`, con el `llm` y el `embedder` del proyecto); sin memoria persistente en producción; el SQLite común de `crewai replay` neutralizado (§5).
- [ ] Toda tarea que consulta un servicio externo puede devolver un `gap`; ningún dato factual sin `source`.
- [ ] Tras exportar el ZIP: añadir Flow, guardrails, hooks, contratos Pydantic y persistencia con autoguardado (nada de esto lo genera Studio).
- [ ] Ejecutar los 12 escenarios de validación (V01–V12) y guardar las trazas.

## 14. Lo que este diseño deliberadamente NO hace

(Para tener la respuesta lista en la defensa — cada punto tiene su justificación en
el apartado correspondiente de arriba.)

- **No** usa `Process.hierarchical` (§2). Queda como variante para comparar en pruebas.
- **No** usa agente formateador (§8): solo Pydantic.
- **No** enruta herramientas por embeddings (ScaleMCP): con 5 MCP el catálogo no
  satura el contexto. Trabajo futuro.
- **No** usa protocolos entre agentes (A2A, ACP, ANP): no existe aún un ecosistema de
  agentes comerciales turísticos con los que negociar.
- **No** ejecuta código generado por agentes: la aritmética de horarios la hace una
  herramienta determinista, no un modelo. Superficie de ataque innecesaria.
- **No** raspa precios ni disponibilidad, nunca, ni como último recurso (§6).
- **No** usa memoria persistente del framework en producción (§5) — solo en
  `crewai train`/`crewai test`. En producción, la memoria de la crew vive en un
  almacén propio de cada ejecución que se destruye al terminar.

## 15. Divergencias con la Memoria que hay que corregir antes de entregar

La `Memoria 21_09.docx` (capítulos 2 y 3) todavía describe una versión anterior del
diseño en varios puntos. **Actualizar antes de la entrega** (el detalle completo del
texto propuesto está en el documento original v2, capítulo 12):

| Dónde | Dice hoy | Debe decir |
|---|---|---|
| Cap. 2, Roles | "un planificador, uno o dos especializados y un crítico" | Un planificador, **5 especialistas** (uno por MCP), **un compositor**, un crítico |
| Cap. 2, Roles | El planificador "descompone y consolida" | Separar: el planificador **solo** descompone (T1); el compositor consolida (T7) |
| Cap. 3, módulo 4 | "Agente de logística" + "Agente de destino" (2 agentes) | Un especialista **por servidor MCP** (5 agentes) |
| Cap. 3, módulo 4 y diagramas UML | Google Maps Platform MCP para lugares y rutas | **Places MCP (Geoapify)** y **Routes MCP (Transitous)**, con datos abiertos; motivo: términos de Google Maps en el EEE (D-020) |
| Cap. 2, Coordinación | "Topología estrictamente jerárquica" | Conceptualmente jerárquica, **implementada con proceso secuencial + async** |
| Cap. 2, Agente crítico | Mezcla juez, hooks y guardrails | Tres mecanismos distintos: juez con rúbrica (tarea), guardrails (tareas), hooks (crew) |
| Cap. 3, RNF-1.04 | Temperatura baja + prompt que prohíbe inventar | Añadir el **guardrail de anclaje** como mecanismo verificable |
| Cap. 3, RNF-6.3 | Filtrado por usuario en pgvector | Añadir que la memoria del framework **no** aísla por usuario, y cómo se resuelve (§5) |
| Cap. 3, RNF-1.09/1.10 | Memoria a largo plazo y de entidad "en el producto" | Largo plazo **solo en evaluación**; entidad **retirada** en favor de pgvector |
| Cap. 2/3, memoria de CrewAI | Tres memorias (`short_term`, `long_term`, `entity`), la de largo plazo en SQLite | En CrewAI 1.15 hay **una memoria unificada** sobre LanceDB, con vistas por ámbito y un LLM que analiza cada recuerdo; almacén propio por ejecución (§5, D-035) |
| Cap. 3, RNF-5.4/5.5 | Raspado como "plan B genérico" | Acotado a datos informativos de lugares; **prohibido** en vuelos/alojamiento |
| Cap. 3, RNF-3.7 | "Pydantic o agente formateador" | Cerrar la alternativa: **solo Pydantic** |
| Cap. 3, secuencia de creación | Termina en consolidar y persistir | Añadir el bucle de revisión (tope 2 rondas) y la salida con advertencias |
| Cap. 3, vista de componentes | "Orquestador con cliente MCP, core y lector RAG" | Desglosar en capa Flow, crews y capa de control (guardrails + hooks) |
| Cap. 3, modelo de datos | Sin estado del Flow ni historial | Añadir `flow_states`, `trip_revisions`, `chat_messages`, columnas `version`/`status`/`source`/`confidence` (§10) |
| Cap. 3, requisitos | Sin autoguardado/historial/concurrencia | Añadir RF-02.19, 02.20, 03.14, 03.15, 03.16, RNF-5.13, 5.14 |

## Referencias

- Memoria del TFG, `Memoria 21_09.docx`, capítulos 2 (Estado del arte, ver
  `docs/estado-del-arte.md`) y 3 (Análisis y diseño, ver `docs/requisitos.md` y
  `docs/data-model/modelo-datos.md`). Fuente de verdad para RF, RNF, casos de uso y
  diagramas UML.
- DeepLearning.AI + CrewAI, *"Design, Develop, and Deploy Multi-Agent Systems with
  CrewAI"* (módulos 1–4): regla 80/20, opt-in agency, memoria vs. conocimiento,
  guardrails, hooks, MCP, human-in-the-loop, `crewai test`/`train`.
- CrewAI Studio v2 (`app.crewai.com/studio/v2`): usado para prototipar la topología;
  el proyecto exportado se completa a mano (Flow, guardrails, hooks, persistencia —
  nada de eso lo genera Studio).
- CrewAI, repositorio y documentación: https://github.com/crewAIInc/crewAI
- **Nota de versión**: CrewAI evoluciona rápido; algunos nombres de parámetro
  cambian entre versiones (p. ej. `guardrail` vs. `guardrails`). Fijar la versión
  exacta en `pyproject.toml` (RNF-8.6) y contrastar contra la documentación de esa
  versión concreta antes de implementar.
