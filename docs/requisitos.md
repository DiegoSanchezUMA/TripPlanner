# Catálogo de requisitos y casos de uso

> Síntesis de `Memoria 21_09.docx` (capítulo 3, "Análisis y diseño de la solución")
> y de la matriz de trazabilidad `Plan de Pruebas - Matriz y trazabilidad_1.xlsx`
> (hoja "Matriz Req-CU-CP"). 65 RF + 118 RNF = **183 requisitos**, 23 casos de uso en
> 5 módulos. Documentación gráfica completa (Visual Paradigm) en `docs/uml/`.
>
> **Nota de coherencia**: algunos RNF listados aquí siguen la redacción original de
> la memoria (p. ej. RNF-1.04 solo menciona "temperatura baja y prompts"); la
> implementación real añade mecanismos verificables (guardrail de anclaje, etc.) —
> ver `docs/arquitectura-multiagente-crewai.md` §15 para la lista de divergencias
> a corregir en la memoria antes de la entrega. RF-02.19/02.20, RF-03.14–03.16 y
> RNF-5.13/5.14 son requisitos **nuevos**, introducidos por el diseño del sistema
> multiagente (autoguardado, historial), y no estaban en la versión original de la
> memoria.

## Requisitos funcionales — 5 módulos (RF-mm.nn)

### Módulo 1 — Autenticación, seguridad y gestión de usuarios (11 RF)

Diagramas: `docs/uml/casos-de-uso/Autenticación, Seguridad y Gestión de Usuarios Use Case Diagram.jpg`,
`docs/uml/requisitos/Módulo 1_...Requirement Diagram.jpg`.

| ID | Título | Descripción |
|---|---|---|
| RF-01.01 | Registro de nueva cuenta | Invitado crea cuenta: email, contraseña con política mínima, fecha de nacimiento, nombre, apellido, residencia |
| RF-01.02 | Autenticación por credenciales | Validación email+contraseña; si correctos, emite JWT |
| RF-01.03 | Cierre de sesión | Purga el JWT del cliente |
| RF-01.04 | Recuperación de cuenta | Código/enlace temporal de un solo uso por email para restablecer contraseña |
| RF-01.05 | Renovación de sesión (refresh token) | Rotación de tokens transparente antes de expirar |
| RF-01.06 | Protección de rutas y recursos | Rechazo con error de autorización si token inválido/expirado |
| RF-01.07 | Cifrado unidireccional | Contraseñas con hash bcrypt/Argon2 + sal; nunca en claro |
| RF-01.08 | Consulta de perfil | Usuario autenticado ve sus datos básicos |
| RF-01.09 | Actualización de datos | Modificar nombre/preferencias de contacto |
| RF-01.10 | Cambio de contraseña activa | Exige la contraseña anterior |
| RF-01.11 | Eliminación de cuenta | Borrado en cascada de viajes + vaciado de vectores en pgvector (derecho al olvido) |

### Módulo 2 — Configuración inicial del viaje y generación del itinerario base (18 RF + 2 nuevos)

Diagramas: `docs/uml/casos-de-uso/Configuración Inicial del Viaje y Generación del Itinerario Base Use Case Diagram.jpg`.

| ID | Título | Descripción |
|---|---|---|
| RF-02.01 | Tipo de grupo de viaje | Solo / Pareja / Familia / Amigos |
| RF-02.02 | Desglose demográfico | Nº exacto de acompañantes y edades/rangos |
| RF-02.03 | Necesidades de movilidad y accesibilidad | Silla de ruedas, rampas, carrito — **hard constraint** |
| RF-02.04 | Selección de intereses turísticos | Multi-elección (cultura, gastronomía, vida nocturna, compras…) |
| RF-02.05 | Densidad de la agenda | Ritmo Relajado/Moderado/Intensivo → nº de bloques/día |
| RF-02.06 | Restricciones y dietas alimentarias | Vegano, halal, sin gluten... — **hard constraint** |
| RF-02.07 | Preferencias de alojamiento | Tipo (hotel, apartamento, hostal) |
| RF-02.08 | Medio de transporte local preferido | Transporte público, caminar, coche |
| RF-02.09 | Flexibilidad de horarios | Preferencia madrugar/alargar la noche; fechas ±N días |
| RF-02.10 | Enriquecimiento contextual mediante ReMAP | Consulta pgvector e inyecta hard facts antes del planificador |
| RF-02.11 | Disparo del flujo multiagente | Serialización del formulario + arranque coordinado de agentes |
| RF-02.12 | Gestión de estado de espera interactivo | Estado de carga dinámico ("Buscando vuelos…") |
| RF-02.13 | Manejo de excepciones y reintentos | Reintento con parámetros más flexibles o mensaje comprensible |
| RF-02.14 | Visualización cronológica diaria | Itinerario por días y franjas horarias |
| RF-02.15 | Integración de transporte sugerido | Tarjetas de vuelo (horarios, aerolíneas, escalas, traslados) |
| RF-02.16 | Integración de alojamiento propuesto | Hotel que mejor cumple ubicación/presupuesto |
| RF-02.17 | Estimación económica desglosada | Coste por categorías (transporte, hotel, actividades, comida) |
| RF-02.18 | Transición al modo conversacional | Chat habilitado tras generar, con contexto completo |
| **RF-02.19** *(nuevo)* | Autoguardado del itinerario | Toda modificación (usuario o agente) se persiste sola; UI muestra estado del guardado |
| **RF-02.20** *(nuevo)* | Reanudación de la sesión de planificación | Sesión interrumpida (incl. pausa por human-in-the-loop) se retoma sin repetir generación |

