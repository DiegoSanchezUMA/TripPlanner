"""Memoria de CrewAI en un Qdrant Edge propio de cada ejecución (D-036).

Sin configurar nada, ``Memory()`` guarda en un LanceDB en una ruta común a todo el
proceso. Eso incluye la memoria que todo ``Flow`` crea por su cuenta
(``Memory(root_scope="/flow/<nombre>")``), así que lo que se recordara para un
usuario lo podría recuperar la ejecución de otro (RNF-6.3). Aquí cada instancia
tiene su propio directorio temporal, que se borra al cerrarla o al dejar de usarse.
En el contenedor, ``/tmp`` está en memoria (D-035): nada toca el disco.
"""

import atexit
import shutil
import tempfile
import threading
import weakref
from datetime import datetime
from typing import Any

from crewai.memory.storage.factory import set_memory_storage_factory
from crewai.memory.storage.qdrant_edge_storage import QdrantEdgeStorage
from crewai.memory.types import MemoryRecord, ScopeInfo

# Las dos especificaciones de serie de Memory(storage=...), cuya ruta es común al proceso.
_BUILT_IN_SPECS = frozenset({"lancedb", "qdrant-edge"})


class RunMemoryStorage(QdrantEdgeStorage):
    """Almacén de la memoria de una sola ejecución.

    Sobre el ``QdrantEdgeStorage`` de CrewAI 1.15.23 cambia dos cosas:

    - **Cerrojo.** El de serie abre el *shard* en cada operación y no sincroniza
      hilos. La memoria guarda en segundo plano mientras los agentes consultan, y
      con 8 hilos se perdían 20 de cada 100 guardados ("path already contains
      segment data"). Aquí todas las operaciones se serializan. Las variantes
      async del original delegan en las síncronas, así que también pasan por él.
    - **Limpieza.** El de serie se registra en ``atexit`` para volcar sus datos a un
      *shard* "central" al salir. Eso lo mantendría vivo, con su directorio, hasta
      el final del proceso. Aquí no hay nada que conservar: el directorio se borra
      al cerrar o cuando el objeto deja de usarse.
    """

    def __init__(self) -> None:
        # Antes de super().__init__, que ya llama a métodos que usan el cerrojo.
        self._lock = threading.RLock()
        super().__init__(path=tempfile.mkdtemp(prefix="crewai-memory-"))
        atexit.unregister(self.close)
        self._remove_dir = weakref.finalize(
            self, shutil.rmtree, self._base_path, ignore_errors=True
        )

    def save(self, records: list[MemoryRecord]) -> None:
        with self._lock:
            super().save(records)

    def search(
        self,
        query_embedding: list[float],
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[MemoryRecord, float]]:
        with self._lock:
            return super().search(
                query_embedding,
                scope_prefix=scope_prefix,
                categories=categories,
                metadata_filter=metadata_filter,
                limit=limit,
                min_score=min_score,
            )

    def delete(
        self,
        scope_prefix: str | None = None,
        categories: list[str] | None = None,
        record_ids: list[str] | None = None,
        older_than: datetime | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> int:
        with self._lock:
            return super().delete(
                scope_prefix=scope_prefix,
                categories=categories,
                record_ids=record_ids,
                older_than=older_than,
                metadata_filter=metadata_filter,
            )

    def update(self, record: MemoryRecord) -> None:
        with self._lock:
            super().update(record)

    def get_record(self, record_id: str) -> MemoryRecord | None:
        with self._lock:
            return super().get_record(record_id)

    def list_records(
        self, scope_prefix: str | None = None, limit: int = 200, offset: int = 0
    ) -> list[MemoryRecord]:
        with self._lock:
            return super().list_records(scope_prefix=scope_prefix, limit=limit, offset=offset)

    def get_scope_info(self, scope: str) -> ScopeInfo:
        with self._lock:
            return super().get_scope_info(scope)

    def list_scopes(self, parent: str = "/") -> list[str]:
        with self._lock:
            return super().list_scopes(parent)

    def list_categories(self, scope_prefix: str | None = None) -> dict[str, int]:
        with self._lock:
            return super().list_categories(scope_prefix)

    def count(self, scope_prefix: str | None = None) -> int:
        with self._lock:
            return super().count(scope_prefix)

    def reset(self, scope_prefix: str | None = None) -> None:
        with self._lock:
            super().reset(scope_prefix)

    def touch_records(self, record_ids: list[str]) -> None:
        with self._lock:
            super().touch_records(record_ids)

    def optimize(self) -> None:
        with self._lock:
            super().optimize()

    def flush_to_central(self) -> None:
        with self._lock:
            super().flush_to_central()

    def close(self) -> None:
        # Sin volcar al shard central: el directorio entero desaparece.
        with self._lock:
            self._closed = True
            self._remove_dir()


def _new_run_memory_storage(spec: str) -> RunMemoryStorage:
    if spec not in _BUILT_IN_SPECS:
        # Una ruta explícita sería un almacén persistente fuera de este control.
        # En evaluación (§5) se pasa una instancia, p. ej. QdrantEdgeStorage(path=...).
        msg = f"Memory(storage={spec!r}): pasa un StorageBackend explícito (D-036)"
        raise ValueError(msg)
    return RunMemoryStorage()


def install_memory_storage() -> None:
    """Hace que todo ``Memory`` sin ``storage=`` explícito use uno nuevo y propio.

    Cubre ``Crew(memory=True)``, ``Memory(...)`` sin ``storage`` y la memoria que
    crea cada ``Flow``. La fábrica es global, pero no guarda estado: cada llamada
    crea un almacén nuevo, así que no hay carrera entre ejecuciones.
    """
    set_memory_storage_factory(_new_run_memory_storage)
