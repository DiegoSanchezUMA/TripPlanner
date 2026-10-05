# Estado del arte y decisiones de alcance

> Síntesis del capítulo 2 ("Estado del arte") de `Memoria 21_09.docx`. Sirve como
> contexto de *por qué* se tomaron las decisiones arquitectónicas de
> `docs/arquitectura-multiagente-crewai.md`, no como sustituto del capítulo
> completo de la memoria (que incluye ~30 referencias bibliográficas numeradas).

## Los tres bloques técnicos que sostienen el prototipo

### 1. LLMs con razonamiento explícito
Un LLM aislado, incluso de última generación, tiene tasas de éxito bajas en
benchmarks de planificación de viajes con restricciones múltiples (fechas,
presupuesto, tiempos de desplazamiento) porque el razonamiento probabilístico falla
al combinar restricciones deterministas. Mitigación estándar en la literatura:
**Chain-of-Thought** (pasos intermedios explícitos) y **ReAct** (bucle
Pensar-Actuar-Observar, intercalando invocación de herramientas con razonamiento) —
este último es el patrón que siguen los agentes del prototipo. El LLM se usa vía
API externa; no hay entrenamiento ni fine-tuning. Lo que aporta el proyecto no es un
modelo nuevo, sino **la orquestación que lo envuelve**.

### 2. Arquitecturas multiagente
Un agente único (modelo + memoria + herramientas) funciona bien en tareas acotadas
pero se degrada al descomponer en subtareas heterogéneas. Los sistemas multiagente
(MAS) asignan cada subtarea a un agente especializado con su propio prompt y
herramientas. **CrewAI** se eligió frente a AutoGen/LangGraph porque su modelo
mental (agentes con rol/objetivo/herramientas, coordinados por proceso secuencial o
jerárquico) encaja de forma natural con el diseño, su integración con MCP está más
madura, y su curva de aprendizaje es menor.

Tres roles recurrentes en la literatura: **planificador/commander**,
**ejecutor/worker**, **crítico/reviewer** — los tres están presentes en el
prototipo (ver `docs/arquitectura-multiagente-crewai.md`). El reto documentado de
las arquitecturas con revisor es el **bucle infinito** planificador↔crítico; se
mitiga acotando rondas de revisión y fijando criterios de aceptación cerrados.

**Enfoque monolítico/serverless descartado**: un backend que trata al LLM como
parser semántico (emite JSON, el resto es código imperativo) funciona bien ante
fallos anticipados pero no ante escenarios nuevos, porque el modelo no participa en
la decisión de qué hacer después. Además, el modelo serverless (límite de ejecución
por invocación, facturación por ms) choca con la naturaleza conversacional de la
planificación, que puede extenderse horas — de ahí el despliegue en una VM de larga
duración (Oracle Cloud) en vez de funciones serverless para el backend.

### 3. Model Context Protocol (MCP)
Estandariza la conexión modelo↔herramientas externas mediante un modelo
cliente-servidor sobre JSON-RPC 2.0 (propuesto por Anthropic, 2024). Dos
transportes: `stdio` (servidor como proceso hijo) y HTTP+SSE/Streamable HTTP
(servidor remoto). El prototipo usa Streamable HTTP para sus servidores, tanto
alojados por el proveedor (p. ej. Geoapify para lugares) como en contenedores
propios (p. ej. Transitous para rutas); `stdio` queda para pruebas locales. Encaja
con el patrón BFF+CopilotKit del frontend, que ya usa SSE.
**Desacoplamiento**: cuando un proveedor externo cambia, la modificación queda
contenida en su servidor MCP, sin tocar el flujo de agentes.

Riesgo documentado a escala: con muchos servidores MCP, cargar todas las
definiciones de herramientas satura el contexto (línea de trabajo **ScaleMCP**,
enrutamiento dinámico por embeddings) — no aplica en el prototipo (solo 5
servidores), queda como trabajo futuro.

Protocolos entre agentes (no modelo↔herramienta sino agente↔agente) como **ACP**,
**A2A** (Google) y **ANP** quedan **fuera de alcance**: no existe todavía un
ecosistema maduro de agentes comerciales turísticos con los que negociar.

### 4. Memoria persistente y RAG
El conocimiento paramétrico de un LLM está congelado y no cubre datos que cambian a
diario (horarios, tarifas, disponibilidad). Respuesta: **RAG** — recuperar de una
base externa en cada consulta y anclar la generación en ese contexto.

**pgvector sobre una base vectorial dedicada** (Pinecone, Weaviate): decisión
práctica, no teórica — la aplicación ya necesita una base relacional para
usuarios/viajes/sesiones, y añadir un motor vectorial dedicado multiplicaría la
superficie operativa para un TFG.

