"""Sistema multiagente (CrewAI). Estructura en arquitectura-multiagente-crewai.md §11."""

from app.agents.knowledge import install_knowledge_storage

# Todo Knowledge que se cree en el proceso sin storage explícito usa un Qdrant en
# memoria propio, nunca el ChromaDB común (D-036). Se instala al importar el
# paquete para que no dependa de que alguien se acuerde de llamarlo.
install_knowledge_storage()