### Módulo 3 — Interacción dinámica y UI generativa (13 RF + 3 nuevos)

Diagramas: `docs/uml/casos-de-uso/Interacción Dinámica y UI Generativa Use Case Diagram.jpg`.

| ID | Título | Descripción |
|---|---|---|
| RF-03.01 | Renderizado del asistente | Chat CopilotKit acoplado a la interfaz, estilizado con Vanilla Extract |
| RF-03.02 | Transmisión en tiempo real (streaming) | Respuestas palabra a palabra |
| RF-03.03 | Desambiguación proactiva | Ante petición ambigua, pregunta antes de tocar MCP |
| RF-03.04 | Sustitución de alojamiento | Cambio de hotel aislado, sin alterar vuelos/actividades |
| RF-03.05 | Modificación de transporte | Cambios en vuelos/transporte local, solo la parte afectada |
| RF-03.06 | Alteración de actividades (CRUD) | Añadir/reemplazar/eliminar consultando Places MCP |
| RF-03.07 | Reorganización temporal | Mueve el itinerario según petición ("dormir hasta tarde el día 3") |
| RF-03.08 | Consciencia del contexto visual | Infiere referencias ("cámbiame la cena del día 2") del estado en pantalla |
| RF-03.09 | Sincronización cartográfica | Mapa se centra al recomendar un lugar |
| RF-03.10 | Ejecución de acciones en el cliente | El agente dispara funciones en el navegador |
| RF-03.11 | Visualización de resultados | Tarjetas visuales en vez de solo texto |
| RF-03.12 | Interacciones directas | Botones en tarjetas ("Confirmar este vuelo") |
| RF-03.13 | Impacto en cascada | Cambio confirmado se refleja en vista principal y presupuesto global |
| **RF-03.14** *(nuevo)* | Historial de revisiones | Cada cambio con autor, marca temporal, cambio aplicado, navegable |
| **RF-03.15** *(nuevo)* | Deshacer y rehacer | La reversión se registra como nueva revisión, sin eliminar histórico |
| **RF-03.16** *(nuevo)* | Indicador de procedencia del dato | Origen (API/scraped/estimación) y confianza por elemento |

### Módulo 4 — Motor de IA y herramientas (integración MCP) (13 RF)

Diagramas: `docs/uml/casos-de-uso/Motor de IA y Herramientas (Integración MCP) Use Case Diagram.jpg`.
Actores externos: Flight MCP (`@mcp/octotrip`), Hotel MCP (`@mcp/winwin-travel`),
Places MCP (Geoapify), Routes MCP (Transitous), Weather MCP (`@mcp_weather_server`).
Places y Routes sustituyen al Google Maps Platform MCP que aparece en el diagrama
(D-020, pendiente de actualizar el diagrama).

| ID | Título | Descripción |
|---|---|---|
| RF-04.01 | Búsqueda de vuelos | Ida/vuelta desde aeropuertos más cercanos, fechas exactas |
| RF-04.02 | Filtrado de vuelos | Sin escalas, business, equipaje, aerolíneas preferidas |
| RF-04.03 | Extracción de información de vuelos | Precios, horarios reales |
| RF-04.04 | Búsqueda de alojamiento | Disponibilidad real para fechas y ocupantes exactos |
| RF-04.05 | Filtrado de alojamiento | Cruce con hard facts (mascotas, accesibilidad, desayuno) |
| RF-04.06 | Extracción de información de alojamiento | Fotos, estrellas, valoraciones |
| RF-04.07 | Búsqueda de actividades | Categórica o lenguaje natural sobre OpenStreetMap (Places MCP) |
| RF-04.08 | Extracción de información de actividades | Horarios de apertura/cierre |
| RF-04.09 | Extracción de coordenadas | Lat/lon exactas para el mapa |
| RF-04.10 | Cálculo de tiempos de desplazamiento | Tiempo real entre POIs consecutivos |
| RF-04.11 | Trazado de rutas de transporte | Línea de bus/metro concreta |
| RF-04.12 | Obtención del tiempo | Previsión climática para coordenadas y fechas |
| RF-04.13 | Condicionamiento por tiempo | El clima como regla de decisión (interior si llueve) |