**Framework ReMAP**: distingue **hard facts** (permanentes: restricciones
dietéticas, preferencias estables) de **soft facts** (temporales: presupuesto,
fechas de un viaje concreto). Se traslada directamente al esquema (tablas
`hard_facts` / `soft_facts` — ver `docs/data-model/modelo-datos.md`). La conversión
automática soft→hard mediante clustering por similitud temporal está en el alcance
del prototipo (algoritmo completo, pseudocódigo, en la memoria apéndice; ver
también §2.6.1 de `arquitectura-multiagente-crewai.md` sobre la regla de alcance de
la capa vectorial: **solo hechos del usuario, nunca datos del mundo**).

Limitaciones conocidas de RAG que se mitigan con medidas simples: degradación
atencional con demasiados fragmentos ("lost in the middle") → se corta
agresivamente el nº de fragmentos inyectados (Top-K 3–5); arranque en frío con
prompts ambiguos → el formulario inicial de onboarding fuerza un mínimo de contexto
antes de invocar al planificador.

## Panorama competitivo

| Producto | Enfoque | Aporta / carece |
|---|---|---|
| **TripIt** | Agrega confirmaciones de reservas por email | No genera planes desde cero |
| **Google Travel** | Metabuscador de vuelos/alojamiento | Descubrimiento y precio, no razonamiento sobre itinerario |
| **Wanderlog** | Planificador colaborativo, mapas, listas | Gran formulario inicial (inspiración directa para el onboarding del prototipo); sin reactividad real a los cambios |
| **Mindtrip** | Tarjetas con foto/valoración/"Save to Trip", panel persistente, "trazas de pensamiento" visibles | Referencia visual explícita del split-screen del prototipo |
| **Layla** | Rol de agente: pregunta si falta info, reserva desde el itinerario | — |
| **iMean AI** y similares | Segmenta bien la respuesta (dónde ir/dormir/comer/costes) | Se autocontradice entre secciones (alucinación) |
| Debilidades transversales del sector | — | Precios estimados poco fiables, difícil editar tras generar, alucinaciones puntuales, paywalls agresivos |

Sistemas académicos: recomendadores clásicos (filtrado colaborativo/basado en
contenido — predicen *qué* interesa, no construyen itinerario), algoritmos de rutas
(Tourist Trip Design Problem, variante del Team Orienteering Problem con ventanas
horarias), y sistemas basados en agentes LLM (**Vaiage**: LLM + grafo multiagente +
human-in-the-loop; **ReMAP**: personalización persistente + memoria jerárquica;
Mahajan & Patil estiman que los planificadores con IA reducen 65–70% el tiempo de
planificación frente al método tradicional).

## El hueco que cubre este TFG

Las aplicaciones comerciales resuelven bien piezas sueltas (agregación, búsqueda,
conversación) pero rara vez combinan las tres capas técnicas relevantes —agentes
especializados con razonamiento explícito, acceso estandarizado a herramientas
externas (MCP), memoria persistente que distingue perfil estable de contexto de
sesión— y cuando lo hacen es sobre stacks cerrados. Los sistemas académicos
exploran cada capa por separado en escenarios reducidos. El TFG **no aspira a
novedad algorítmica** sino a **coherencia arquitectónica y didáctica**: integrar
CrewAI (orquestación) + MCP (herramientas) + PostgreSQL/pgvector (memoria) + RAG,
con interfaz split-screen y panel de itinerario con mapa que hace visible el
proceso de construcción del viaje mientras ocurre.

## Alcance del prototipo — qué queda dentro y qué es trabajo futuro

### Dentro del alcance
- Sistema multiagente CrewAI con planificador + especialistas + agente crítico,
  coordinación jerárquica (conceptual, implementada secuencial — ver arquitectura).
- LLM comercial vía API con patrones ReAct + CoT.
- Integración con al menos un servidor MCP externo (vuelos tipo OctoTrip).
- PostgreSQL + pgvector: relacional (usuario/viaje/sesión) + vectorial (RAG).
- Esquema de memoria explícito: hard facts (perfil) vs. soft facts (sesión/viaje).
- Frontend Next.js/React/TypeScript, BFF, split-screen conversacional + dashboard
  con mapa interactivo sincronizado.
- REST/JSON + SSE para actualizaciones incrementales del itinerario.
- Conversión automática soft→hard fact por clustering de similitud (ReMAP).

### Trabajo futuro (explícitamente fuera de alcance)
- Protocolos entre agentes (ACP, A2A, ANP) — sin ecosistema comercial maduro aún.
- Enrutamiento dinámico de herramientas MCP por embeddings (ScaleMCP) — solo
  relevante si el catálogo de servidores MCP crece mucho más allá de 4.
- Participación en una "economía de agentes" Web 4.0 con transacciones autónomas —
  prospectivo, depende de la consolidación del ecosistema externo.

## Referencias
- `Memoria 21_09.docx`, capítulo 2 completo (con ~30 referencias bibliográficas
  numeradas [1]–[30], no reproducidas aquí — citar desde el documento original al
  redactar la memoria final).
- `docs/arquitectura-multiagente-crewai.md` — cómo se materializan estas decisiones
  en agentes, tareas, guardrails y persistencia concretos.
