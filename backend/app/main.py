"""Punto de entrada de la API (un único proceso y worker, D-011)."""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="TripPlanner API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
