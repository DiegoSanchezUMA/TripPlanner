"""Sistema multiagente (CrewAI). Estructura en arquitectura-multiagente-crewai.md §11."""

from app.agents.knowledge import install_knowledge_storage
from app.agents.memory import install_memory_storage

# Todo Knowledge y toda Memory que se creen en el proceso sin storage explícito
# usan un Qdrant propio, nunca el almacén de serie común a todo el proceso
# (ChromaDB y LanceDB, D-036). Se instala al importar el paquete para que no
# dependa de que alguien se acuerde de llamarlo.
install_knowledge_storage()
install_memory_storage()
