# syntax=docker/dockerfile:1
#
# Imagen del backend (FastAPI + CrewAI en un único proceso, D-011). D-034.
# Contexto de build: backend/ (ver docker-compose.yml). Lo que entra en el
# contexto lo limita Dockerfile.dockerignore, junto a este fichero.
#
# Dos etapas sobre la misma imagen de Python, para que el intérprete esté en la
# misma ruta y el entorno virtual funcione al copiarlo de una a otra:
#   builder: Python + uv. Instala las dependencias en /app/.venv.
#   runner:  solo Python, el entorno ya instalado y el código. Sin el uv del
#            builder (el .venv trae otro: crewai-cli depende de él), sin la
#            caché de uv y sin root. Solo /tmp es escribible (D-035).

# Etapa auxiliar: solo aporta el ejecutable de uv a la etapa builder, en la
# versión exacta de D-016. No entra en la imagen final.
FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

# ---------------------------------------------------------------- builder ----
FROM python:3.13.16-slim-trixie AS builder

COPY --from=uv /uv /bin/uv

# UV_COMPILE_BYTECODE: compila a .pyc al instalar, así el contenedor arranca
#   más rápido.
# UV_LINK_MODE=copy: la caché de uv está en otro sistema de ficheros (cache
#   mount) y no se pueden crear enlaces duros hacia ella.
# UV_PYTHON_DOWNLOADS=0: usar el Python de la imagen, nunca descargar otro.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Solo las dependencias. Esta capa no se vuelve a construir mientras no cambien
# uv.lock ni pyproject.toml, aunque cambie el código.
# - Los dos ficheros entran por bind mount: se leen, pero no se copian a la
#   imagen.
# - La caché de uv es un cache mount: sobrevive entre builds de la misma
#   máquina, así que un cambio en el lock solo descarga lo nuevo.
# - --locked --no-build: el lock tiene que estar al día y solo se instalan
#   wheels, sin compilar nada (D-031). --no-dev: sin pytest, ruff ni pyright.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-build --no-dev --no-install-project

# ----------------------------------------------------------------- runner ----
FROM python:3.13.16-slim-trixie AS runner

# Usuario sin privilegios con UID y GID fijos.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# El entorno primero y el código después: el código cambia en casi cada commit
# y así solo se rehace su capa. Todo queda de root, de solo lectura para app.
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY app ./app

# PYTHONDONTWRITEBYTECODE: el código es de solo lectura, que no intente
# escribir .pyc. PYTHONUNBUFFERED: logs al momento, sin búfer.
# HOME y CREWAI_STORAGE_DIR en /tmp (D-035): el usuario app no tiene carpeta
# personal y CrewAI escribe en disco nada más importarse (crea su carpeta de
# datos) y en cada Crew (SQLite de salidas de tareas). /tmp es el único sitio
# escribible: efímero y, en el Compose, en memoria (tmpfs).
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    CREWAI_STORAGE_DIR=/tmp/crewai

USER app
EXPOSE 8000

# Sin curl en la imagen slim: la comprobación usa el propio Python.
# "docker compose up --wait" espera a que este check pase.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Un único proceso y un único worker (D-011).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
