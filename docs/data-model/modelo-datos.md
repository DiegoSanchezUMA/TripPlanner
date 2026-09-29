# Modelo de datos

> Síntesis del diagrama de clases (`docs/uml/clases/Diagrama de clases.jpg`,
> Visual Paradigm) descrito en `Memoria 21_09.docx` cap. 3, ampliado con las tablas
> de orquestación/autoguardado de `Diseno sistema multiagente CrewAI - TFG v2.docx`
> cap. 9 (ver `docs/arquitectura-multiagente-crewai.md` §10 para el porqué de cada
> tabla). Motor único: **PostgreSQL 16 + pgvector** (relacional y vectorial en el
> mismo motor, decisión justificada en el estado del arte — ver
> `docs/estado-del-arte.md`).

## Tablas base (diagrama de clases original)

```
users
├── id (uuid, PK)
├── username, email, password_hash
├── first_name, last_name, date_of_birth, residence
├── created_at, updated_at
│
├──< trips (user_id FK)
│    ├── id (uuid, PK)
│    ├── title, destination, origin, start_date, end_date
│    ├── group_type, travelers_count, tempo, status
│    ├── total_estimated_cost, created_at, updated_at
│    │
│    ├──< trip_days (trip_id FK)
│    │    ├── day_date, day_order, daily_food_budget, daily_budget
│    │    │
│    │    ├──< itinerary_items (trip_day_id FK)
│    │    │    ├── item_type, title, description
│    │    │    ├── start_time, end_time, cost
│    │    │    ├── location_lat, location_lng, place_id
│    │    │    └── mcp_metadata
│    │    │
│    │    └──< trip_day_weather (trip_day_id FK)
│    │         ├── temperature_min/max/mean, precipitation_probability/sum
│    │         ├── snowfall_sum, wind_speed_max, wind_gusts_max, weather_code
│    │         └── sunrise, sunset, fetched_at
│    │
│    ├──< trip_preferences (trip_id FK)
│    │    └── mobility_needs, dietary_restrictions, accommodation_pref,
│    │        transport_pref, interests_tags
│    │
│    └──< trip_reservations (trip_id FK)
│         ├── reservation_type, name, booking_reference
│         ├── start_datetime, end_datetime, total_cost, mcp_metadata
│         │
│         ├──o flight_reservations (trip_reservations_id FK, 1:1)
│         │    ├── airline, airline_code, alliance, is_direct, stops
│         │    ├── total_duration_minutes, origin/destination_airport
│         │    ├── baggage, tags
│         │    └──< flight_legs (flight_reservations_id FK)
│         │         └── leg_order, flight_number, carrier, aircraft,
│         │             departure/arrival_airport, duration_minutes
│         │
│         └──o hotel_reservations (trip_reservations_id FK, 1:1)
│              └── hotel_address, city, country, star_rating, room_type,
│                  meal_plan, guests_count, rooms_count, amenities,
│                  photos, cancellation_policy, taxes
│
├──< soft_facts (user_id FK, trip_id FK)
│    └── content, embedding (vector), created_at
│
└──< hard_facts (user_id FK — NO trip_id, permanentes)
     └── fact_type, content, embedding (vector), created_at, updated_at
```

**Distinción hard/soft facts** (implementación directa de ReMAP — ver
`docs/estado-del-arte.md`): `hard_facts` vive asociado solo a `user_id` (permanente,
p. ej. alergia, movilidad reducida); `soft_facts` se asocia a `user_id` + `trip_id`
(volátil, p. ej. preferencia de un viaje concreto). Ambas tienen columna `embedding`
para búsqueda vectorial vía pgvector — es la **única** información que vive en la
capa vectorial (ver regla de alcance en `arquitectura-multiagente-crewai.md` §5:
pgvector guarda quién es el usuario, nunca datos del mundo).

## Tablas de orquestación y autoguardado (añadidas por el diseño multiagente v2)

Estas tablas **no aparecen** en el diagrama de clases original de Visual Paradigm —
hay que añadirlas antes de la entrega (ver divergencias en
`arquitectura-multiagente-crewai.md` §15).

```sql
-- Estado del CrewAI Flow (conversación/orquestación, distinto del estado del dominio)
CREATE TABLE flow_states (
    flow_uuid    uuid PRIMARY KEY,
    trip_id      uuid REFERENCES trips(trip_id) ON DELETE CASCADE,
    user_id      uuid REFERENCES users(user_id) ON DELETE CASCADE,
    state        jsonb NOT NULL,        -- TravelPlannerState serializado
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON flow_states (trip_id);

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

-- Historial de revisiones del itinerario (append-only; deshacer = revisión nueva)
CREATE TABLE trip_revisions (
    revision_id        uuid PRIMARY KEY,
    trip_id            uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    author             text NOT NULL CHECK (author IN ('user','agent')),
    agent_role         text,             -- NULL cuando author = 'user'
    source_message_id  uuid REFERENCES chat_messages(message_id) ON DELETE SET NULL,
    patch              jsonb NOT NULL,   -- ItineraryPatch aplicado
    inverse_patch      jsonb NOT NULL,   -- para deshacer
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON trip_revisions (trip_id, created_at DESC);

-- Conversación (distinta del historial de revisiones — "qué se dijo" vs "qué cambió")
CREATE TABLE chat_messages (
    message_id   uuid PRIMARY KEY,
    trip_id      uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    role         text NOT NULL CHECK (role IN ('user','assistant','tool')),
    content      text,
    tool_calls   jsonb,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON chat_messages (trip_id, created_at);
```

**Borrado en cascada** (RF-01.11, derecho al olvido): todas las tablas cuelgan de
`trips`/`users` con `ON DELETE CASCADE`, salvo `source_message_id` en
`trip_revisions` (`SET NULL` — borrar la conversación no debe destruir el historial
del itinerario, son dos cosas distintas y auditables por separado).

## Índices vectoriales

`RNF-8.4` (rendimiento sostenido de RAG con volumen) exige índices **HNSW** en las
columnas `embedding` de `soft_facts` y `hard_facts` para mantener latencia baja
incluso con miles de registros por usuario. `RNF-2.03` exige recuperación top-K en
menos de 500 ms.

## Referencias
- `docs/uml/clases/Diagrama de clases.jpg` — diagrama fuente (Visual Paradigm).
- `docs/arquitectura-multiagente-crewai.md` §9–10 — por qué existen `flow_states` y
  `trip_revisions`, y el ciclo completo de autoguardado con bloqueo optimista.
- `docs/estado-del-arte.md` — justificación de pgvector sobre PostgreSQL frente a
  una base vectorial dedicada, y del algoritmo de consolidación soft→hard fact.
