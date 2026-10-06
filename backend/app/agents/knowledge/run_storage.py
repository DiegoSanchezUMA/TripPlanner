"""Knowledge de CrewAI en un Qdrant en memoria, propio de cada ejecución (D-036).

El ``KnowledgeStorage`` de serie de CrewAI 1.15.23 guarda el knowledge de todas las
crews del proceso en un mismo ChromaDB en disco (colección ``knowledge_crew``, en
una ruta que se fija al importar CrewAI). Con varios usuarios, la crew de uno
recupera los hechos de otro (RNF-6.3). Aquí cada instancia tiene su propio Qdrant
en memoria, que desaparece con ella: el aislamiento no depende de ningún filtro.
"""

import asyncio
import threading
from collections.abc import Callable
from typing import Any, Self, cast

from crewai.knowledge.storage.factory import set_knowledge_storage_factory
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage
from crewai.rag.core.base_embeddings_callable import EmbeddingFunction
from crewai.rag.core.types import Documents
from crewai.rag.embeddings.factory import build_embedder
from crewai.rag.embeddings.types import EmbedderConfig
from crewai.rag.qdrant.client import QdrantClient as CrewQdrantClient
from crewai.rag.types import SearchResult
from pydantic import PrivateAttr, model_validator
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


class RunKnowledgeStorage(KnowledgeStorage):
    """Almacén del knowledge de una sola ejecución.

    Además del aislamiento, corrige tres cosas del adaptador de Qdrant de CrewAI:

    - **Dimensión.** CrewAI crea la colección con 384 dimensiones (las del modelo
      local de fastembed). Aquí se crea con la del embedder del proyecto.
    - **Vía async.** Los agentes consultan con ``aquery_knowledge``. Con un cliente
      síncrono, CrewAI lanzaría un error, lo registraría y devolvería ``[]``: la crew
      seguiría sin los hechos del usuario y sin avisar. Aquí la vía async delega en
      la síncrona en un hilo.
    - **Errores.** El de serie se traga cualquier error de búsqueda y devuelve
      ``[]``. Aquí se propagan; solo "el usuario no tiene hechos" devuelve ``[]``.

    El modo local de qdrant-client no sincroniza hilos, y las tareas async de la
    PlanningCrew consultan a la vez, así que el acceso se serializa con un cerrojo.
    """

    _qdrant: QdrantClient = PrivateAttr()
    _embed: Callable[[str], list[float]] = PrivateAttr()
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    # Mismo nombre que el validador de KnowledgeStorage para sustituirlo: el de
    # serie crearía el cliente de ChromaDB común.
    @model_validator(mode="after")
    def _init_client(self) -> Self:
        if self.embedder is None:
            # Sin embedder, CrewAI usaría el de OpenAI por defecto (§4 y §5).
            raise ValueError("RunKnowledgeStorage necesita el embedder del proyecto (D-036)")
        # build_embedder acepta un dict o un proveedor, pero sus sobrecargas no
        # cubren la unión EmbedderConfig (CrewAI lo ignora igual en KnowledgeStorage).
        embed_batch = cast(
            "EmbeddingFunction[Documents]",
            build_embedder(self.embedder),  # pyright: ignore[reportCallIssue, reportArgumentType]
        )
        # Cada texto se embebe una vez: save() mide la dimensión con el primero.
        cache: dict[str, list[float]] = {}

        def embed(text: str) -> list[float]:
            if text not in cache:
                cache[text] = [float(x) for x in embed_batch([text])[0]]
            return cache[text]

        self._embed = embed
        self._qdrant = QdrantClient(location=":memory:")
        self._client = CrewQdrantClient(client=self._qdrant, embedding_function=embed)
        return self

    @property
    def _collection(self) -> str:
        # El mismo nombre que usa KnowledgeStorage.
        return f"knowledge_{self.collection_name}" if self.collection_name else "knowledge"

    def save(self, documents: list[str]) -> None:
        if not documents:
            return
        with self._lock:
            if not self._qdrant.collection_exists(self._collection):
                size = len(self._embed(documents[0]))
                self._qdrant.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE),
                )
            super().save(documents)

    def search(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        if not query:
            raise ValueError("La consulta no puede estar vacía")
        with self._lock:
            if not self._qdrant.collection_exists(self._collection):
                return []  # El usuario no tiene hechos: no es un error.
            return self._get_client().search(
                collection_name=self._collection,
                query=" ".join(query),
                limit=limit,
                metadata_filter=metadata_filter,
                score_threshold=score_threshold,
            )

    def reset(self) -> None:
        with self._lock:
            if self._qdrant.collection_exists(self._collection):
                self._qdrant.delete_collection(self._collection)

    async def asearch(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        return await asyncio.to_thread(self.search, query, limit, metadata_filter, score_threshold)

    async def asave(self, documents: list[str]) -> None:
        await asyncio.to_thread(self.save, documents)

    async def areset(self) -> None:
        await asyncio.to_thread(self.reset)


def _new_run_storage(
    embedder: EmbedderConfig | None, collection_name: str | None
) -> RunKnowledgeStorage:
    return RunKnowledgeStorage(embedder=embedder, collection_name=collection_name)


def install_knowledge_storage() -> None:
    """Hace que todo ``Knowledge`` sin ``storage=`` explícito use uno nuevo y propio.

    Cubre el caso habitual, ``Crew(knowledge_sources=...)`` o
    ``Agent(knowledge_sources=...)``, en el que CrewAI construye el ``Knowledge``
    por su cuenta. La fábrica es global al proceso, pero no guarda estado: cada
    llamada crea un almacén nuevo, así que no hay carrera entre ejecuciones.
    """
    set_knowledge_storage_factory(_new_run_storage)