### Módulo 5 — Gestión de contexto, memoria y conocimiento — RAG (5 RF)

Diagramas: `docs/uml/casos-de-uso/Gestión de Contexto, Memoria y Conocimiento (RAG) Use Case Diagram.jpg`.

| ID | Título | Descripción |
|---|---|---|
| RF-05.01 | Extracción de preferencias implícitas | Soft facts no declarados, desde el historial de conversación |
| RF-05.02 | Evaluación de recurrencia por similitud | Agrupa soft facts semejantes; promociona a hard fact si se repiten |
| RF-05.03 | Vectorización de los hechos | Embeddings en pgvector |
| RF-05.04 | Recuperación aumentada (RAG) | Al iniciar viaje, recupera las reglas históricas más relevantes |
| RF-05.05 | Consolidación de hecho por criticidad | Datos vitales (alergias, dieta, movilidad) → hard fact inmediato, sin esperar recurrencia |

## Requisitos no funcionales — ISO/IEC 25010, 9 características (RNF-c.nn)

118 RNF en total. Detalle exhaustivo con métrica, fórmula, herramienta de medición y
caso/hipótesis asociados en la hoja "Métricas RNF (ISO 25023)" de
`Plan de Pruebas - Matriz y trazabilidad_1.xlsx` (no reproducido aquí por volumen).
Resumen por característica:

### 1. Adecuación funcional (10 RNF: RNF-1.01–1.10)
Alcance del MVP, cobertura de la interacción por chat, integridad del intercambio de
datos (validación Pydantic), **mitigación de alucinaciones** (RNF-1.04 — ver
guardrail de anclaje en `arquitectura-multiagente-crewai.md`), manejo de cuotas
gratuitas, inyección de contexto estricta, restricción de herramientas por agente,
memoria corto/largo plazo/entidad (ver §5 del doc de arquitectura para el diseño
real, distinto de esta redacción original).

### 2. Eficiencia de desempeño (20 RNF: RNF-2.01–2.20)
Latencia de generación (≤120 s, objetivo 90 s), TTFT conversacional (<3 s),
recuperación vectorial (<500 ms), optimización de tokens (3–5 hard facts Top-K),
memoria de servidor sin fugas, poda de historial (≤10 intercambios), concurrencia
(≥5 usuarios), límite de hard facts por usuario (≤50), aislamiento de herramientas,
async, paralelismo T2-T4, router de flujo, diseño atómico de tareas, especialización
de agentes.

### 3. Compatibilidad (8 RNF: RNF-3.1–3.8)
Contenedores sin conflicto, config por `.env`, estándar MCP abierto, AG-UI
(frontend↔agente), API FastAPI, paridad de contratos Pydantic↔TypeScript, salidas
estructuradas forzadas, estado compartido en Flows.

### 4. Capacidad de interacción / usabilidad (17 RNF: RNF-4.1–4.17)
Claridad de propósito, previsualización, paradigma conversacional, formularios
intuitivos, UI generativa, navegación contextual, validación estricta en cliente,
desambiguación de prompts vagos, streaming, feedback visual (<2 s sin cambio),
accesibilidad WCAG 2.1 AA (Lighthouse ≥90), responsive, chips de sugerencia,
mensajes de error constructivos, transparencia de IA, visibilidad de herramientas en
uso, **human-in-the-loop** (RNF-4.17).

### 5. Fiabilidad (14 RNF: RNF-5.1–5.14, incluye 5.13/5.14 nuevos)
Prevención de errores de formato, estabilidad de estado en chat, disponibilidad
académica (≥95%/7 días), degradación con scraping acotado, tolerancia a rate limits,
tolerancia a caídas de MCP, persistencia transaccional ACID, recuperación de
itinerario confirmado, razonamiento previo (planificador/revisor), puntuación
iterativa (`crewai test`), muestreo de calidad en producción, **RNF-5.13 bloqueo
optimista**, **RNF-5.14 persistencia del estado de orquestación en motor relacional**.

### 6. Seguridad (18 RNF: RNF-6.1–6.18)
Cifrado en reposo (bcrypt/Argon2) y en tránsito (TLS 1.3), aislamiento de memoria
vectorial por `user_id`, integridad referencial, sanitización de entradas (hooks),
registro de creación/sesión, **trazabilidad de agentes** (Langfuse), auditoría de
modificaciones, verificación JWT, autenticidad de servicios externos, **resistencia a
prompt injection** (RNF-6.12), rate limiting defensivo, **guardrails** (RNF-6.14),
hooks de intercepción, asignación restringida de herramientas, ejecución segura de
código (no aplica — el diseño no ejecuta código generado), **LLM-as-a-Judge**
(RNF-6.18).

