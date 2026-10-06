"""Knowledge por ejecución (D-036): aislamiento, dimensión, vía async y ChromaDB."""

import importlib
import importlib.util
import re
import sys
import zlib

import numpy as np
import pytest
from crewai.knowledge.knowledge import Knowledge
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.storage.factory import (
    resolve_knowledge_storage,
    set_knowledge_storage_factory,
)
from crewai.rag.core.types import Documents, Embeddings
from crewai.rag.embeddings.providers.custom.custom_provider import CustomProvider
from crewai.rag.embeddings.providers.custom.embedding_callable import CustomEmbeddingFunction
from qdrant_client.models import VectorParams

import app.agents
from app.agents.knowledge import RunKnowledgeStorage

# Como el embedder de Gemini. El adaptador de Qdrant de CrewAI crearía la
# colección con 384 dimensiones y fallaría.
DIM = 768


class BagOfWordsEmbedding(CustomEmbeddingFunction):
    """Embedder determinista y sin red: cada palabra suma 1 en una dimensión."""

    def __call__(self, input: Documents) -> Embeddings:
        vectors: Embeddings = []
        for text in input:
            vector = np.zeros(DIM, dtype=np.float32)
            for word in re.findall(r"\w+", text.lower()):
                vector[zlib.crc32(word.encode()) % DIM] += 1.0
            vectors.append(vector)
        return vectors


EMBEDDER = CustomProvider(embedding_callable=BagOfWordsEmbedding)


def crew_knowledge(*facts: str) -> Knowledge:
    """Construye el Knowledge igual que Crew(knowledge_sources=...) (crew.py:711)."""
    knowledge = Knowledge(
        sources=[StringKnowledgeSource(content=fact) for fact in facts],
        embedder=EMBEDDER,
        collection_name="crew",
    )
    knowledge.add_sources()
    return knowledge


def contents(knowledge: Knowledge, query: str) -> list[str]:
    return [r["content"] for r in knowledge.query([query], score_threshold=0.0)]


def test_importing_agents_package_installs_run_storage() -> None:
    set_knowledge_storage_factory(None)

    importlib.reload(app.agents)

    assert isinstance(resolve_knowledge_storage(EMBEDDER, "crew"), RunKnowledgeStorage)


def test_knowledge_built_by_crewai_uses_run_storage() -> None:
    assert isinstance(crew_knowledge("x").storage, RunKnowledgeStorage)


def test_each_run_only_sees_its_own_facts() -> None:
    # La fuga que motivó D-036: con el almacén de serie, B recuperaba la alergia de A.
    user_a = crew_knowledge("Usuario A: alergia grave a los frutos secos.")
    user_b = crew_knowledge("Usuario B: prefiere hoteles de la cadena Melia.")

    assert contents(user_b, "alergia frutos secos") == [
        "Usuario B: prefiere hoteles de la cadena Melia."
    ]
    assert contents(user_a, "alergia frutos secos") == [
        "Usuario A: alergia grave a los frutos secos."
    ]


def test_collection_uses_embedder_dimension() -> None:
    knowledge = crew_knowledge("Viaja con silla de ruedas.")
    storage = knowledge.storage
    assert isinstance(storage, RunKnowledgeStorage)

    info = storage._qdrant.get_collection("knowledge_crew")  # pyright: ignore[reportPrivateUsage]

    vectors = info.config.params.vectors
    assert isinstance(vectors, VectorParams)
    assert vectors.size == DIM


async def test_async_query_returns_facts() -> None:
    # Los agentes consultan por esta vía (agent/utils.py: aquery_knowledge). Con un
    # cliente síncrono, el almacén de serie devolvería [] sin avisar.
    knowledge = crew_knowledge("Dieta vegetariana estricta.")

    results = await knowledge.aquery(["dieta vegetariana"], score_threshold=0.0)

    assert [r["content"] for r in results] == ["Dieta vegetariana estricta."]


async def test_async_save_and_reset() -> None:
    storage = RunKnowledgeStorage(embedder=EMBEDDER, collection_name="crew")

    await storage.asave(["Movilidad reducida."])
    found = [r["content"] for r in await storage.asearch(["movilidad"], score_threshold=0.0)]
    await storage.areset()

    assert found == ["Movilidad reducida."]
    assert await storage.asearch(["movilidad"], score_threshold=0.0) == []


def test_saving_again_adds_to_the_same_collection() -> None:
    storage = RunKnowledgeStorage(embedder=EMBEDDER, collection_name="crew")

    storage.save(["Alergia al marisco."])
    storage.save(["Sin gluten."])
    storage.save([])

    assert len(storage.search(["alergia gluten"], score_threshold=0.0)) == 2


def test_empty_query_is_rejected() -> None:
    storage = RunKnowledgeStorage(embedder=EMBEDDER, collection_name="crew")

    with pytest.raises(ValueError, match="vacía"):
        storage.search([])


def test_user_without_facts_gets_no_results() -> None:
    assert contents(crew_knowledge(), "alergias") == []


def test_reset_removes_facts() -> None:
    knowledge = crew_knowledge("Alergia al marisco.")

    knowledge.reset()

    assert contents(knowledge, "alergia marisco") == []


def test_requires_project_embedder() -> None:
    with pytest.raises(ValueError, match="embedder del proyecto"):
        RunKnowledgeStorage(embedder=None, collection_name="crew")


def test_chromadb_is_only_used_as_a_library() -> None:
    # CrewAI exige chromadb~=1.1.0 y sus avisos de Dependabot (D-036) están en el
    # servidor HTTP, que nunca debe cargarse, y en una carga remota de código que
    # necesita sentence-transformers. Si alguna de las dos cosas cambia, hay que
    # revisar D-036 antes de seguir.
    assert not any(name.startswith("chromadb.server") for name in sys.modules)
    assert importlib.util.find_spec("sentence_transformers") is None
    assert importlib.util.find_spec("transformers") is None
