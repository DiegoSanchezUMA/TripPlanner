"""Memoria por ejecución (D-036): aislamiento, hilos y limpieza del directorio."""

import gc
import importlib
import math
from concurrent.futures import ThreadPoolExecutor

import pytest
from crewai import Memory
from crewai.memory.storage.factory import resolve_memory_storage, set_memory_storage_factory
from crewai.memory.types import MemoryRecord

import app.agents
from app.agents.memory import RunMemoryStorage

DIM = 768


def vector(seed: int) -> list[float]:
    """Vector determinista y distinto para cada semilla."""
    return [math.sin(seed * (i + 1)) for i in range(DIM)]


def record(
    content: str, seed: int, scope: str = "/", categories: list[str] | None = None
) -> MemoryRecord:
    return MemoryRecord(
        content=content, scope=scope, categories=categories or [], embedding=vector(seed)
    )


def run_storage(memory: Memory) -> RunMemoryStorage:
    storage = memory._storage  # pyright: ignore[reportPrivateUsage]
    assert isinstance(storage, RunMemoryStorage)
    return storage


def test_importing_agents_package_installs_run_memory_storage() -> None:
    set_memory_storage_factory(None)

    importlib.reload(app.agents)

    assert isinstance(resolve_memory_storage("lancedb"), RunMemoryStorage)


def test_memory_without_storage_uses_run_storage() -> None:
    # Memory() no llama al LLM ni al embedder al construirse.
    run_storage(Memory())


def test_flow_memory_uses_run_storage() -> None:
    # Lo mismo que hace todo Flow sin memoria propia (flow/runtime/__init__.py:890).
    run_storage(Memory(root_scope="/flow/travel_planner_flow"))


def test_each_run_only_sees_its_own_records() -> None:
    user_a = RunMemoryStorage()
    user_b = RunMemoryStorage()

    user_a.save([record("Usuario A: alergia grave a los frutos secos.", seed=1)])
    user_b.save([record("Usuario B: prefiere hoteles de la cadena Melia.", seed=2)])

    found = [r.content for r, _ in user_b.search(vector(1), limit=10)]
    assert found == ["Usuario B: prefiere hoteles de la cadena Melia."]


def test_concurrent_saves_and_searches_lose_nothing() -> None:
    # Con el QdrantEdgeStorage de serie se perdían entre 3 y 6 de estos 8 guardados
    # (5 de 5 ejecuciones): "path already contains segment data".
    storage = RunMemoryStorage()

    def work(i: int) -> None:
        if i % 2:
            storage.save([record(f"hecho {i}", seed=i)])
        else:
            storage.search(vector(i), limit=3)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, range(16)))  # list() propaga cualquier excepción

    assert storage.count() == 8


def test_every_operation_reaches_the_original_storage() -> None:
    # Cada método envuelto con el cerrojo debe pasar bien sus argumentos.
    storage = RunMemoryStorage()
    hotel = record("Prefiere hoteles Melia.", seed=1, scope="/user/a", categories=["hotel"])
    diet = record("Dieta vegetariana.", seed=2, scope="/user/a/diet", categories=["dieta"])
    storage.save([hotel, diet])

    assert storage.get_record(hotel.id) is not None
    storage.update(hotel.model_copy(update={"content": "Prefiere hoteles NH."}))
    assert [r.content for r in storage.list_records(scope_prefix="/user/a/diet")] == [
        "Dieta vegetariana."
    ]
    assert storage.get_scope_info("/user/a").record_count == 2
    assert "/user/a/diet" in storage.list_scopes("/user/a")
    assert storage.list_categories() == {"hotel": 1, "dieta": 1}
    assert storage.count(scope_prefix="/user/a") == 2
    storage.touch_records([hotel.id])
    storage.optimize()
    storage.flush_to_central()
    assert [r.content for r, _ in storage.search(vector(1), scope_prefix="/user/a", limit=1)] == [
        "Prefiere hoteles NH."
    ]

    assert storage.delete(categories=["dieta"]) == 1
    storage.reset(scope_prefix="/user/a")
    assert storage.count() == 0


async def test_async_operations_work() -> None:
    storage = RunMemoryStorage()

    await storage.asave([record("Movilidad reducida.", seed=7)])
    results = await storage.asearch(vector(7), limit=1)

    assert [r.content for r, _ in results] == ["Movilidad reducida."]


def test_close_removes_directory() -> None:
    storage = RunMemoryStorage()
    storage.save([record("Sin gluten.", seed=3)])
    path = storage._base_path  # pyright: ignore[reportPrivateUsage]
    assert path.exists()

    storage.close()

    assert not path.exists()


def test_directory_removed_when_storage_is_no_longer_used() -> None:
    storage = RunMemoryStorage()
    storage.save([record("Dieta vegetariana.", seed=4)])
    path = storage._base_path  # pyright: ignore[reportPrivateUsage]

    del storage
    gc.collect()

    assert not path.exists()


def test_explicit_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="D-036"):
        Memory(storage="./memoria-persistente")