### 7. Mantenibilidad (16 RNF: RNF-7.1–7.16)
Arquitectura en 3 capas (BFF), capa Flows aislando lógica de IA, especialización
atómica de agentes, componentización de UI (Storybook), estandarización MCP,
trazado profundo, registro de excepciones, **agnosticismo de LLM** (cambiar proveedor
= variable de entorno), tipado estático compartido, pruebas deterministas sin gastar
tokens, evaluación cuantitativa (`crewai test`) y probabilística (juez), pruebas
unitarias backend/frontend, análisis estático (SonarQube, quality gate — ver
`docs/plan-de-pruebas.md`), trazabilidad de ejecución.

### 8. Flexibilidad (8 RNF: RNF-8.1–8.8)
Agnosticismo de LLM, integración dinámica de herramientas MCP, escalado horizontal
FastAPI (stateless), rendimiento sostenido de RAG con índices HNSW, contenedorización
integral (Docker Compose, 1 comando), determinismo de dependencias (lockfiles),
intercambiabilidad del frontend, sustitución de fuentes de datos externas.

### 9. Seguridad física / safety (7 RNF: RNF-9.1–9.7)
Prevención de itinerarios temerarios (sin exterior con alerta de tormenta/calor),
rutas seguras (nunca a pie por vías sin infraestructura peatonal), **respeto
estricto de movilidad como hard constraint** (RNF-9.3), detección climática
proactiva, datos de auxilio local (112, consulado/embajada), alertas visuales,
**redirección de consultas críticas de salud sin diagnosticar** (RNF-9.7).

## Casos de uso — 23 en 5 módulos

Actor principal: **Usuario Autenticado** (hereda de Usuario Invitado). Desde el
módulo 2, los **Servidores MCP** aparecen como actor "sistema externo".

| Módulo | Casos de uso |
|---|---|
| 1. Auth/usuarios | CU-01.01 Registrar cuenta · CU-01.02 Iniciar sesión · CU-01.03 Recuperar cuenta · CU-01.04 Cerrar sesión · CU-01.05 Consultar perfil · CU-01.06 Actualizar datos · CU-01.07 Cambiar contraseña · CU-01.08 Eliminar cuenta · CU-01.09 Borrar historial y preferencias vectoriales (interno de 01.08, derecho al olvido) |
| 2. Config./generación | CU-02.01 Configurar parámetros del viaje (onboarding) · CU-02.02 Generar itinerario base · CU-02.03 Recuperar contexto ReMAP (interno) · CU-02.04 Orquestar flujo multiagente (interno) · CU-02.05 Gestionar reintentos por fallo de servicios (extensión) · CU-02.06 Visualizar itinerario |
| 3. Interacción/UI generativa | CU-03.01 Interactuar con el itinerario mediante chat · CU-03.02 Resolución de ambigüedad de prompt (extensión, human-in-the-loop) · CU-03.03 Sincronización de pantalla (Shared State) · CU-03.04 Interacción con componentes visuales generados |
| 4. Motor de IA / MCP | CU-04.01 Gestionar vuelos · CU-04.03 Gestionar hoteles · CU-04.04 Gestionar actividades y puntos de interés · CU-04.05 Analizar tiempo (incluido en 04.04) · CU-04.06 Trazar ruta (incluido en 04.04) |
| 5. Memoria/RAG | CU-05.01 Extraer preferencias del viaje · CU-05.02 Consolidar conocimiento a largo plazo (proceso por lotes) · CU-05.03 Recuperar contexto mediante RAG |

**Nota de implementación**: el diagrama de casos de uso del módulo 4 sugiere un
agente por servidor MCP — es exactamente lo que implementa el diseño final (5
especialistas desde D-020), no los "2 agentes agrupados" que describía una versión anterior de
la memoria (ver `docs/arquitectura-multiagente-crewai.md` §15).

## Referencias
- `Memoria 21_09.docx`, capítulo 3 (fuente original, con descripciones en prosa de
  cada RF/RNF y de los 5 diagramas de casos de uso).
- `Plan de Pruebas - Matriz y trazabilidad_1.xlsx`, hoja "Matriz Req-CU-CP" (mapeo
  completo requisito ↔ casos de uso ↔ casos de prueba ↔ hipótesis, con nº de casos
  por requisito).
- Diagramas de requisitos por característica ISO 25010 y por módulo:
  `docs/uml/requisitos/*.jpg`.
