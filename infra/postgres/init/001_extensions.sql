-- Se ejecuta una única vez, la primera vez que el volumen de datos está vacío
-- (mecanismo estándar de la imagen oficial de Postgres: todo lo que hay en
-- /docker-entrypoint-initdb.d se ejecuta en orden alfabético al inicializar).

-- pgvector: necesaria para hard_facts.embedding y soft_facts.embedding
-- (ver docs/data-model/modelo-datos.md). La imagen pgvector/pgvector:0.8.7-pg16-bookworm ya trae
-- el binario compilado; aquí solo se activa para esta base de datos concreta.
CREATE EXTENSION IF NOT EXISTS vector;

-- gen_random_uuid() para las claves primarias uuid (users.id, trips.id, etc.)
-- ya viene en el core de Postgres 16 vía pgcrypto; se activa explícitamente
-- por claridad y porque algunas herramientas de migración lo esperan declarado.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
